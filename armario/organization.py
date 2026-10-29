"""Local tags and collections; adding to a collection never moves garments."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .db import get_db
from .domain import ids, text_value, validate_garments
from .queries import GARMENT_SELECT, active_garments

bp = Blueprint("organization", __name__)


@bp.get("/colecciones")
def index():
    db = get_db()
    collections = db.execute(
        "SELECT c.*, count(i.garment_id) total FROM collections c LEFT JOIN collection_items i ON i.collection_id=c.id GROUP BY c.id ORDER BY c.name"
    ).fetchall()
    tags = db.execute(
        "SELECT t.*, count(gt.garment_id) total FROM tags t LEFT JOIN garment_tags gt ON gt.tag_id=t.id GROUP BY t.id ORDER BY t.name"
    ).fetchall()
    return render_template("organization.html", collections=collections, tags=tags)


@bp.post("/colecciones/nueva")
def create_collection():
    db = get_db()
    with db:
        cid = db.execute(
            "INSERT INTO collections(name,notes) VALUES (?,?)",
            (text_value(request.form, "name", 100, True), text_value(request.form, "notes", 3000)),
        ).lastrowid
    return redirect(url_for("organization.collection", cid=cid))


@bp.get("/colecciones/<int:cid>")
def collection(cid):
    db = get_db()
    from .queries import entity

    collection = entity("collections", cid)
    items = db.execute(
        GARMENT_SELECT
        + " JOIN collection_items ci ON ci.garment_id=g.id WHERE ci.collection_id=? ORDER BY g.id DESC",
        (cid,),
    ).fetchall()
    return render_template(
        "collection.html",
        collection=collection,
        items=items,
        garments=active_garments(),
        selected=[x["id"] for x in items],
    )


@bp.post("/colecciones/<int:cid>/guardar")
def save_collection(cid):
    from .queries import entity

    entity("collections", cid)
    db = get_db()
    chosen = ids(request.form.getlist("garment_ids"))
    existing = {
        row[0]
        for row in db.execute(
            "SELECT garment_id FROM collection_items WHERE collection_id=?", (cid,)
        )
    }
    for item in validate_garments(db, chosen, active=False) if chosen else []:
        if item["archived"] and item["id"] not in existing:
            raise ValueError("No puedes añadir prendas archivadas.")
    # Keep archived members, which are absent from the active picker.
    archived = {
        row[0]
        for row in db.execute(
            "SELECT g.id FROM garments g JOIN collection_items i ON i.garment_id=g.id WHERE i.collection_id=? AND g.archived=1",
            (cid,),
        )
    }
    with db:
        db.execute(
            "UPDATE collections SET name=?,notes=? WHERE id=?",
            (
                text_value(request.form, "name", 100, True),
                text_value(request.form, "notes", 3000),
                cid,
            ),
        )
        db.execute("DELETE FROM collection_items WHERE collection_id=?", (cid,))
        db.executemany(
            "INSERT INTO collection_items VALUES (?,?)",
            [(cid, gid) for gid in sorted(set(chosen) | archived)],
        )
    flash("Colección guardada. Las prendas conservan su ubicación.", "success")
    return redirect(url_for("organization.collection", cid=cid))


@bp.post("/etiquetas/nueva")
def create_tag():
    db = get_db()
    with db:
        db.execute(
            "INSERT INTO tags(name) VALUES (?)", (text_value(request.form, "name", 60, True),)
        )
    return redirect(url_for("organization.index"))


@bp.post("/etiquetas/<int:tid>/guardar")
def save_tag(tid):
    from .queries import entity

    entity("tags", tid)
    db = get_db()
    chosen = ids(request.form.getlist("garment_ids"))
    if chosen:
        validate_garments(db, chosen, active=False)
    with db:
        db.executemany(
            "INSERT OR IGNORE INTO garment_tags VALUES (?,?)", [(gid, tid) for gid in chosen]
        )
    flash("Etiqueta añadida a las prendas seleccionadas.", "success")
    return redirect(url_for("organization.index"))


@bp.get("/etiquetas/<int:tid>")
def tag(tid):
    from .queries import entity

    db = get_db()
    item = entity("tags", tid)
    selected = [
        row[0] for row in db.execute("SELECT garment_id FROM garment_tags WHERE tag_id=?", (tid,))
    ]
    return render_template("tag.html", tag=item, garments=active_garments(), selected=selected)


@bp.post("/etiquetas/<int:tid>/actualizar")
def update_tag(tid):
    from .queries import entity

    entity("tags", tid)
    db = get_db()
    chosen = ids(request.form.getlist("garment_ids"))
    existing = {
        row[0] for row in db.execute("SELECT garment_id FROM garment_tags WHERE tag_id=?", (tid,))
    }
    for item in validate_garments(db, chosen, active=False) if chosen else []:
        if item["archived"] and item["id"] not in existing:
            raise ValueError("No puedes añadir prendas archivadas.")
    archived = {
        r[0]
        for r in db.execute(
            "SELECT g.id FROM garments g JOIN garment_tags gt ON gt.garment_id=g.id WHERE gt.tag_id=? AND g.archived=1",
            (tid,),
        )
    }
    with db:
        db.execute(
            "UPDATE tags SET name=? WHERE id=?", (text_value(request.form, "name", 60, True), tid)
        )
        db.execute("DELETE FROM garment_tags WHERE tag_id=?", (tid,))
        db.executemany(
            "INSERT INTO garment_tags VALUES (?,?)",
            [(gid, tid) for gid in sorted(set(chosen) | archived)],
        )
    return redirect(url_for("organization.index"))


@bp.post("/organizacion/<kind>/<int:item_id>/eliminar")
def delete(kind, item_id):
    if kind not in {"coleccion", "etiqueta"} or request.form.get("confirm") != "1":
        raise ValueError("Confirma la eliminación.")
    table = "collections" if kind == "coleccion" else "tags"
    from .queries import entity

    entity(table, item_id)
    db = get_db()
    with db:
        db.execute(f"DELETE FROM {table} WHERE id=?", (item_id,))
    flash("Elemento eliminado. Las prendas se conservan.", "success")
    return redirect(url_for("organization.index"))
