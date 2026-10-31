"""Optional local assistance: explicit requests, editable review, constrained saving."""

import json

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from .ai_client import TEXT_MODEL, VISION_MODEL
from .ai_jobs import KINDS, STATES, decoded_job, enqueue, preferences, valid_sources
from .db import get_db
from .domain import ids, text_value, validate_garments
from .profiles import (
    CONTRASTS,
    GROUPS,
    LEG_LENGTHS,
    TYPES,
    approved,
    blank_profile,
    profile_from_form,
    revision,
    save_profile,
    source,
    vision_snapshot,
)
from .queries import active_garments, entity, garment
from .recommendations import (
    catalog,
    constraints_from_form,
    current_snapshot,
    make_snapshot,
    valid_plan,
)

bp = Blueprint("assistant", __name__)


def job_entity(jid):
    row = get_db().execute("SELECT * FROM ai_jobs WHERE id=?", (jid,)).fetchone()
    if row is None:
        abort(404, "Esta tarea no existe.")
    return decoded_job(row)


def task_redirect(jid):
    worker = current_app.extensions.get("ai_worker")
    if worker:
        worker.wake.set()
    return redirect(url_for("assistant.task", jid=jid))


@bp.route("/ajustes/ia", methods=["GET", "POST"])
def settings():
    db = get_db()
    if request.method == "POST":
        enabled = int(request.form.get("enabled") == "1")
        with db:
            db.execute("UPDATE ai_settings SET enabled=? WHERE id=1", (enabled,))
            if not enabled:
                db.execute(
                    "UPDATE ai_jobs SET status='cancelled',error='Asistencia desactivada por el usuario.',finished_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE status IN ('queued','running') AND kind!='check'"
                )
        flash("Preferencias de asistencia local guardadas.", "success")
        return redirect(url_for("assistant.settings"))
    check = db.execute(
        "SELECT * FROM ai_jobs WHERE kind='check' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return render_template(
        "ai_settings.html",
        preferences=preferences(db),
        check=decoded_job(check) if check else None,
        vision_model=VISION_MODEL,
        text_model=TEXT_MODEL,
        states=STATES,
    )


@bp.post("/ia/comprobar")
def check():
    db = get_db()
    with db:
        jid = enqueue(db, "check", {})
    return task_redirect(jid)


@bp.get("/ia/tareas")
def tasks():
    rows = get_db().execute("SELECT * FROM ai_jobs ORDER BY id DESC LIMIT 100").fetchall()
    return render_template(
        "ai_tasks.html", jobs=rows, states=STATES, kinds=KINDS, preferences=preferences(get_db())
    )


@bp.post("/ia/cola")
def queue_control():
    action = request.form.get("action")
    if action not in {"pause", "resume", "clear"}:
        raise ValueError("Elige una acción válida para la cola.")
    db = get_db()
    with db:
        if action == "clear":
            if request.form.get("confirm") != "1":
                raise ValueError("Confirma la eliminación del historial de tareas finalizadas.")
            db.execute("DELETE FROM ai_jobs WHERE status NOT IN ('queued','running')")
        else:
            db.execute("UPDATE ai_settings SET paused=? WHERE id=1", (int(action == "pause"),))
    worker = current_app.extensions.get("ai_worker")
    if worker:
        worker.wake.set()
    return redirect(url_for("assistant.tasks"))


@bp.get("/ia/tareas/<int:jid>")
def task(jid):
    job = job_entity(jid)
    items = {}
    fresh = valid_sources(get_db(), job)
    if job["kind"] == "outfit" and job["result"]:
        wanted = {gid for proposal in job["result"]["outfits"] for gid in proposal["garment_ids"]}
        for row in active_garments():
            if row["id"] in wanted:
                items[row["id"]] = row
    return render_template(
        "ai_task.html", job=job, items=items, fresh=fresh, states=STATES, kinds=KINDS
    )


@bp.get("/ia/tareas/<int:jid>/estado")
def task_state(jid):
    job = job_entity(jid)
    return jsonify(status=job["status"])


@bp.post("/ia/tareas/<int:jid>/cancelar")
def cancel(jid):
    job_entity(jid)
    db = get_db()
    with db:
        db.execute(
            "UPDATE ai_jobs SET status='cancelled',error='Tarea cancelada por el usuario.',finished_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=? AND status IN ('queued','running')",
            (jid,),
        )
    return redirect(url_for("assistant.task", jid=jid))


