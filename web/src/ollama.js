// Ollama siempre se consulta en el propio equipo y solo a petición del usuario.
export const VISION_MODEL = "qwen3-vl:4b-instruct-q4_K_M";
export const TEXT_MODEL = "qwen3:4b-instruct-2507-q4_K_M";
const endpoint = "http://127.0.0.1:11434";
const responseLimit = 1024 * 1024;

async function request(path, body, timeout) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(endpoint + path, {
      method: body ? "POST" : "GET",
      headers: {
        Accept: "application/json",
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
      redirect: "error",
      credentials: "omit",
    });
    if (!response.ok || !response.body)
      throw Error("Ollama rechazó la solicitud.");
    const reader = response.body.getReader();
    const chunks = [];
    let length = 0;
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        length += value.length;
        if (length > responseLimit)
          throw Error("La respuesta de Ollama es demasiado grande.");
        chunks.push(value);
      }
    } finally {
      await reader.cancel().catch(() => {});
    }
    const result = new Uint8Array(length);
    let offset = 0;
    for (const chunk of chunks) {
      result.set(chunk, offset);
      offset += chunk.length;
    }
    return JSON.parse(new TextDecoder().decode(result));
  } finally {
    clearTimeout(timer);
  }
}

export async function models() {
  const result = await request("/api/tags", null, 10000);
  if (!Array.isArray(result.models)) throw Error("Lista de modelos inválida.");
  const found = {};
  for (const item of result.models) {
    if (
      !item ||
      typeof item !== "object" ||
      ![VISION_MODEL, TEXT_MODEL].includes(item.name)
    )
      continue;
    if (Object.hasOwn(found, item.name))
      throw Error("La lista de modelos contiene duplicados.");
    if (
      typeof item.digest !== "string" ||
      !item.digest ||
      item.digest.length > 100
    )
      throw Error("No se puede identificar la versión del modelo.");
    found[item.name] = item.digest;
  }
  return found;
}

export async function chat(model, system, content, schema, image) {
  if (
    ![VISION_MODEL, TEXT_MODEL].includes(model) ||
    (image && model !== VISION_MODEL)
  )
    throw Error("Modelo o imagen no admitidos.");
  const available = await models();
  if (!available[model]) throw Error("Falta instalar el modelo " + model + ".");
  const message = { role: "user", content };
  if (image) message.images = [image];
  const result = await request(
    "/api/chat",
    {
      model,
      messages: [{ role: "system", content: system }, message],
      format: schema,
      stream: false,
      keep_alive: 0,
      options: { num_ctx: 8192, num_predict: 2200, temperature: 0 },
    },
    300000,
  );
  if (
    result.done !== true ||
    result.done_reason === "length" ||
    result.model !== model ||
    typeof result.message?.content !== "string"
  )
    throw Error("La respuesta del modelo está incompleta.");
  if ((await models())[model] !== available[model])
    throw Error("El modelo ha cambiado durante la tarea. Vuelve a intentarlo.");
  return {
    value: JSON.parse(result.message.content),
    digest: available[model],
  };
}
