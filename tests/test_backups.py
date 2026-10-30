import json
import zipfile
from pathlib import Path

import pytest

from armario import create_app
from armario.backups import create_backup, process_lock, restore_backup, verify_backup
from armario.db import SCHEMA_VERSION, connect, migrate

from .conftest import photograph, post


def test_complete_backup_restore_roundtrip(client, add_garment, db, app, tmp_path):
    gid = add_garment(photos=photograph(), seasons=["Invierno"])
    post(client, "/outfits/nuevo", {"name": "Completo", "garment_ids": [gid]})
    trip = post(client, "/maletas/nueva", {"name": "Viaje", "origin_id": 1, "destination_id": 2})
    tid = int(trip.location.rsplit("/", 1)[1])
    post(client, f"/maletas/{tid}/anadir", {"outfit_id": 1})
    response = post(client, "/copias")
    assert response.status_code == 302
    download = client.get(response.location)
    assert download.status_code == 200 and download.data.startswith(b"PK")
    path = next((app.config["DATA_DIR"] / "backups").glob("*.zip"))
    assert verify_backup(path) == {
        "schema_version": SCHEMA_VERSION,
        "garments": 1,
        "outfits": 1,
        "outfit_items": 1,
    }
    target = tmp_path / "restored"
    restored, old = restore_backup(path, target)
    assert restored["garments"] == 1 and old is None
    new = create_app({"TESTING": True, "DATA_DIR": target}).test_client()
    assert b"Camisa azul" in new.get("/").data
    assert b"Completo" in new.get("/outfits").data
    assert b"Camisa azul" in new.get(f"/maletas/{tid}").data
    with connect(target / "wardrobe.sqlite") as restored_db:
        assert restored_db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert restored_db.execute("SELECT count(*) FROM trip_items").fetchone()[0] == 1
    assert len(list((target / "images").glob("*.webp"))) == 3


def test_restore_preserves_existing_directory(app, add_garment):
    add_garment()
    root = app.config["DATA_DIR"]
    path = create_backup(root)
    db = connect(root / "wardrobe.sqlite")
    with db:
        db.execute("UPDATE garments SET name='Posterior'")
    db.close()
    _, previous = restore_backup(path, root)
    assert previous.exists()
    with connect(root / "wardrobe.sqlite") as db:
        assert db.execute("SELECT name FROM garments").fetchone()[0] == "Camisa azul"
    with connect(previous / "wardrobe.sqlite") as db:
        assert db.execute("SELECT name FROM garments").fetchone()[0] == "Posterior"
    assert list((previous / "backups").glob("before-restore-*.zip"))


def modified_archive(original, target, modify):
    with zipfile.ZipFile(original) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    modify(files)
    with zipfile.ZipFile(target, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return target


@pytest.mark.parametrize(
    "case", ["hash", "traversal", "missing_photo", "version", "extra", "manifest"]
)
def test_invalid_backup_never_overwrites_existing_data(app, add_garment, tmp_path, case):
    add_garment(photos=photograph())
    root = app.config["DATA_DIR"]
    path = create_backup(root)

    def mutate(files):
        manifest = json.loads(files["manifest.json"])
        if case == "hash":
            files["wardrobe.sqlite"] += b"tamper"
        elif case == "traversal":
            files["../outside.txt"] = b"bad"
            manifest["files"]["../outside.txt"] = "a" * 64
        elif case == "missing_photo":
            del files[next(name for name in files if name.startswith("images/"))]
        elif case == "version":
            manifest["schema_version"] = 999
        elif case == "extra":
            files["unexpected"] = b"bad"
        elif case == "manifest":
            manifest["format"] = 42
        files["manifest.json"] = json.dumps(manifest).encode()

    broken = modified_archive(path, tmp_path / "broken.zip", mutate)
    before = (root / "wardrobe.sqlite").read_bytes()
    with pytest.raises(ValueError):
        restore_backup(broken, root)
    assert (root / "wardrobe.sqlite").read_bytes() == before
    assert not (tmp_path / "outside.txt").exists()


def test_missing_photo_aborts_backup_without_partial_archive(app, add_garment):
    add_garment(photos=photograph())
    root = app.config["DATA_DIR"]
    next((root / "images").glob("*.webp")).unlink()
    with pytest.raises(FileNotFoundError):
        create_backup(root)
    assert not list((root / "backups").iterdir())


def test_populated_v1_migration_preserves_relations_and_backs_up(tmp_path):
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "images").mkdir()
    script = Path(__file__).parents[1] / "armario" / "migrations" / "001_core.sql"
    db = connect(root / "wardrobe.sqlite")
    db.executescript(script.read_text(encoding="utf-8"))
    db.execute("INSERT INTO locations(name) VALUES ('Espacio anterior')")
    db.commit()
    with db:
        db.execute("PRAGMA user_version=1")
        db.execute("INSERT INTO garments(name,category_id,location_id) VALUES ('Anterior',1,1)")
        db.execute("INSERT INTO outfits(name) VALUES ('Anterior')")
        db.execute("INSERT INTO outfit_items VALUES (1,1)")
    db.close()
    migrate(root)
    with connect(root / "wardrobe.sqlite") as after:
        assert after.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert after.execute("SELECT count(*) FROM outfit_items").fetchone()[0] == 1
        assert after.execute("SELECT name FROM garments").fetchone()[0] == "Anterior"
        assert after.execute("PRAGMA foreign_key_check").fetchall() == []
    backup = next((root / "backups").glob("before-schema-1-*.zip"))
    assert verify_backup(backup)["schema_version"] == 1