@bp.post("/ia/tareas/<int:jid>/reintentar")
def retry(jid):
    job = job_entity(jid)
    if job["status"] not in {"failed", "cancelled", "stale"}:
        raise ValueError("Solo se reintentan tareas con error, canceladas o con datos modificados.")
    db = get_db()
    with db:
        if job["kind"] == "vision":
            validate_garments(db, [job["garment_id"]])
            snapshot = vision_snapshot(db, job["garment_id"])
        elif job["kind"] == "outfit":
            snapshot = make_snapshot(db, job["input"]["constraints"])
        else:
            snapshot = {}
        new_id = enqueue(db, job["kind"], snapshot, job["garment_id"])
    return task_redirect(new_id)


@bp.route("/ia/analizar", methods=["GET", "POST"])
def analyze_batch():
    if request.method == "GET":
        return render_template(
            "ai_analyze.html", garments=active_garments(), preferences=preferences(get_db())
        )
    chosen = ids(request.form.getlist("garment_ids"))
    if not 1 <= len(chosen) <= 20:
        raise ValueError("Selecciona entre una y veinte prendas para analizar.")
    db = get_db()
    validate_garments(db, chosen)
    with db:
        for gid in chosen:
            enqueue(db, "vision", vision_snapshot(db, gid), gid)
    worker = current_app.extensions.get("ai_worker")
    if worker:
        worker.wake.set()
    flash(f"{len(chosen)} análisis en cola. Ninguno cambiará tus fichas sin revisión.", "success")
    return redirect(url_for("assistant.tasks"))


@bp.post("/prendas/<int:gid>/analizar")
def analyze(gid):
    validate_garments(get_db(), [gid])
    db = get_db()
    with db:
        jid = enqueue(db, "vision", vision_snapshot(db, gid), gid)
    return task_redirect(jid)


@bp.route("/prendas/<int:gid>/descripcion", methods=["GET", "POST"])
def profile(gid):
    item = garment(gid)
    if item["archived"]:
        raise ValueError("Recupera la prenda del archivo antes de revisar su descripción.")
    db = get_db()
    saved = approved(db, gid)
    job_id = (
        request.form.get("job_id", "") if request.method == "POST" else request.args.get("job", "")
    )
    job = None
    if job_id:
        try:
            job = job_entity(int(job_id))
        except ValueError as error:
            raise ValueError("La tarea seleccionada no es válida.") from error
        if (
            job["kind"] != "vision"
            or job["garment_id"] != gid
            or job["status"] != "completed"
            or not valid_sources(db, job)
        ):
            raise ValueError(
                "Esta propuesta ya no corresponde a la foto o revisión actual. Solicita otro análisis."
            )
    data = job["result"] if job else saved["profile"] if saved else blank_profile()
    current_source = source(db, gid)
    if request.method == "POST":
        try:
            expected = int(request.form.get("revision", ""))
        except ValueError as error:
            raise ValueError("La revisión no es válida. Recarga la página.") from error
        if current_source != {
            "name": request.form.get("source_name", ""),
            "hash": request.form.get("source_hash", ""),
        }:
            raise ValueError(
                "La foto principal ha cambiado. Recarga antes de revisar la descripción."
            )
        if request.form.get("confirm") != "1":
            raise ValueError("Confirma que has revisado la descripción.")
        provenance = {"origin": "vision_reviewed" if job else "manual", "schema": 1}
        if job:
            provenance.update(
                model=job["model"],
                digest=job["model_digest"],
                prompt=job["prompt_version"],
                job_id=job["id"],
            )
        with db:
            save_profile(db, gid, profile_from_form(request.form), expected, provenance)
        flash(
            "Descripción revisada guardada. Las propuestas de IA nunca sustituyen tus correcciones automáticamente.",
            "success",
        )
        return redirect(url_for("inventory.detail", gid=gid))
    return render_template(
        "ai_profile.html",
        item=item,
        data=data,
        saved=saved,
        job=job,
        revision=revision(db, gid),
        source=current_source,
        types=TYPES,
        contrasts=CONTRASTS,
        lengths=LEG_LENGTHS,
        groups=GROUPS,
    )


def default_constraints():
    from werkzeug.datastructures import MultiDict

    return constraints_from_form(MultiDict())


