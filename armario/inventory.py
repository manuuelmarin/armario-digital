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

from .db import get_db
from .domain import SEASONS, date_value, identifier, ids, move_garments, price_value, text_value
from .images import remove_files, store_image
from .queries import GARMENT_SELECT, garment

bp = Blueprint("inventory", __name__)


@bp.get("/")
def index():
    args = request.args
    clauses, parameters = ["g.archived=?"], [int(args.get("archived") == "1")]
    for column in ("location_id", "category_id"):
        if args.get(column):
            clauses.append(f"g.{column}=?")
            parameters.append(identifier(args, column))
    if args.get("season"):
        if args["season"] not in SEASONS:
            raise ValueError("La temporada no es válida.")
        clauses.append(
            "EXISTS(SELECT 1 FROM garment_seasons s WHERE s.garment_id=g.id AND s.season=?)"
        )
        parameters.append(args["season"])
    if args.get("favorite") == "1":
        clauses.append("g.favorite=1")
    if query := text_value(args, "q"):
        clauses.append(
            "instr(fold(g.name || ' ' || g.brand || ' ' || g.color || ' ' || g.notes), fold(?)) > 0"
        )
        parameters.append(query)
    try:
        page = max(1, min(100000, int(args.get("page", "1"))))
    except ValueError as exc:
        raise ValueError("La página no es válida.") from exc
    where = " WHERE " + " AND ".join(clauses)
    db = get_db()
    count = db.execute("SELECT count(*) FROM garments g" + where, parameters).fetchone()[0]
    rows = db.execute(
        GARMENT_SELECT + where + " ORDER BY g.id DESC LIMIT 48 OFFSET ?",
        [*parameters, (page - 1) * 48],
    ).fetchall()

    def page_url(number):
        return url_for("inventory.index", **dict(args, page=number))

    return render_template(
        "inventory.html", garments=rows, count=count, page=page, page_url=page_url
    )


def save_garment(gid=None):
    form, db = request.form, get_db()
    old = garment(gid) if gid else None
    name = text_value(form, "name", required=True)
    category, location = identifier(form, "category_id"), identifier(form, "location_id")
    seasons = set(form.getlist("seasons"))
    if not seasons.issubset(SEASONS):
        raise ValueError("La temporada no es válida.")
    metadata = (
        name,
        category,
        text_value(form, "brand", 80),
        text_value(form, "size", 30),
        text_value(form, "color", 60),
        text_value(form, "notes", 3000),
        price_value(form),
        date_value(form, "purchased_on"),
        int(form.get("favorite") == "1"),
    )
    photos = [file for file in request.files.getlist("photos") if file.filename]
    existing_count = (
        db.execute("SELECT count(*) FROM garment_images WHERE garment_id=?", (gid,)).fetchone()[0]
        if gid
        else 0
    )
    if existing_count + len(photos) > 6:
        raise ValueError("Puedes guardar hasta seis fotografías por prenda.")
    root = current_app.config["DATA_DIR"] / "images"
    created = []
    try:
        with db:
            if old:
                if old["archived"]:
                    raise ValueError("Recupera esta prenda del archivo antes de editarla.")
                db.execute(
                    "UPDATE garments SET name=?,category_id=?,brand=?,size=?,color=?,notes=?,price_cents=?,purchased_on=?,favorite=? WHERE id=?",
                    (*metadata, gid),
                )
                move_garments(db, [gid], location, "Cambio de ubicación en la ficha")
            else:
                gid = db.execute(
                    "INSERT INTO garments(name,category_id,brand,size,color,notes,price_cents,purchased_on,favorite,location_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (*metadata, location),
                ).lastrowid
            db.execute("DELETE FROM garment_seasons WHERE garment_id=?", (gid,))
            db.executemany(
                "INSERT INTO garment_seasons VALUES (?,?)", [(gid, season) for season in seasons]
            )
            for photo in photos:
                image = store_image(photo, root)
                names = [image["filename"], image["thumbnail"]]
                created.extend(names)
                if db.execute(
                    "SELECT 1 FROM garment_images WHERE garment_id=? AND digest=?",
                    (gid, image["digest"]),
                ).fetchone():
                    remove_files(root, names)
                    continue
                db.execute(
                    "INSERT INTO garment_images(garment_id,filename,thumbnail,digest) VALUES (?,?,?,?)",
                    (gid, image["filename"], image["thumbnail"], image["digest"]),
                )
    except Exception:
        remove_files(root, created)
        raise
    flash("Prenda guardada.", "success")
    return redirect(url_for("inventory.detail", gid=gid))


