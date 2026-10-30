from datetime import UTC, datetime

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from .backups import create_backup, verify_backup
from .db import get_db
from .domain import text_value
from .queries import entity

bp = Blueprint("settings", __name__)


@bp.route("/empezar", methods=["GET", "POST"])
def onboarding():
    db = get_db()
    if db.execute("SELECT 1 FROM locations LIMIT 1").fetchone():
        return redirect(url_for("inventory.index"))
    if request.method == "POST":
        name = text_value(request.form, "name", 80, required=True)
        with db:
            db.execute("INSERT INTO locations(name) VALUES (?)", (name,))
        flash("Tu primer espacio está listo. Añade una prenda para empezar.", "success")
        return redirect(url_for("inventory.new"))
    return render_template("onboarding.html")


@bp.get("/ubicaciones")
def locations():
    rows = (
        get_db()
        .execute(
            "SELECT l.*,count(g.id) total FROM locations l LEFT JOIN garments g ON g.location_id=l.id AND g.archived=0 GROUP BY l.id ORDER BY l.id"
        )
        .fetchall()
    )
    return render_template("locations.html", items=rows)


@bp.post("/ubicaciones/nueva")
@bp.post("/ubicaciones/<int:lid>/renombrar")
def save_location(lid=None):
    if lid:
        entity("locations", lid)
    name = text_value(request.form, "name", 80, required=True)
    db = get_db()
    with db:
        if lid:
            db.execute("UPDATE locations SET name=? WHERE id=?", (name, lid))
        else:
            db.execute("INSERT INTO locations(name) VALUES (?)", (name,))
    flash("Ubicación guardada.", "success")
    return redirect(url_for("settings.locations"))


@bp.route("/ubicaciones/<int:lid>/eliminar", methods=["GET", "POST"])
def delete_location(lid):
    location = entity("locations", lid)
    if request.method == "GET":
        return render_template(
            "confirm.html",
            title="Eliminar ubicación",
            message=f"Se eliminará {location['name']} si no tiene prendas, viajes ni movimientos asociados.",
        )
    if request.form.get("confirm") != "1":
        raise ValueError("Confirma la eliminación.")
    db = get_db()
    with db:
        db.execute("DELETE FROM locations WHERE id=?", (lid,))
    return redirect(url_for("settings.locations"))


@bp.get("/ajustes")
def index():
    root = current_app.config["DATA_DIR"]
    copies = (
        sorted((root / "backups").glob("*.zip"), reverse=True)
        if (root / "backups").exists()
        else []
    )
    regular = [p for p in copies if p.name.startswith(("daily-", "manual-")) and not p.is_symlink()]
    latest = max((p.stat().st_mtime for p in regular), default=None)
    backup_age = max(0, int((datetime.now(UTC).timestamp() - latest) / 86400)) if latest else None
    return render_template("settings.html", data_dir=root, copies=copies, backup_age=backup_age)


@bp.post("/copias/limpiar")
def prune_daily_backups():
    """Delete only old daily backups after an explicit action; preserve all others."""
    if request.form.get("confirm") != "1":
        raise ValueError("Confirma la limpieza de copias automáticas.")
    try:
        keep = int(request.form.get("keep", ""))
    except ValueError as exc:
        raise ValueError("Introduce un número válido de copias.") from exc
    if not 1 <= keep <= 365:
        raise ValueError("Conserva entre 1 y 365 copias diarias.")
    folder = current_app.config["DATA_DIR"] / "backups"
    copies = sorted(
        (p for p in folder.glob("daily-*.zip") if p.is_file() and not p.is_symlink()),
        key=lambda p: p.name,
        reverse=True,
    )
    # Never discard older copies if the retained daily archives do not verify.
    if len(copies) > keep:
        for copy in copies[:keep]:
            try:
                verify_backup(copy)
            except Exception as exc:
                raise ValueError(
                    "No se ha borrado nada: una de las copias que se conservarían no supera la verificación."
                ) from exc
    for copy in copies[keep:]:
        copy.unlink()
    flash(f"Se han eliminado {max(0, len(copies) - keep)} copias diarias antiguas.", "success")
    return redirect(url_for("settings.index"))


@bp.post("/ajustes/categorias")
def category():
    db = get_db()
    with db:
        db.execute(
            "INSERT INTO categories(name) VALUES (?)",
            (text_value(request.form, "name", 80, required=True),),
        )
    flash("Categoría creada.", "success")
    return redirect(url_for("settings.index"))


@bp.post("/copias")
def backup():
    path = create_backup(current_app.config["DATA_DIR"])
    flash("Copia creada con base de datos, fotografías y comprobaciones de integridad.", "success")
    return redirect(url_for("settings.download_backup", name=path.name))


@bp.get("/copias/<name>")
def download_backup(name):
    if not name.endswith(".zip") or "/" in name or "\\" in name or not name.isascii():
        abort(404)
    return send_from_directory(current_app.config["DATA_DIR"] / "backups", name, as_attachment=True)
