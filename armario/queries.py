from flask import abort

from .db import get_db

GARMENT_SELECT = """
 SELECT g.*, c.name category_name, l.name location_name,
 img.thumbnail, img.filename, img.preview, img.width, img.height,
 img.preview_width, img.thumbnail_width
 FROM garments g
 JOIN categories c ON c.id=g.category_id
 JOIN locations l ON l.id=g.location_id
 LEFT JOIN garment_images img ON img.id=(SELECT min(id) FROM garment_images WHERE garment_id=g.id)
"""


def garment(gid):
    row = get_db().execute(GARMENT_SELECT + " WHERE g.id=?", (gid,)).fetchone()
    if row is None:
        abort(404, "Esta prenda no existe.")
    return row


def entity(table, item_id):
    if table not in {"outfits", "trips", "locations"}:
        raise ValueError("Unsupported entity type")
    row = get_db().execute(f"SELECT * FROM {table} WHERE id=?", (item_id,)).fetchone()
    if row is None:
        abort(404, "Este elemento no existe.")
    return row


def active_garments():
    return get_db().execute(GARMENT_SELECT + " WHERE g.archived=0 ORDER BY g.name,g.id").fetchall()
