"""Synthetic HTTP-render benchmark; run with python -m tests.benchmark."""

import io
import json
import platform
import sqlite3
import statistics
import tempfile
import time
import uuid
from pathlib import Path

from PIL import Image

from armario import create_app
from armario.db import connect


def benchmark():
    results = []
    image = io.BytesIO()
    Image.new("RGB", (80, 100), "white").save(image, "WEBP")
    photo = image.getvalue()
    for count in (100, 500, 1000):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            app = create_app({"TESTING": True, "DATA_DIR": root})
            db = connect(root / "wardrobe.sqlite")
            with db:
                for number in range(count):
                    gid = db.execute(
                        "INSERT INTO garments(name,category_id,location_id) VALUES (?,2,?)",
                        (f"Prenda {number}", number % 3 + 1),
                    ).lastrowid
                    db.execute("INSERT INTO garment_seasons VALUES (?,'Verano')", (gid,))
                    token = uuid.uuid4().hex
                    names = (f"{token}.webp", f"{token}-thumb.webp")
                    for name in names:
                        (root / "images" / name).write_bytes(photo)
                    db.execute(
                        "INSERT INTO garment_images(garment_id,filename,thumbnail,digest) VALUES (?,?,?,?)",
                        (gid, *names, "synthetic"),
                    )
            db.close()
            client = app.test_client()
            measurements = {"garments": count}
            for label, route in (
                ("gallery", "/"),
                ("combined_filters", "/?location_id=2&category_id=2&season=Verano&q=PRENDA"),
            ):
                client.get(route)
                times = []
                for _ in range(30):
                    start = time.perf_counter()
                    response = client.get(route)
                    times.append((time.perf_counter() - start) * 1000)
                    assert response.status_code == 200
                measurements[label] = {
                    "median_ms": round(statistics.median(times), 2),
                    "p95_ms": round(sorted(times)[28], 2),
                }
            results.append(measurements)
    return {
        "python": platform.python_version(),
        "platform": platform.system(),
        "sqlite": sqlite3.sqlite_version,
        "samples": 30,
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(benchmark(), indent=2))
