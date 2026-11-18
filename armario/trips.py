from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .db import get_db
from .domain import add_trip_garments, date_value, identifier, ids, move_garments, text_value
from .queries import GARMENT_SELECT, entity

bp = Blueprint("trips", __name__)


def trip_items(tid):
    return (
        get_db()
        .execute(
            """
        SELECT i.*,g.name,g.archived,g.location_id,l.name location_name,
        (SELECT thumbnail FROM garment_images WHERE garment_id=g.id ORDER BY is_primary DESC, id LIMIT 1) thumbnail
        FROM trip_items i LEFT JOIN garments g ON g.id=i.garment_id
        LEFT JOIN locations l ON l.id=g.location_id WHERE trip_id=? ORDER BY i.id
    """,
            (tid,),
        )
        .fetchall()
    )


@bp.get("/maletas")
def index():
    trips = (
        get_db()
        .execute("""
        SELECT t.*,a.name origin,b.name destination,
        (SELECT count(*) FROM trip_items WHERE trip_id=t.id) total,
        (SELECT count(*) FROM trip_items WHERE trip_id=t.id AND packed=1) packed
        FROM trips t JOIN locations a ON a.id=t.origin_id JOIN locations b ON b.id=t.destination_id
        ORDER BY t.id DESC
    """)
        .fetchall()
    )
    return render_template("trips.html", trips=trips)


@bp.route("/maletas/nueva", methods=["GET", "POST"])
@bp.route("/maletas/<int:tid>/editar", methods=["GET", "POST"])
def edit(tid=None):
    trip = entity("trips", tid) if tid else None
    if request.method == "POST":
        origin, destination = (
            identifier(request.form, "origin_id"),
            identifier(request.form, "destination_id"),
        )
        if origin == destination:
            raise ValueError("El origen y el destino deben ser distintos.")
        starts, ends = date_value(request.form, "starts_on"), date_value(request.form, "ends_on")
        if starts and ends and ends < starts:
            raise ValueError("La fecha de vuelta debe ser posterior a la de salida.")
        fields = (
            text_value(request.form, "name", required=True),
            origin,
            destination,
            starts,
            ends,
            text_value(request.form, "notes", 3000),
        )
        db = get_db()
        with db:
            if tid:
                db.execute(
                    "UPDATE trips SET name=?,origin_id=?,destination_id=?,starts_on=?,ends_on=?,notes=? WHERE id=?",
                    (*fields, tid),
                )
            else:
                tid = db.execute(
                    "INSERT INTO trips(name,origin_id,destination_id,starts_on,ends_on,notes) VALUES (?,?,?,?,?,?)",
                    fields,
                ).lastrowid
        return redirect(url_for("trips.detail", tid=tid))
    return render_template("trip_form.html", trip=trip)


@bp.get("/maletas/<int:tid>")
def detail(tid):
    trip = entity("trips", tid)
    return render_template(
        "trip_detail.html",
        trip=trip,
        items=trip_items(tid),
        outfits=get_db().execute("SELECT * FROM outfits ORDER BY name").fetchall(),
    )


@bp.get("/maletas/<int:tid>/seleccionar")
def select_garments(tid):
    trip = entity("trips", tid)
    page = max(1, request.args.get("page", 1, type=int))
    query = text_value(request.args, "q")
    rows = (
        get_db()
        .execute(
            GARMENT_SELECT
            + " WHERE g.archived=0 AND instr(fold(g.name || ' ' || g.color || ' ' || l.name || ' ' || c.name),fold(?))>0 ORDER BY g.name,g.id LIMIT 25 OFFSET ?",
            (query, (min(page, 100000) - 1) * 24),
        )
        .fetchall()
    )
    return render_template(
        "trip_picker.html", trip=trip, rows=rows[:24], more=len(rows) > 24, page=page, query=query
    )


@bp.get("/maletas/<int:tid>/imprimir")
def printable(tid):
    trip = entity("trips", tid)
    return render_template("trip_print.html", trip=trip, items=trip_items(tid))


