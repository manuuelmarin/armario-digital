"""Isolated example inventory with original, deterministic garment illustrations.

The demo is generated from code. It contains no imported photos or personal data.
"""

import io
from pathlib import Path

from PIL import Image, ImageDraw

from .db import connect
from .images import store_image

SAMPLES = (
    ("Camisa Oxford", "Camisas", "shirt", "#afc2ca", "Azul niebla", 1, 69),
    ("Jersey de punto", "Punto", "knit", "#d2c7b3", "Avena", 1, 89),
    ("Denim recto", "Pantalones", "pants", "#667888", "Índigo", 1, 79),
    ("Gabardina clásica", "Abrigos", "coat", "#bbaa8b", "Arena", 2, 149),
    ("Camiseta esencial", "Camisetas", "tee", "#ece8de", "Crudo", 1, 29),
    ("Zapatillas de lona", "Calzado", "shoes", "#dad1bb", "Piedra", 1, 85),
    ("Vestido midi", "Vestidos", "dress", "#a66751", "Terracota", 2, 115),
    ("Bolso de diario", "Accesorios", "bag", "#454b43", "Oliva", 1, 99),
    ("Chaqueta de trabajo", "Chaquetas", "shirt", "#6b7561", "Verde salvia", 2, 109),
    ("Pantalón de pinzas", "Pantalones", "pants", "#424d59", "Grafito", 1, 95),
    ("Sudadera relajada", "Sudaderas", "knit", "#a9a5a0", "Gris cálido", 1, 65),
    ("Camiseta de rayas", "Camisetas", "striped", "#e4dece", "Crudo y tinta", 2, 39),
)


