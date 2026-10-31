"""Durable single-worker queue. Inference never holds the application mutation lock."""

import json
import logging
import threading

from .ai_client import (
    PROMPT_VERSION,
    TEXT_MODEL,
    VISION_MODEL,
    ModelError,
    ModelTimeout,
    OllamaClient,
)
from .db import connect
from .profiles import PROFILE_SCHEMA, VISION_PROMPT, image_payload, source_matches, validate_profile
from .recommendations import RANKING_SCHEMA, TEXT_PROMPT, current_snapshot, prompt_data, rank_result

LOG = logging.getLogger(__name__)
STATES = {
    "queued": "En cola",
    "running": "En curso",
    "completed": "Completada",
    "failed": "Error",
    "cancelled": "Cancelada",
    "stale": "Datos modificados",
}
KINDS = {"check": "Comprobar Ollama", "vision": "Describir prenda", "outfit": "Proponer outfits"}


def preferences(db):
    return dict(db.execute("SELECT * FROM ai_settings WHERE id=1").fetchone())


def enqueue(db, kind, snapshot, gid=None):
    if kind not in KINDS:
        raise ValueError("Tipo de tarea no admitido.")
    if kind != "check" and not preferences(db)["enabled"]:
        raise ValueError("Activa la asistencia local en Ajustes antes de solicitar una tarea.")
    if (
        db.execute("SELECT count(*) FROM ai_jobs WHERE status IN ('queued','running')").fetchone()[
            0
        ]
        >= 200
    ):
        raise ValueError("La cola tiene 200 tareas pendientes. Espera o cancela alguna.")
    if (
        kind == "vision"
        and db.execute(
            "SELECT 1 FROM ai_jobs WHERE kind='vision' AND garment_id=? AND status IN ('queued','running')",
            (gid,),
        ).fetchone()
    ):
        raise ValueError("Esta prenda ya tiene un análisis pendiente.")
    return db.execute(
        "INSERT INTO ai_jobs(kind,garment_id,input_json,prompt_version,model) VALUES (?,?,?,?,?)",
        (
            kind,
            gid,
            json.dumps(snapshot, ensure_ascii=False),
            PROMPT_VERSION,
            VISION_MODEL if kind == "vision" else TEXT_MODEL if kind == "outfit" else "",
        ),
    ).lastrowid


def decoded_job(row):
    result = dict(row)
    result["input"] = json.loads(row["input_json"])
    result["result"] = json.loads(row["result_json"]) if row["result_json"] else None
    return result


def valid_sources(db, job):
    if job["kind"] == "vision":
        return source_matches(db, job["garment_id"], job["input"])
    if job["kind"] == "outfit":
        return current_snapshot(db, job["input"])
    return True


