"""Bounded Ollama protocol. No proxy, redirects, remote hosts or model downloads."""

import http.client
import json

VISION_MODEL = "qwen3-vl:4b-instruct-q4_K_M"
TEXT_MODEL = "qwen3:4b-instruct-2507-q4_K_M"
PROMPT_VERSION = "wardrobe-1"
RESPONSE_LIMIT = 1024 * 1024


class ModelError(ValueError):
    """A safe, user-facing service error; never includes a response or photograph."""


class ModelTimeout(ModelError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON contiene claves repetidas.")
        result[key] = value
    return result


def read_json(value):
    try:
        return json.loads(value, object_pairs_hook=unique_object)
    except (ValueError, TypeError, RecursionError) as error:
        raise ModelError("La respuesta no es un JSON válido y único. No se ha aplicado.") from error


class OllamaClient:
    def __init__(self, timeout=300):
        self.timeout = timeout

    def request(self, path, body=None):
        if path not in {"/api/tags", "/api/chat"}:
            raise ValueError("Operación de Ollama no permitida.")
        connection = http.client.HTTPConnection("127.0.0.1", 11434, timeout=self.timeout)
        try:
            payload = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
            connection.request(
                "POST" if body is not None else "GET",
                path,
                body=payload,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            response = connection.getresponse()
            if response.status != 200:
                raise ModelError(
                    "Ollama rechazó la solicitud. Revisa el servicio y los modelos locales."
                )
            data = response.read(RESPONSE_LIMIT + 1)
            if len(data) > RESPONSE_LIMIT:
                raise ModelError("La respuesta de Ollama supera el límite permitido.")
            return read_json(data)
        except TimeoutError as error:
            raise ModelTimeout(
                "Ollama ha superado el tiempo de espera. Se ha pausado la cola; comprueba el servicio antes de reanudar."
            ) from error
        except (OSError, http.client.HTTPException) as error:
            raise ModelError(
                "No se puede conectar con Ollama en este equipo (127.0.0.1:11434)."
            ) from error
        finally:
            connection.close()

    def models(self):
        response = self.request("/api/tags")
        if not isinstance(response, dict) or not isinstance(response.get("models"), list):
            raise ModelError("Ollama no ha devuelto una lista de modelos válida.")
        found = {}
        for row in response["models"]:
            if not isinstance(row, dict) or row.get("name") not in {VISION_MODEL, TEXT_MODEL}:
                continue
            digest = row.get("digest", "")
            if not isinstance(digest, str) or not digest or len(digest) > 100:
                raise ModelError("No se puede identificar la versión del modelo local.")
            found[row["name"]] = digest
        return found

    def chat(self, model, system, content, schema, image=None):
        if model not in {VISION_MODEL, TEXT_MODEL}:
            raise ModelError("Selecciona uno de los modelos locales admitidos.")
        available = self.models()
        if model not in available:
            raise ModelError(
                f"Falta el modelo local {model}. Instálalo siguiendo la guía de IA local."
            )
        message = {"role": "user", "content": content}
        if image:
            if model != VISION_MODEL:
                raise ModelError("El modelo de texto no recibe imágenes.")
            message["images"] = [image]
        response = self.request(
            "/api/chat",
            {
                "model": model,
                "messages": [{"role": "system", "content": system}, message],
                "format": schema,
                "stream": False,
                "keep_alive": 0,
                "options": {"num_ctx": 8192, "num_predict": 2200, "temperature": 0},
            },
        )
        if (
            not isinstance(response, dict)
            or response.get("done") is not True
            or response.get("done_reason") == "length"
            or response.get("model") != model
            or not isinstance(response.get("message"), dict)
        ):
            raise ModelError("La inferencia está incompleta o no corresponde al modelo solicitado.")
        content = response["message"].get("content")
        if not isinstance(content, str):
            raise ModelError("Ollama no ha devuelto contenido válido.")
        if self.models().get(model) != available[model]:
            raise ModelError(
                "El modelo ha cambiado durante la tarea. Reintenta con una versión estable."
            )
        return read_json(content), available[model]
