"""Synthetic archives and business-row oracle shared by browser and Python."""

import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

from invalid_archives import generate
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from armario.backups import create_backup, digest, restore_backup, verify_backup  # noqa: E402
from armario.db import connect, migrate  # noqa: E402


def snapshot(path):
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return {
            row[0]: [dict(item) for item in db.execute(f'SELECT * FROM "{row[0]}" ORDER BY rowid')]
            for row in tables
        }


def create_fixtures(target):
    target.mkdir(parents=True, exist_ok=True)
    for color in ("red", "green", "blue"):
        Image.new("RGB", (36, 24), color).save(target / f"{color}.jpg")
    for version in range(1, 10):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            images = source / "images"
            images.mkdir()
            names = ["1" * 32 + part + ".webp" for part in ("", "-thumb")]
            for name in names:
                Image.new("RGB", (16, 24), "green").save(images / name)
            db = connect(source / "wardrobe.sqlite")
            with db:
                for script in sorted((ROOT / "armario/migrations").glob("*.sql"))[:version]:
                    db.executescript(script.read_text(encoding="utf-8"))
                db.execute(f"PRAGMA user_version={version}")
                db.executescript(
                    "INSERT INTO locations(name) VALUES('Madrid'),('Albacete'); INSERT INTO garments(name,category_id,location_id,price_cents) VALUES('Camisa heredada',2,1,3500); INSERT INTO outfits(name) VALUES('Conjunto'); INSERT INTO outfit_items VALUES(1,1); INSERT INTO garment_seasons VALUES(1,'Verano');"
                )
                db.execute(
                    "INSERT INTO garment_images(garment_id,filename,thumbnail,digest) VALUES(1,?,?,?)",
                    (*names, digest(images / names[0])),
                )
                if version >= 2:
                    db.executescript(
                        "INSERT INTO trips(name,origin_id,destination_id) VALUES('Viaje',1,2); INSERT INTO trip_items(trip_id,garment_id) VALUES(1,1);"
                    )
                if version >= 5:
                    db.executemany(
                        "INSERT INTO image_integrity VALUES(?,?)",
                        [(n, digest(images / n)) for n in names],
                    )
                if version >= 6:
                    db.executescript(
                        "INSERT INTO tags(name) VALUES('Trabajo'); INSERT INTO garment_tags VALUES(1,1); INSERT INTO collections(name) VALUES('Cápsula'); INSERT INTO collection_items VALUES(1,1);"
                    )
                if version >= 7:
                    db.execute("INSERT INTO boards(name) VALUES('Ideas')")
                    db.execute(
                        "INSERT INTO board_items(board_id,caption,filename,thumbnail,x,y,width) VALUES(1,'Prueba',?,?,34,122,310)",
                        names,
                    )
                if version >= 9:
                    db.executescript(
                        "INSERT INTO ai_jobs(kind,prompt_version,input_json) VALUES('vision','histórico','{}'); INSERT INTO garment_profiles(garment_id,revision,profile_json,provenance_json) VALUES(1,1,'{}','{}'); INSERT INTO outfit_origins VALUES(1,'{}');"
                    )
            db.close()
            archive = create_backup(source, expected_version=version)
            shutil.copyfile(archive, target / f"v{version}.zip")
            migrate(source)
            (target / f"v{version}.json").write_text(
                json.dumps(snapshot(source / "wardrobe.sqlite")), encoding="utf-8"
            )

    generate(target)


def roundtrip(file):
    verify_backup(file)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "armario"
        restore_backup(file, root)
        state = snapshot(root / "wardrobe.sqlite")
        assert len(state["garments"]) >= 1
        for photo in state["garment_images"]:
            for col in ("filename", "preview", "thumbnail"):
                if photo[col]:
                    path = root / "images" / photo[col]
                    entry = next(r for r in state["image_integrity"] if r["name"] == photo[col])
                    assert digest(path) == entry["sha256"]


if __name__ == "__main__":
    (create_fixtures if sys.argv[1] == "fixtures" else roundtrip)(Path(sys.argv[2]).resolve())