class AIWorker:
    def __init__(self, root, mutation_lock, client=None):
        self.root = root
        self.lock = mutation_lock
        self.client = client or OllamaClient()
        self.stopping = threading.Event()
        self.wake = threading.Event()
        self.thread = None

    def recover(self):
        with self.lock:
            db = connect(self.root / "wardrobe.sqlite")
            try:
                with db:
                    db.execute(
                        "UPDATE ai_jobs SET status='failed',error='La aplicación se cerró durante esta tarea. Puedes reintentar explícitamente.',finished_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE status='running'"
                    )
            finally:
                db.close()

    def start(self):
        if self.thread:
            return
        self.recover()
        self.thread = threading.Thread(target=self.run, name="armario-local-ai", daemon=True)
        self.thread.start()

    def stop(self):
        self.stopping.set()
        self.wake.set()
        if self.thread:
            self.thread.join(timeout=2)
        # If Ollama is still generating, its response will be discarded before any write.
        with self.lock:
            db = connect(self.root / "wardrobe.sqlite")
            try:
                with db:
                    db.execute(
                        "UPDATE ai_jobs SET status='cancelled',error='La aplicación se ha cerrado. Puedes reintentar la tarea.',finished_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE status='running'"
                    )
            finally:
                db.close()

    def run(self):
        while not self.stopping.is_set():
            if not self.run_once():
                self.wake.wait(1)
                self.wake.clear()

    def run_once(self):
        db = connect(self.root / "wardrobe.sqlite")
        job = None
        try:
            with self.lock, db:
                if self.stopping.is_set():
                    return False
                settings = preferences(db)
                row = db.execute(
                    "SELECT * FROM ai_jobs WHERE status='queued' AND (kind='check' OR ?=1) ORDER BY id LIMIT 1",
                    (int(settings["enabled"] and not settings["paused"]),),
                ).fetchone()
                if not row:
                    return False
                job = decoded_job(row)
                if not valid_sources(db, job):
                    self.finish(
                        db,
                        job["id"],
                        "stale",
                        error="La foto, descripción, ubicación o disponibilidad ha cambiado. Crea una nueva tarea.",
                    )
                    return True
                db.execute(
                    "UPDATE ai_jobs SET status='running',started_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
                    (job["id"],),
                )
                image = image_payload(self.root, job["input"]) if job["kind"] == "vision" else None
            # No DB transaction, Flask context or mutation lock spans an HTTP request.
            if job["kind"] == "check":
                result, digest = {"models": self.client.models()}, ""
            elif job["kind"] == "vision":
                value, digest = self.client.chat(
                    VISION_MODEL,
                    VISION_PROMPT,
                    "Describe la prenda de esta fotografía según los siete grupos.",
                    PROFILE_SCHEMA,
                    image=image,
                )
                result = validate_profile(value)
            else:
                content = json.dumps(prompt_data(job["input"]), ensure_ascii=False)
                value, digest = self.client.chat(TEXT_MODEL, TEXT_PROMPT, content, RANKING_SCHEMA)
                result = rank_result(value, job["input"])
            with self.lock, db:
                if self.stopping.is_set():
                    return True
                row = db.execute("SELECT status FROM ai_jobs WHERE id=?", (job["id"],)).fetchone()
                if not row or row["status"] != "running":
                    return True
                if job["kind"] != "check" and not preferences(db)["enabled"]:
                    self.finish(
                        db, job["id"], "cancelled", error="La asistencia local se ha desactivado."
                    )
                elif not valid_sources(db, job):
                    self.finish(
                        db,
                        job["id"],
                        "stale",
                        error="Los datos han cambiado durante la tarea. No se ha aplicado la respuesta.",
                    )
                else:
                    self.finish(db, job["id"], "completed", result, digest=digest)
            return True
        except (ValueError, OSError) as error:
            if job and not self.stopping.is_set():
                with self.lock, db:
                    if isinstance(error, ModelTimeout):
                        db.execute("UPDATE ai_settings SET paused=1 WHERE id=1")
                    message = (
                        str(error)
                        if isinstance(error, (ValueError, ModelError))
                        else "No se puede leer la fotografía local. Comprueba su integridad."
                    )
                    self.finish(db, job["id"], "failed", error=message)
            return bool(job)
        except Exception:
            # Never log prompts, model output, photos or user-entered data.
            LOG.error(
                "Error interno en el trabajador de IA (tarea %s).",
                job["id"] if job else "sin asignar",
            )
            if job and not self.stopping.is_set():
                with self.lock, db:
                    self.finish(
                        db,
                        job["id"],
                        "failed",
                        error="Error interno de la tarea. Puedes reintentar; tus prendas no se han modificado.",
                    )
            return bool(job)
        finally:
            db.close()

    @staticmethod
    def finish(db, job_id, status, result=None, error="", digest=""):
        db.execute(
            "UPDATE ai_jobs SET status=?,result_json=?,error=?,model_digest=?,finished_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=? AND status IN ('queued','running')",
            (
                status,
                json.dumps(result, ensure_ascii=False) if result is not None else None,
                error[:800],
                digest,
                job_id,
            ),
        )
