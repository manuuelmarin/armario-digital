from flask import abort

from .db import get_db

GARMENT_SELECT = """
 SELECT g.*, c.name category_name, l.name location_name,
 (SELECT thumbnail FROM garment_images WHERE garment_id=g.id ORDER BY id LIMIT 1) thumbnail
 FROM garments g JOIN categories c ON c.id=g.category_id JOIN locations l ON l.id=g.location_id
"""


def garment(gid):
    row = get_db().execute(GARMENT_SELECT + " WHERE g.id=?", (gid,)).fetchone()
    if row is None:
        abort(404, "Esta prenda no existe.")
    return row


def entity(table, item_id):
    assert table in {"outfits", "trips", "locations"}
    row = get_db().execute(f"SELECT * FROM {table} WHERE id=?", (item_id,)).fetchone()
    if row is None:
        abort(404, "Este elemento no existe.")
    return row


def active_garments():
    return get_db().execute(GARMENT_SELECT + " WHERE g.archived=0 ORDER BY g.name,g.id").fetchall()
