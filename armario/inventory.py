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
from .domain import (
    SEASONS,
    date_value,
    identifier,
    ids,
    move_garments,
    price_value,
    text_value,
    validate_garments,
)
from .images import record_integrity, remove_files, store_image
from .queries import GARMENT_SELECT, garment

bp = Blueprint("inventory", __name__)
SORT_OPTIONS = {
    "newest": "g.id DESC",
    "oldest": "g.id ASC",
    "name": "fold(g.name),g.id",
    "name_desc": "fold(g.name) DESC,g.id DESC",
}


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
    if args.get("tag_id"):
        clauses.append(
            "EXISTS(SELECT 1 FROM garment_tags gt WHERE gt.garment_id=g.id AND gt.tag_id=?)"
        )
        parameters.append(identifier(args, "tag_id"))
    if args.get("collection_id"):
        clauses.append(
            "EXISTS(SELECT 1 FROM collection_items ci WHERE ci.garment_id=g.id AND ci.collection_id=?)"
        )
        parameters.append(identifier(args, "collection_id"))
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
    sort = args.get("sort", "newest")
    if sort not in SORT_OPTIONS:
        raise ValueError("El orden seleccionado no es válido.")
    db = get_db()
    count = db.execute("SELECT count(*) FROM garments g" + where, parameters).fetchone()[0]
    rows = db.execute(
        GARMENT_SELECT + where + f" ORDER BY {SORT_OPTIONS[sort]} LIMIT 48 OFFSET ?",
        [*parameters, (page - 1) * 48],
    ).fetchall()

    def page_url(number):
        return url_for("inventory.index", **dict(args, page=number))

    def filter_url(**changes):
        values = {**args.to_dict(), "page": 1, **changes}
        return url_for(
            "inventory.index",
            **{key: value for key, value in values.items() if value is not None and value != ""},
        )

    return render_template(
        "inventory.html",
        garments=rows,
        count=count,
        page=page,
        page_url=page_url,
        filter_url=filter_url,
        sort=sort,
        total=db.execute("SELECT count(*) FROM garments WHERE archived=0").fetchone()[0],
        all_tags=db.execute("SELECT * FROM tags ORDER BY name").fetchall(),
        all_collections=db.execute("SELECT * FROM collections ORDER BY name").fetchall(),
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
                names = [image["filename"], image["thumbnail"], image["preview"]]
                created.extend(names)
                if db.execute(
                    "SELECT 1 FROM garment_images WHERE garment_id=? AND digest=?",
                    (gid, image["digest"]),
                ).fetchone():
                    remove_files(root, names)
                    continue
                record_integrity(db, root, names)
                db.execute(
                    "INSERT INTO garment_images(garment_id,filename,thumbnail,preview,digest,width,height,preview_width,thumbnail_width) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        gid,
                        image["filename"],
                        image["thumbnail"],
                        image["preview"],
                        image["digest"],
                        image["width"],
                        image["height"],
                        image["preview_width"],
                        image["thumbnail_width"],
                    ),
                )
    except Exception:
        remove_files(root, created)
        raise
    flash("Prenda guardada.", "success")
    return redirect(url_for("inventory.detail", gid=gid))


