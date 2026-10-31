"""SQLite connections and forward-only, transactional schema changes."""

import sqlite3
import unicodedata
from pathlib import Path

from flask import current_app, g

SCHEMA_VERSION = 9


def connect(path):
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 15000")
    db.create_function("fold", 1, fold, deterministic=True)
    return db


def fold(value):
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", value or "")
        if not unicodedata.combining(char)
    ).casefold()


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATA_DIR"] / "wardrobe.sqlite")
    return g.db


def close_db(error=None):
    if (db := g.pop("db", None)) is not None:
        db.close()


def migrate(root):
    from .backups import create_backup

    root.mkdir(parents=True, exist_ok=True)
    (root / "images").mkdir(exist_ok=True)
    db = connect(root / "wardrobe.sqlite")
    try:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise RuntimeError("Los datos pertenecen a una versión más reciente. Actualiza la app.")
        if version == SCHEMA_VERSION:
            return
        if version:
            create_backup(root, prefix=f"before-schema-{version}", expected_version=version)
        for number in range(version + 1, SCHEMA_VERSION + 1):
            sql = next(Path(__file__).with_name("migrations").glob(f"{number:03d}_*.sql"))
            try:
                db.executescript("BEGIN IMMEDIATE;\n" + sql.read_text(encoding="utf-8"))
                if number == 5:
                    from .backups import digest, referenced_images

                    for name in referenced_images(db):
                        db.execute(
                            "INSERT INTO image_integrity(name,sha256) VALUES (?,?)",
                            (name[7:], digest(root / name)),
                        )
                if db.execute("PRAGMA foreign_key_check").fetchall():
                    raise RuntimeError("La migración ha producido relaciones inválidas.")
                db.execute(f"PRAGMA user_version = {number}")
                db.commit()
            except Exception:
                db.rollback()
                raise
    finally:
        db.close()