@bp.route("/prendas/nueva", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        return save_garment()
    return render_template("garment_form.html", item=None, chosen_seasons=[])


@bp.route("/prendas/<int:gid>/editar", methods=["GET", "POST"])
def edit(gid):
    if request.method == "POST":
        return save_garment(gid)
    item = garment(gid)
    if item["archived"]:
        raise ValueError("Recupera esta prenda del archivo antes de editarla.")
    seasons = [
        row[0]
        for row in get_db().execute("SELECT season FROM garment_seasons WHERE garment_id=?", (gid,))
    ]
    return render_template("garment_form.html", item=item, chosen_seasons=seasons)


@bp.get("/prendas/<int:gid>")
def detail(gid):
    item, db = garment(gid), get_db()
    return render_template(
        "garment_detail.html",
        item=item,
        photos=db.execute(
            "SELECT * FROM garment_images WHERE garment_id=? ORDER BY id", (gid,)
        ).fetchall(),
        chosen_seasons=[
            row[0]
            for row in db.execute("SELECT season FROM garment_seasons WHERE garment_id=?", (gid,))
        ],
        outfits=db.execute(
            "SELECT o.* FROM outfits o JOIN outfit_items i ON i.outfit_id=o.id WHERE i.garment_id=?",
            (gid,),
        ).fetchall(),
        movements=db.execute(
            "SELECT m.*, a.name origin, b.name destination FROM garment_movements m JOIN locations a ON a.id=m.from_id JOIN locations b ON b.id=m.to_id WHERE garment_id=? ORDER BY m.id DESC LIMIT 20",
            (gid,),
        ).fetchall(),
    )


@bp.post("/prendas/mover")
def move():
    selected = ids(request.form.getlist("garment_ids"))
    db = get_db()
    with db:
        changed = move_garments(db, selected, identifier(request.form, "destination_id"))
    flash(f"{changed} prendas trasladadas.", "success")
    return redirect(url_for("inventory.index"))


@bp.post("/prendas/<int:gid>/favorito")
def favorite(gid):
    garment(gid)
    db = get_db()
    with db:
        db.execute("UPDATE garments SET favorite=1-favorite WHERE id=?", (gid,))
    return redirect(url_for("inventory.detail", gid=gid))


@bp.post("/prendas/<int:gid>/archivar")
def archive(gid):
    garment(gid)
    db = get_db()
    with db:
        db.execute("UPDATE garments SET archived=1-archived WHERE id=?", (gid,))
    flash("Estado de archivo actualizado. Se conservan las combinaciones y maletas.", "success")
    return redirect(url_for("inventory.detail", gid=gid))


@bp.route("/prendas/<int:gid>/eliminar", methods=["GET", "POST"])
def delete(gid):
    item, db = garment(gid), get_db()
    if request.method == "GET":
        return render_template(
            "confirm.html",
            title="Eliminar prenda",
            message=f"Se eliminarán {item['name']}, sus fotos y su historial. Si está en un outfit o una maleta, la operación se bloqueará. Archivar permite conservarlo todo.",
        )
    if request.form.get("confirm") != "1":
        raise ValueError("Confirma la eliminación.")
    photos = db.execute(
        "SELECT filename,thumbnail FROM garment_images WHERE garment_id=?", (gid,)
    ).fetchall()
    with db:
        db.execute("DELETE FROM garments WHERE id=?", (gid,))
    remove_files(
        current_app.config["DATA_DIR"] / "images", [name for row in photos for name in row]
    )
    flash("Prenda eliminada.", "success")
    return redirect(url_for("inventory.index"))


@bp.post("/prendas/<int:gid>/fotos/<int:image_id>/eliminar")
def delete_image(gid, image_id):
    garment(gid)
    db = get_db()
    photo = db.execute(
        "SELECT * FROM garment_images WHERE id=? AND garment_id=?", (image_id, gid)
    ).fetchone()
    if not photo:
        abort(404)
    with db:
        db.execute("DELETE FROM garment_images WHERE id=?", (image_id,))
    remove_files(current_app.config["DATA_DIR"] / "images", [photo["filename"], photo["thumbnail"]])
    return redirect(url_for("inventory.detail", gid=gid))


@bp.get("/imagenes/<name>")
def image(name):
    from .backups import IMAGE_NAME

    if not IMAGE_NAME.fullmatch(name):
        abort(404)
    return send_from_directory(current_app.config["DATA_DIR"] / "images", name)