@bp.post("/maletas/<int:tid>/duplicar")
@bp.post("/maletas/<int:tid>/vuelta", endpoint="return_trip")
def duplicate(tid):
    trip = entity("trips", tid)
    returning = request.path.endswith("/vuelta")
    origin, destination = (
        (trip["destination_id"], trip["origin_id"])
        if returning
        else (trip["origin_id"], trip["destination_id"])
    )
    suffix = " (vuelta)" if returning else " (copia)"
    db = get_db()
    with db:
        new_id = db.execute(
            "INSERT INTO trips(name,origin_id,destination_id,notes) VALUES (?,?,?,?)",
            (trip["name"][: 120 - len(suffix)] + suffix, origin, destination, trip["notes"]),
        ).lastrowid
        db.execute(
            "INSERT INTO trip_items(trip_id,garment_id,label,packed) SELECT ?,garment_id,label,0 FROM trip_items WHERE trip_id=?",
            (new_id, tid),
        )
    flash("Lista copiada sin mover prendas. Revisa sus fechas y contenido.", "success")
    return redirect(url_for("trips.detail", tid=new_id))


@bp.post("/maletas/<int:tid>/anadir")
def add(tid):
    entity("trips", tid)
    db = get_db()
    with db:
        if request.form.get("outfit_id"):
            oid = identifier(request.form, "outfit_id")
            entity("outfits", oid)
            chosen = [
                row[0]
                for row in db.execute(
                    "SELECT garment_id FROM outfit_items WHERE outfit_id=?", (oid,)
                )
            ]
            add_trip_garments(db, tid, chosen)
        elif request.form.get("label", "").strip():
            db.execute(
                "INSERT OR IGNORE INTO trip_items(trip_id,label) VALUES (?,?)",
                (tid, text_value(request.form, "label", required=True)),
            )
        else:
            add_trip_garments(db, tid, ids(request.form.getlist("garment_ids")))
    flash("Lista actualizada. Las ubicaciones no han cambiado.", "success")
    return redirect(url_for("trips.detail", tid=tid))


@bp.post("/maletas/<int:tid>/elementos/<int:iid>/<action>")
def update_item(tid, iid, action):
    entity("trips", tid)
    db = get_db()
    if action not in {"preparar", "quitar"}:
        abort(404)
    if not db.execute("SELECT 1 FROM trip_items WHERE id=? AND trip_id=?", (iid, tid)).fetchone():
        abort(404)
    with db:
        if action == "preparar":
            value = request.form.get("desired")
            if value is None:  # Forms from earlier versions toggle once.
                db.execute("UPDATE trip_items SET packed=1-packed WHERE id=?", (iid,))
            elif value in {"0", "1"}:
                db.execute("UPDATE trip_items SET packed=? WHERE id=?", (int(value), iid))
            else:
                raise ValueError("Estado no válido.")
        else:
            db.execute("DELETE FROM trip_items WHERE id=?", (iid,))
    return redirect(url_for("trips.detail", tid=tid))


@bp.route("/maletas/<int:tid>/trasladar", methods=["GET", "POST"])
def transfer(tid):
    trip, db = entity("trips", tid), get_db()
    items = trip_items(tid)
    eligible = [
        i
        for i in items
        if i["garment_id"]
        and i["packed"]
        and not i["archived"]
        and i["location_id"] == trip["origin_id"]
    ]
    if request.method == "POST":
        if request.form.get("confirm") != "1":
            raise ValueError("Confirma el cambio de ubicación.")
        chosen = ids(request.form.getlist("garment_ids"))
        if not chosen:
            raise ValueError("Selecciona las prendas que has trasladado.")
        allowed = {
            i["garment_id"]
            for i in items
            if i["garment_id"]
            and i["packed"]
            and not i["archived"]
            and i["location_id"] in {trip["origin_id"], trip["destination_id"]}
        }
        if not set(chosen).issubset(allowed):
            raise ValueError("La lista o las ubicaciones han cambiado. Revisa el traslado.")
        with db:
            changed = move_garments(db, chosen, trip["destination_id"], f"Viaje: {trip['name']}")
        flash(f"{changed} prendas trasladadas. Se han conservado tus outfits.", "success")
        return redirect(url_for("trips.detail", tid=tid))
    return render_template("transfer.html", trip=trip, eligible=eligible)


@bp.route("/maletas/<int:tid>/eliminar", methods=["GET", "POST"])
def delete(tid):
    trip = entity("trips", tid)
    if request.method == "GET":
        return render_template(
            "confirm.html",
            title="Eliminar maleta",
            message=f"Se eliminará la lista {trip['name']}. No se moverá ni eliminará ninguna prenda.",
        )
    if request.form.get("confirm") != "1":
        raise ValueError("Confirma la eliminación.")
    db = get_db()
    with db:
        db.execute("DELETE FROM trips WHERE id=?", (tid,))
    return redirect(url_for("trips.index"))
