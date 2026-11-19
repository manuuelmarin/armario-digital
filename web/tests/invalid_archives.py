"""Produce malformed, fictitious ZIPs for the recovery contract."""

import hashlib
import json
import sqlite3
import warnings
import zipfile


def generate(folder):
    with zipfile.ZipFile(folder / "v9.zip") as source:
        original = {n: source.read(n) for n in source.namelist()}
    photo = next(n for n in original if n.startswith("images/"))
    for case in (
        "hash",
        "missing",
        "duplicate",
        "manifest",
        "future",
        "foreign-key",
        "cascade",
        "orphan",
        "webp",
        "baseline",
    ):
        files = dict(original)
        manifest = json.loads(files["manifest.json"])
        if case == "hash":
            manifest["files"][photo] = "0" * 64
        elif case == "missing":
            del files[photo]
            del manifest["files"][photo]
        elif case == "manifest":
            manifest["format"] = 5
        elif case == "webp":
            files[photo] = b"not an image"
            manifest["files"][photo] = hashlib.sha256(files[photo]).hexdigest()
        elif case in {"foreign-key", "cascade", "orphan", "future", "baseline"}:
            path = folder / "invalid-work.sqlite"
            path.write_bytes(files["wardrobe.sqlite"])
            with sqlite3.connect(path) as db:
                if case == "future":
                    db.execute("PRAGMA user_version=10")
                    manifest["schema_version"] = 10
                elif case == "orphan":
                    db.execute("UPDATE garments SET location_id=800")
                elif case == "baseline":
                    db.execute("UPDATE image_integrity SET sha256=?", ("0" * 64,))
                else:
                    db.execute("ALTER TABLE outfit_items RENAME TO old_items")
                    fk = (
                        ""
                        if case == "foreign-key"
                        else " REFERENCES garments(id) ON DELETE CASCADE"
                    )
                    db.execute(
                        "CREATE TABLE outfit_items(outfit_id INTEGER NOT NULL REFERENCES outfits(id) ON DELETE CASCADE,garment_id INTEGER NOT NULL"
                        + fk
                        + ", PRIMARY KEY(outfit_id,garment_id))"
                    )
                    db.execute("INSERT INTO outfit_items SELECT * FROM old_items")
                    db.execute("DROP TABLE old_items")
            db.close()
            files["wardrobe.sqlite"] = path.read_bytes()
            path.unlink()
            manifest["files"]["wardrobe.sqlite"] = hashlib.sha256(
                files["wardrobe.sqlite"]
            ).hexdigest()
        files["manifest.json"] = json.dumps(manifest).encode()
        with zipfile.ZipFile(folder / f"invalid-{case}.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
            for name, data in files.items():
                bundle.writestr(name, data)
            if case == "duplicate":
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    bundle.writestr(photo, files[photo])