@bp.route("/outfits/generar", methods=["GET", "POST"])
def generate():
    db = get_db()
    if request.method == "POST":
        constraints = constraints_from_form(request.form)
        constraints["excluded"] = ids(request.form.getlist("excluded"))
        if len(constraints["excluded"]) > 20:
            raise ValueError("Hay demasiadas exclusiones. Crea una nueva generación.")
        if constraints["location_id"]:
            entity("locations", constraints["location_id"])
        with db:
            jid = enqueue(db, "outfit", make_snapshot(db, constraints))
        return task_redirect(jid)
    constraints = default_constraints()
    constraints["fixed"] = ids(request.args.getlist("fixed"))
    if request.args.get("outfit_id"):
        try:
            outfit_id, replacement = (
                int(request.args["outfit_id"]),
                int(request.args.get("replace", "0")),
            )
        except ValueError as error:
            raise ValueError("La sustitución no es válida.") from error
        entity("outfits", outfit_id)
        chosen = [
            r[0]
            for r in db.execute(
                "SELECT garment_id FROM outfit_items WHERE outfit_id=?", (outfit_id,)
            )
        ]
        if replacement not in chosen:
            raise ValueError("Elige una prenda del outfit para sustituir.")
        constraints["fixed"] = [gid for gid in chosen if gid != replacement]
        constraints["excluded"] = [replacement]
    if constraints["fixed"]:
        validate_garments(db, constraints["fixed"])
    garments = active_garments()
    # Include jackets and accessories in the readiness count, independent of the default filters.
    all_constraints = {**default_constraints(), "accessories": True}
    ready = set(catalog(db, all_constraints))
    return render_template(
        "ai_generate.html",
        constraints=constraints,
        garments=garments,
        ready=ready,
        preferences=preferences(db),
    )


def result_proposal(job, number):
    if job["kind"] != "outfit" or job["status"] != "completed" or not job["result"]:
        raise ValueError("Esta tarea no tiene propuestas guardables.")
    try:
        proposal = job["result"]["outfits"][int(number) - 1]
        if int(number) < 1:
            raise IndexError
    except (ValueError, TypeError, IndexError) as error:
        raise ValueError("La propuesta seleccionada no existe.") from error
    if not current_snapshot(get_db(), job["input"]):
        raise ValueError(
            "El armario ha cambiado desde la generación. Vuelve a generar antes de guardar o sustituir."
        )
    current_items = catalog(get_db(), job["input"]["constraints"])
    if not valid_plan(proposal["garment_ids"], current_items, job["input"]["constraints"]):
        raise ValueError("La propuesta ya no cumple los filtros. Vuelve a generar.")
    return proposal


@bp.post("/ia/tareas/<int:jid>/guardar")
def save_outfit(jid):
    job = job_entity(jid)
    proposal = result_proposal(job, request.form.get("proposal"))
    db = get_db()
    with db:
        oid = db.execute(
            "INSERT INTO outfits(name,notes,occasion) VALUES (?,?,?)",
            (
                text_value(request.form, "name", required=True),
                proposal["reason"][:3000],
                job["input"]["constraints"]["occasion"],
            ),
        ).lastrowid
        db.executemany(
            "INSERT INTO outfit_items(outfit_id,garment_id) VALUES (?,?)",
            [(oid, gid) for gid in proposal["garment_ids"]],
        )
        db.execute(
            "INSERT INTO outfit_origins(outfit_id,provenance_json) VALUES (?,?)",
            (
                oid,
                json.dumps(
                    {
                        "model": job["model"],
                        "digest": job["model_digest"],
                        "prompt": job["prompt_version"],
                        "job_id": jid,
                        "created_at": job["finished_at"],
                        "constraints": job["input"]["constraints"],
                        "ratings": {key: proposal[key] for key in ("harmony", "style", "balance")},
                    },
                    ensure_ascii=False,
                ),
            ),
        )
    flash("Outfit guardado. Puedes editarlo como cualquier combinación.", "success")
    return redirect(url_for("looks.detail", oid=oid))


@bp.post("/ia/tareas/<int:jid>/sustituir")
def replace(jid):
    job = job_entity(jid)
    proposal = result_proposal(job, request.form.get("proposal"))
    try:
        gid = int(request.form.get("garment_id", ""))
    except ValueError as error:
        raise ValueError("Selecciona la prenda que quieres sustituir.") from error
    if gid not in proposal["garment_ids"]:
        raise ValueError("Esta prenda no pertenece a la propuesta.")
    constraints = {
        **job["input"]["constraints"],
        "mode": "recommended",
        "fixed": [other for other in proposal["garment_ids"] if other != gid],
        "excluded": [gid],
    }
    db = get_db()
    with db:
        new_id = enqueue(db, "outfit", make_snapshot(db, constraints))
    return task_redirect(new_id)