def test_newer_schema_rejected_unchanged(app):
    root = app.config["DATA_DIR"]
    with connect(root / "wardrobe.sqlite") as db:
        db.execute("PRAGMA user_version=999")
    with pytest.raises(RuntimeError):
        migrate(root)
    with connect(root / "wardrobe.sqlite") as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 999


def test_process_lock_prevents_parallel_server_or_restore(tmp_path):
    root = tmp_path / "exclusive"
    with process_lock(root):
        with pytest.raises(RuntimeError):
            with process_lock(root):
                pass
    with process_lock(root):
        pass


def test_restore_preserves_corrupt_database_and_restores_valid_copy(app, add_garment):
    add_garment(photos=photograph())
    root = app.config["DATA_DIR"]
    backup = create_backup(root)
    broken = b"corrupt database contents"
    (root / "wardrobe.sqlite").write_bytes(broken)
    result, previous = restore_backup(backup, root)
    assert result["garments"] == 1
    assert (previous / "wardrobe.sqlite").read_bytes() == broken
    assert verify_backup(previous / "backups" / backup.name)["garments"] == 1


def test_backup_rejects_corrupted_referenced_image(app, add_garment):
    add_garment(photos=photograph())
    root = app.config["DATA_DIR"]
    next((root / "images").glob("*.webp")).write_bytes(b"damaged image")
    with pytest.raises(ValueError, match="imagen"):
        create_backup(root)
    assert not list((root / "backups").glob("*.zip"))
    assert not list((root / "backups").glob("*.partial"))


def test_backup_creation_respects_restore_size_limit(app, add_garment, monkeypatch):
    import armario.backups as backups

    add_garment()
    root = app.config["DATA_DIR"]
    monkeypatch.setattr(backups, "MAX_UNPACKED_BYTES", 256)
    with pytest.raises(ValueError, match="límite"):
        create_backup(root)
    assert not list((root / "backups").glob("*.zip"))


def test_backup_rejects_a_valid_but_modified_image(client, add_garment, db, app):
    from PIL import Image

    add_garment(photos=photograph())
    name = db.execute("SELECT thumbnail FROM garment_images").fetchone()[0]
    path = app.config["DATA_DIR"] / "images" / name
    Image.new("RGB", (60, 60), "red").save(path, "WEBP")
    with pytest.raises(ValueError, match="huella original"):
        create_backup(app.config["DATA_DIR"])


def test_prune_daily_copies_keeps_manual_and_migration_copies(client, app, monkeypatch):
    folder = app.config["DATA_DIR"] / "backups"
    folder.mkdir(exist_ok=True)
    for name in (
        "daily-20260101.zip",
        "daily-20260102.zip",
        "manual-20260101.zip",
        "before-schema-4.zip",
    ):
        (folder / name).write_bytes(b"test")
    assert post(client, "/copias/limpiar", {"keep": "1"}).status_code == 400
    assert post(client, "/copias/limpiar", {"keep": "1", "confirm": "1"}).status_code == 400
    assert (folder / "daily-20260101.zip").exists()
    monkeypatch.setattr("armario.settings.verify_backup", lambda path: {})
    assert post(client, "/copias/limpiar", {"keep": "1", "confirm": "1"}).status_code == 302
    assert not (folder / "daily-20260101.zip").exists()
    assert (folder / "daily-20260102.zip").exists()
    assert (folder / "manual-20260101.zip").exists()
    assert (folder / "before-schema-4.zip").exists()
