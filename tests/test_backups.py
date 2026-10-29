import json
import zipfile
from pathlib import Path

import pytest

from armario import create_app
from armario.backups import create_backup, process_lock, restore_backup, verify_backup
from armario.db import connect, migrate

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
        "schema_version": 2,
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
    assert len(list((target / "images").glob("*.webp"))) == 2


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
    with db:
        db.execute("PRAGMA user_version=1")
        db.execute("INSERT INTO garments(name,category_id,location_id) VALUES ('Anterior',1,1)")
        db.execute("INSERT INTO outfits(name) VALUES ('Anterior')")
        db.execute("INSERT INTO outfit_items VALUES (1,1)")
    db.close()
    migrate(root)
    with connect(root / "wardrobe.sqlite") as after:
        assert after.execute("PRAGMA user_version").fetchone()[0] == 2
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