def garment_illustration(kind: str, color: str) -> io.BytesIO:
    """Draw a flat-lay vector-style illustration on a transparent canvas."""
    image = Image.new("RGBA", (1000, 1200))
    mask = Image.new("L", image.size)
    shape = ImageDraw.Draw(mask)
    details = []
    if kind in {"shirt", "knit", "tee", "striped"}:
        short = kind in {"tee", "striped"}
        points = [
            (300, 210),
            (415, 160),
            (450, 178),
            (550, 178),
            (585, 160),
            (700, 210),
            (835, 430 if short else 770),
            (705, 490 if short else 810),
            (650, 340),
            (650, 1020),
            (350, 1020),
            (350, 340),
            (295, 490 if short else 810),
            (165, 430 if short else 770),
        ]
        shape.polygon(points, fill=255)
        details = points
    elif kind == "coat":
        details = [
            (305, 180),
            (435, 135),
            (565, 135),
            (695, 180),
            (840, 830),
            (720, 865),
            (655, 365),
            (705, 1090),
            (295, 1090),
            (345, 365),
            (280, 865),
            (160, 830),
        ]
        shape.polygon(details, fill=255)
    elif kind == "pants":
        details = [
            (300, 150),
            (700, 150),
            (730, 365),
            (660, 1090),
            (505, 1090),
            (500, 510),
            (455, 1090),
            (300, 1090),
            (270, 365),
        ]
        shape.polygon(details, fill=255)
    elif kind == "dress":
        details = [
            (370, 150),
            (440, 115),
            (475, 170),
            (525, 170),
            (560, 115),
            (630, 150),
            (660, 350),
            (580, 470),
            (790, 1060),
            (210, 1060),
            (420, 470),
            (340, 350),
        ]
        shape.polygon(details, fill=255)
    elif kind == "bag":
        shape.rounded_rectangle((225, 400, 775, 960), radius=65, fill=255)
        shape.arc((330, 170, 670, 650), 180, 360, fill=255, width=48)
        shape.rectangle((330, 390, 378, 520), fill=255)
        shape.rectangle((622, 390, 670, 520), fill=255)
    elif kind == "shoes":
        for offset in (0, 260):
            shape.rounded_rectangle((210 + offset, 270, 435 + offset, 950), radius=100, fill=255)
    base = tuple(int(color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    fabric = Image.new("RGBA", image.size)
    draw = ImageDraw.Draw(fabric)
    for y in range(image.height):
        factor = 1.035 - y / image.height * 0.10
        draw.line((0, y, 1000, y), fill=tuple(min(255, int(v * factor)) for v in base) + (255,))
    # Fine construction lines remain crisp at high density; these are illustrations.
    for x in range(0, 1000, 9 if kind == "knit" else 17):
        draw.line((x, 0, x, 1200), fill=(*base, 60), width=1)
    if kind == "striped":
        for y in range(235, 1100, 45):
            draw.rectangle((0, y, 1000, y + 12), fill="#535e65")
    image.paste(fabric, (0, 0), mask)
    draw = ImageDraw.Draw(image)
    seam = tuple(max(0, value - 28) for value in base) + (185,)
    light = tuple(min(255, value + 20) for value in base) + (230,)
    if details:
        draw.line([*details, details[0]], fill=seam, width=3, joint="curve")
    if kind == "shirt":
        draw.line((500, 190, 500, 1010), fill=seam, width=4)
        draw.polygon([(415, 160), (500, 212), (443, 300), (402, 235)], fill=light, outline=seam)
        draw.polygon([(585, 160), (500, 212), (557, 300), (598, 235)], fill=light, outline=seam)
        draw.rectangle((545, 345, 620, 430), outline=seam, width=3)
        for y in range(330, 990, 100):
            draw.ellipse((493, y, 507, y + 14), fill="#eee8dc", outline=seam)
    if kind in {"knit", "tee", "striped"}:
        draw.arc((418, 139, 582, 258), 0, 180, fill=seam, width=14)
        draw.line((357, 995, 643, 995), fill=seam, width=12)
    if kind == "pants":
        draw.rectangle((301, 153, 698, 210), outline=seam, width=5)
        draw.line((500, 210, 500, 500), fill=seam, width=4)
        draw.arc((292, 198, 450, 420), 0, 110, fill=seam, width=4)
        draw.arc((550, 198, 708, 420), 70, 180, fill=seam, width=4)
        for x in (360, 600):
            draw.line((x, 165, x, 228), fill=seam, width=10)
    if kind == "coat":
        draw.polygon([(435, 135), (493, 265), (414, 480), (360, 300)], fill=light, outline=seam)
        draw.polygon([(565, 135), (507, 265), (586, 480), (640, 300)], fill=light, outline=seam)
        draw.line((505, 350, 505, 1080), fill=seam, width=4)
        draw.rectangle((310, 630, 690, 660), fill=seam)
        for y in (530, 750, 900):
            draw.ellipse((535, y, 557, y + 22), fill="#79725f")
    if kind == "dress":
        draw.line((420, 470, 580, 470), fill=seam, width=10)
        for end in (320, 425, 575, 680):
            draw.line((500, 490, end, 1040), fill=seam, width=2)
    if kind == "bag":
        draw.rounded_rectangle((248, 425, 752, 938), radius=48, outline=light, width=3)
        draw.ellipse((474, 650, 526, 702), outline="#bca67b", width=9)
    if kind == "shoes":
        for offset in (0, 260):
            draw.rounded_rectangle(
                (225 + offset, 590, 420 + offset, 930),
                radius=80,
                fill="#ede9df",
                outline=seam,
                width=3,
            )
            draw.ellipse(
                (247 + offset, 290, 399 + offset, 540), fill="#7f817a", outline=seam, width=8
            )
            for y in range(520, 690, 35):
                draw.line((270 + offset, y, 375 + offset, y + 30), fill="#f5f1e5", width=12)
                draw.line((375 + offset, y, 270 + offset, y + 30), fill="#f5f1e5", width=12)
    stream = io.BytesIO()
    image.save(stream, "PNG")
    stream.seek(0)
    return stream


def seed_demo(root: Path) -> None:
    db = connect(root / "wardrobe.sqlite")
    try:
        if db.execute("SELECT 1 FROM garments LIMIT 1").fetchone():
            return
        with db:
            db.executemany(
                "INSERT INTO locations(name) VALUES (?)",
                [("Armario principal",), ("Temporada",), ("Estudio",)],
            )
            db.execute("INSERT OR IGNORE INTO categories(name) VALUES ('Vestidos')")
            categories = {row["name"]: row["id"] for row in db.execute("SELECT * FROM categories")}
            for index, (name, category, kind, color, label, location, price) in enumerate(SAMPLES):
                gid = db.execute(
                    "INSERT INTO garments(name,category_id,location_id,color,size,price_cents,favorite,notes) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        name,
                        categories[category],
                        location,
                        label,
                        "M",
                        price * 100,
                        int(index in {0, 1, 5}),
                        "Ejemplo ficticio con ilustración original de demostración.",
                    ),
                ).lastrowid
                photo = store_image(garment_illustration(kind, color), root / "images")
                db.execute(
                    "INSERT INTO garment_images(garment_id,filename,thumbnail,preview,digest,width,height,preview_width,thumbnail_width) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        gid,
                        *[
                            photo[key]
                            for key in (
                                "filename",
                                "thumbnail",
                                "preview",
                                "digest",
                                "width",
                                "height",
                                "preview_width",
                                "thumbnail_width",
                            )
                        ],
                    ),
                )
                db.executemany(
                    "INSERT INTO garment_seasons VALUES (?,?)",
                    [(gid, season) for season in ("Primavera", "Otoño")],
                )
            for name, occasion, items in (
                ("De diario", "Informal", (1, 3, 6, 8)),
                ("A primera hora", "Trabajo", (2, 4, 10)),
                ("Un plan de tarde", "Tiempo libre", (7, 8, 6)),
            ):
                oid = db.execute(
                    "INSERT INTO outfits(name,occasion,favorite) VALUES (?,?,1)", (name, occasion)
                ).lastrowid
                db.executemany(
                    "INSERT INTO outfit_items VALUES (?,?)", [(oid, gid) for gid in items]
                )
            tid = db.execute(
                "INSERT INTO trips(name,origin_id,destination_id,notes) VALUES ('Fin de semana',1,3,'Lista de ejemplo para explorar el flujo de preparación.')"
            ).lastrowid
            db.executemany(
                "INSERT INTO trip_items(trip_id,garment_id,packed) VALUES (?,?,?)",
                [(tid, 1, 1), (tid, 3, 1), (tid, 6, 0)],
            )
            db.execute("INSERT INTO trip_items(trip_id,label) VALUES (?, 'Neceser')", (tid,))
    finally:
        db.close()