@bp.route("/prendas/importar", methods=["GET", "POST"])
def bulk_import():
    db = get_db()
    if not db.execute("SELECT 1 FROM locations LIMIT 1").fetchone():
        return redirect(url_for("settings.onboarding"))
    if request.method == "GET":
        return render_template("bulk_import.html")
    category = identifier(request.form, "category_id")
    location = identifier(request.form, "location_id")
    uploads = [file for file in request.files.getlist("photos") if file.filename]
    if not 1 <= len(uploads) <= 20:
        raise ValueError("Selecciona entre una y veinte fotografías.")
    names_input = request.form.getlist("photo_names")
    if names_input and len(names_input) != len(uploads):
        raise ValueError("La lista de fotografías ha cambiado. Vuelve a seleccionarlas.")
    if names_input and any(not n.strip() or len(n.strip()) > 120 for n in names_input):
        raise ValueError("Cada nombre debe tener entre 1 y 120 caracteres.")
    root = current_app.config["DATA_DIR"] / "images"
    created = []
    try:
        with db:
            for index, upload in enumerate(uploads):
                name = upload.filename.replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0]
                name = (
                    names_input[index].strip()
                    if names_input
                    else (name.strip()[:120] or "Prenda sin nombre")
                )
                gid = db.execute(
                    "INSERT INTO garments(name,category_id,location_id) VALUES (?,?,?)",
                    (name, category, location),
                ).lastrowid
                image = store_image(upload, root)
                names = [image["filename"], image["thumbnail"], image["preview"]]
                created.extend(names)
                record_integrity(db, root, names)
                db.execute(
                    "INSERT INTO garment_images(garment_id,filename,thumbnail,preview,digest,width,height,preview_width,thumbnail_width) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        gid,
                        *(
                            image[k]
                            for k in (
                                "filename",
                                "thumbnail",
                                "preview",
                                "digest",
                                "width",
                                "height",
                                "preview_width",
                                "thumbnail_width",
                            )
                        ),
                    ),
                )
    except Exception:
        remove_files(root, created)
        raise
    flash(f"Se han importado {len(uploads)} prendas. Puedes editar sus datos después.", "success")
    return redirect(url_for("inventory.index"))


@bp.route("/prendas/nueva", methods=["GET", "POST"])
def new():
    if not get_db().execute("SELECT 1 FROM locations LIMIT 1").fetchone():
        return redirect(url_for("settings.onboarding"))
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
            "SELECT * FROM garment_images WHERE garment_id=? ORDER BY is_primary DESC, COALESCE(sort_order, id), id",
            (gid,),
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


@bp.post("/prendas/traslado/revisar")
def review_move():
    selected = ids(request.form.getlist("garment_ids"))
    db = get_db()
    rows = validate_garments(db, selected)
    destination = identifier(request.form, "destination_id")
    place = db.execute("SELECT * FROM locations WHERE id=?", (destination,)).fetchone()
    if not place:
        raise ValueError("La ubicación de destino no existe.")
    locations = {row["id"]: row["name"] for row in db.execute("SELECT * FROM locations")}
    return render_template("move_review.html", garments=rows, destination=place, names=locations)


@bp.post("/prendas/mover")
def move():
    selected = ids(request.form.getlist("garment_ids"))
    db = get_db()
    with db:
        changed = move_garments(db, selected, identifier(request.form, "destination_id"))
    flash(f"{changed} prendas trasladadas.", "success")
    return redirect(url_for("inventory.index"))


@bp.post("/prendas/editar-lote")
def bulk_edit():
    selected = ids(request.form.getlist("garment_ids"))
    db = get_db()
    rows = validate_garments(db, selected)
    if request.form.get("confirm") != "1":
        return render_template(
            "bulk_edit.html",
            garments=rows,
            tags=db.execute("SELECT * FROM tags ORDER BY name").fetchall(),
        )
    category_value = request.form.get("category_id", "")
    category = identifier(request.form, "category_id") if category_value else None
    if category and not db.execute("SELECT 1 FROM categories WHERE id=?", (category,)).fetchone():
        raise ValueError("La categoría no existe.")
    season = request.form.get("season", "")
    if season and season not in SEASONS:
        raise ValueError("La temporada no es válida.")
    tag_value = request.form.get("tag_id", "")
    tag = identifier(request.form, "tag_id") if tag_value else None
    if tag and not db.execute("SELECT 1 FROM tags WHERE id=?", (tag,)).fetchone():
        raise ValueError("La etiqueta no existe.")
    if not any((category, season, tag)):
        raise ValueError("Elige al menos un cambio.")
    with db:
        validate_garments(db, selected)
        if category:
            db.executemany(
                "UPDATE garments SET category_id=? WHERE id=?",
                [(category, gid) for gid in selected],
            )
        if season:
            db.executemany(
                "INSERT OR IGNORE INTO garment_seasons(garment_id,season) VALUES (?,?)",
                [(gid, season) for gid in selected],
            )
        if tag:
            db.executemany(
                "INSERT OR IGNORE INTO garment_tags(garment_id,tag_id) VALUES (?,?)",
                [(gid, tag) for gid in selected],
            )
    flash(
        f"Cambios guardados en {len(selected)} prendas. Sus ubicaciones no han cambiado.", "success"
    )
    return redirect(url_for("inventory.index"))


