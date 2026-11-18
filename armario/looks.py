import json

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .db import get_db
from .domain import ids, text_value, validate_garments
from .queries import GARMENT_SELECT, active_garments, entity

bp = Blueprint("looks", __name__)


@bp.get("/outfits")
def index():
    db = get_db()
    search = text_value(request.args, "q")
    favorite = request.args.get("favorite") == "1"
    outfits = [
        dict(row)
        for row in db.execute(
            "SELECT * FROM outfits WHERE (?='' OR instr(fold(name || ' ' || occasion || ' ' || notes), fold(?))>0) AND (?=0 OR favorite=1) ORDER BY favorite DESC,id DESC",
            (search, search, int(favorite)),
        )
    ]
    by_id = {outfit["id"]: outfit for outfit in outfits}
    for outfit in outfits:
        outfit["items"] = []
    if outfits:
        for item in db.execute(
            GARMENT_SELECT.replace("SELECT g.*", "SELECT i.outfit_id, g.*")
            + " JOIN outfit_items i ON i.garment_id=g.id ORDER BY i.outfit_id,g.id"
        ):
            if item["outfit_id"] in by_id:
                by_id[item["outfit_id"]]["items"].append(item)
    place_id = request.args.get("location_id", type=int)
    place = entity("locations", place_id) if place_id else None
    complete_only = request.args.get("complete") == "1"
    if place:
        for outfit in outfits:
            outfit["missing"] = [
                item
                for item in outfit["items"]
                if item["archived"] or item["location_id"] != place_id
            ]
        if complete_only:
            outfits = [o for o in outfits if o["items"] and not o["missing"]]
    return render_template(
        "outfits.html",
        outfits=outfits,
        search=search,
        favorite=favorite,
        place=place,
        complete_only=complete_only,
    )


@bp.get("/outfits/<int:oid>")
def detail(oid):
    outfit = entity("outfits", oid)
    items = (
        get_db()
        .execute(
            GARMENT_SELECT
            + " JOIN outfit_items i ON i.garment_id=g.id WHERE i.outfit_id=? ORDER BY g.id",
            (oid,),
        )
        .fetchall()
    )
    origin = (
        get_db()
        .execute("SELECT provenance_json FROM outfit_origins WHERE outfit_id=?", (oid,))
        .fetchone()
    )
    return render_template(
        "outfit_detail.html",
        outfit=outfit,
        items=items,
        origin=json.loads(origin[0]) if origin else None,
    )


@bp.post("/outfits/<int:oid>/duplicar")
def duplicate(oid):
    outfit = entity("outfits", oid)
    db = get_db()
    with db:
        new_id = db.execute(
            "INSERT INTO outfits(name,notes,occasion,favorite) VALUES (?,?,?,?)",
            (outfit["name"][:112] + " (copia)", outfit["notes"], outfit["occasion"], 0),
        ).lastrowid
        db.execute(
            "INSERT INTO outfit_items(outfit_id,garment_id) SELECT ?,garment_id FROM outfit_items WHERE outfit_id=?",
            (new_id, oid),
        )
    flash("Outfit duplicado. Las prendas mantienen su ubicación.", "success")
    return redirect(url_for("looks.detail", oid=new_id))


@bp.route("/outfits/nuevo", methods=["GET", "POST"])
@bp.route("/outfits/<int:oid>/editar", methods=["GET", "POST"])
def edit(oid=None):
    db = get_db()
    outfit = entity("outfits", oid) if oid else None
    selected = {
        row[0]
        for row in db.execute("SELECT garment_id FROM outfit_items WHERE outfit_id=?", (oid,))
    }
    if request.method == "POST":
        chosen = ids(request.form.getlist("garment_ids"))
        # Existing archived pieces may be kept, but cannot be newly added.
        for item in validate_garments(db, chosen, active=False):
            if item["archived"] and item["id"] not in selected:
                raise ValueError("No puedes añadir prendas archivadas.")
        fields = (
            text_value(request.form, "name", required=True),
            text_value(request.form, "notes", 3000),
            text_value(request.form, "occasion", 80),
            int(request.form.get("favorite") == "1"),
        )
        with db:
            if oid:
                db.execute(
                    "UPDATE outfits SET name=?,notes=?,occasion=?,favorite=? WHERE id=?",
                    (*fields, oid),
                )
                db.execute("DELETE FROM outfit_items WHERE outfit_id=?", (oid,))
                # A manually changed combination no longer carries the original model ratings.
                db.execute("DELETE FROM outfit_origins WHERE outfit_id=?", (oid,))
            else:
                oid = db.execute(
                    "INSERT INTO outfits(name,notes,occasion,favorite) VALUES (?,?,?,?)", fields
                ).lastrowid
            db.executemany("INSERT INTO outfit_items VALUES (?,?)", [(oid, gid) for gid in chosen])
        flash("Outfit guardado.", "success")
        return redirect(url_for("looks.index"))
    available = [dict(g) for g in active_garments()]
    if selected:
        present = {g["id"] for g in available}
        for gid in selected - present:
            available.append(dict(db.execute(GARMENT_SELECT + " WHERE g.id=?", (gid,)).fetchone()))
    return render_template("outfit_form.html", outfit=outfit, garments=available, selected=selected)


@bp.route("/outfits/<int:oid>/eliminar", methods=["GET", "POST"])
def delete(oid):
    outfit = entity("outfits", oid)
    if request.method == "GET":
        return render_template(
            "confirm.html",
            title="Eliminar outfit",
            message=f"Se eliminará la combinación {outfit['name']}. Las prendas y las maletas conservarán sus datos.",
        )
    if request.form.get("confirm") != "1":
        raise ValueError("Confirma la eliminación.")
    db = get_db()
    with db:
        db.execute("DELETE FROM outfits WHERE id=?", (oid,))
    return redirect(url_for("looks.index"))
