"""Validation and operations shared by inventory, outfits and packing lists."""

from datetime import date
from decimal import Decimal, InvalidOperation

SEASONS = ("Primavera", "Verano", "Otoño", "Invierno")


def text_value(form, key, limit=120, required=False):
    value = form.get(key, "").strip()
    if required and not value:
        raise ValueError("Completa los campos obligatorios.")
    if len(value) > limit:
        raise ValueError(f"El campo {key} supera los {limit} caracteres.")
    return value


def ids(values):
    try:
        result = sorted({int(v) for v in values})
    except (ValueError, TypeError) as exc:
        raise ValueError("La selección no es válida.") from exc
    if any(v < 1 for v in result) or len(result) > 1000:
        raise ValueError("Selecciona entre 1 y 1.000 elementos válidos.")
    return result


def identifier(form, key):
    result = ids([form.get(key)])
    return result[0]


def date_value(form, key):
    value = form.get(key, "").strip()
    if value:
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise ValueError("Introduce una fecha válida.") from exc
    return None


def price_value(form):
    value = form.get("price", "").strip().replace(",", ".")
    if not value:
        return None
    try:
        number = Decimal(value)
        if not number.is_finite() or number < 0 or number > 1_000_000:
            raise ValueError("El precio debe estar entre 0 y 1.000.000 €.")
        if number != number.quantize(Decimal("0.01")):
            raise ValueError("El precio admite dos decimales.")
        return int(number * 100)
    except InvalidOperation as exc:
        raise ValueError("El precio no es válido.") from exc


def validate_garments(db, garment_ids, active=True):
    if not garment_ids:
        raise ValueError("Selecciona al menos una prenda.")
    marks = ",".join("?" for _ in garment_ids)
    rows = db.execute(f"SELECT * FROM garments WHERE id IN ({marks})", garment_ids).fetchall()
    if len(rows) != len(garment_ids) or (active and any(row["archived"] for row in rows)):
        raise ValueError("La selección contiene prendas eliminadas o archivadas. Revísala.")
    return rows


def move_garments(db, garment_ids, destination_id, reason="Traslado manual"):
    if not db.execute("SELECT 1 FROM locations WHERE id=?", (destination_id,)).fetchone():
        raise ValueError("La ubicación de destino no existe.")
    rows = validate_garments(db, garment_ids)
    changed = 0
    for garment in rows:
        if garment["location_id"] == destination_id:
            continue
        db.execute("UPDATE garments SET location_id=? WHERE id=?", (destination_id, garment["id"]))
        db.execute(
            "INSERT INTO garment_movements(garment_id,from_id,to_id,reason) VALUES (?,?,?,?)",
            (garment["id"], garment["location_id"], destination_id, reason),
        )
        changed += 1
    return changed


def add_trip_garments(db, trip_id, garment_ids):
    validate_garments(db, garment_ids)
    db.executemany(
        "INSERT OR IGNORE INTO trip_items(trip_id,garment_id) VALUES (?,?)",
        [(trip_id, gid) for gid in garment_ids],
    )