@bp.post("/prendas/<int:gid>/favorito")
def favorite(gid):
    garment(gid)
    db = get_db()
    with db:
        db.execute("UPDATE garments SET favorite=1-favorite WHERE id=?", (gid,))
    if request.form.get("return_view") == "inventory":
        return redirect(
            url_for(
                "inventory.index",
                **{
                    key: request.form[key]
                    for key in (
                        "q",
                        "category_id",
                        "location_id",
                        "tag_id",
                        "collection_id",
                        "season",
                        "favorite",
                        "archived",
                        "sort",
                        "page",
                    )
                    if request.form.get(key)
                },
            )
        )
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
        "SELECT filename,thumbnail,preview FROM garment_images WHERE garment_id=?", (gid,)
    ).fetchall()
    with db:
        db.execute("DELETE FROM garments WHERE id=?", (gid,))
        db.executemany(
            "DELETE FROM image_integrity WHERE name=?",
            [(name,) for row in photos for name in row if name],
        )
    remove_files(
        current_app.config["DATA_DIR"] / "images", [name for row in photos for name in row]
    )
    flash("Prenda eliminada.", "success")
    return redirect(url_for("inventory.index"))


@bp.post("/prendas/<int:gid>/fotos/<int:image_id>/principal")
def primary_image(gid, image_id):
    garment(gid)
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM garment_images WHERE id=? AND garment_id=?", (image_id, gid)
    ).fetchone():
        abort(404)
    with db:
        db.execute("UPDATE garment_images SET is_primary=0 WHERE garment_id=?", (gid,))
        db.execute("UPDATE garment_images SET is_primary=1 WHERE id=?", (image_id,))
    flash("Fotografía principal actualizada.", "success")
    return redirect(url_for("inventory.detail", gid=gid))


@bp.post("/prendas/<int:gid>/fotos/<int:image_id>/ordenar")
def reorder_image(gid, image_id):
    garment(gid)
    direction = request.form.get("direction")
    if direction not in {"anterior", "siguiente"}:
        raise ValueError("El orden solicitado no es válido.")
    db = get_db()
    with db:
        photos = db.execute(
            "SELECT id FROM garment_images WHERE garment_id=? ORDER BY is_primary DESC, COALESCE(sort_order,id), id",
            (gid,),
        ).fetchall()
        order = [row["id"] for row in photos]
        if image_id not in order:
            abort(404)
        index = order.index(image_id)
        target = index + (-1 if direction == "anterior" else 1)
        # The cover remains first; use the separate control to change it.
        if 0 < index < len(order) and 0 < target < len(order):
            order[index], order[target] = order[target], order[index]
            db.executemany(
                "UPDATE garment_images SET sort_order=? WHERE id=? AND garment_id=?",
                [(pos, photo_id, gid) for pos, photo_id in enumerate(order)],
            )
    return redirect(url_for("inventory.detail", gid=gid))


@bp.route("/prendas/<int:gid>/fotos/<int:image_id>/eliminar", methods=["GET", "POST"])
def delete_image(gid, image_id):
    garment(gid)
    db = get_db()
    photo = db.execute(
        "SELECT * FROM garment_images WHERE id=? AND garment_id=?", (image_id, gid)
    ).fetchone()
    if not photo:
        abort(404)
    if request.method == "GET":
        return render_template(
            "confirm.html",
            title="Eliminar fotografía",
            message="Se eliminará esta fotografía de la prenda. Las demás fotografías se conservan.",
        )
    if request.form.get("confirm") != "1":
        raise ValueError("Confirma la eliminación de la fotografía.")
    with db:
        db.execute("DELETE FROM garment_images WHERE id=?", (image_id,))
        db.executemany(
            "DELETE FROM image_integrity WHERE name=?",
            [(photo[key],) for key in ("filename", "thumbnail", "preview") if photo[key]],
        )
    remove_files(
        current_app.config["DATA_DIR"] / "images",
        [photo["filename"], photo["thumbnail"], photo["preview"]],
    )
    return redirect(url_for("inventory.detail", gid=gid))


@bp.get("/imagenes/<name>")
def image(name):
    from .backups import IMAGE_NAME

    if not IMAGE_NAME.fullmatch(name):
        abort(404)
    return send_from_directory(current_app.config["DATA_DIR"] / "images", name)
