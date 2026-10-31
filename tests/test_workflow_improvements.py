from urllib.parse import parse_qs, urlsplit

from armario.backups import create_backup

from .conftest import photograph, post


def test_bulk_category_review_and_atomic_validation(client, add_garment, db):
    first, second = add_garment("Uno"), add_garment("Dos", location=2)
    review = post(client, "/prendas/editar-lote", {"garment_ids": [str(first), str(second)]})
    assert b"Uno" in review.data and b"Dos" in review.data
    assert db.execute("SELECT count(*) FROM garments WHERE category_id=3").fetchone()[0] == 0
    bad = post(
        client,
        "/prendas/editar-lote",
        {"garment_ids": [str(first), "99999"], "category_id": "3", "confirm": "1"},
    )
    assert bad.status_code == 400
    ok = post(
        client,
        "/prendas/editar-lote",
        {"garment_ids": [str(first), str(second)], "category_id": "3", "confirm": "1"},
    )
    assert ok.status_code == 302
    rows = db.execute("SELECT category_id, location_id FROM garments ORDER BY id").fetchall()
    assert [tuple(row) for row in rows] == [(3, 1), (3, 2)]


def test_batch_import_names_and_invalid_names_are_atomic(client, db):
    response = post(
        client,
        "/prendas/importar",
        {
            "category_id": "2",
            "location_id": "1",
            "photos": [photograph(), photograph("red")],
            "photo_names": ["Camisa", "Abrigo"],
        },
    )
    assert response.status_code == 302
    assert [row[0] for row in db.execute("SELECT name FROM garments ORDER BY id")] == [
        "Camisa",
        "Abrigo",
    ]
    bad = post(
        client,
        "/prendas/importar",
        {"category_id": "2", "location_id": "1", "photos": [photograph()], "photo_names": [" "]},
    )
    assert bad.status_code == 400
    assert db.execute("SELECT count(*) FROM garments").fetchone()[0] == 2


def test_favorite_keeps_collection_filters(client, add_garment):
    gid = add_garment()
    result = post(
        client,
        f"/prendas/{gid}/favorito",
        {"return_view": "inventory", "tag_id": "2", "collection_id": "3", "q": "azul"},
    )
    query = parse_qs(urlsplit(result.location).query)
    assert query["tag_id"] == ["2"] and query["collection_id"] == ["3"] and query["q"] == ["azul"]


def test_backup_verification_valid_invalid_and_symlink(client, app, tmp_path):
    archive = create_backup(app.config["DATA_DIR"])
    response = post(client, f"/copias/{archive.name}/verificar", follow_redirects=True)
    assert response.status_code == 200 and b"Copia verificada" in response.data
    broken = archive.parent / "broken.zip"
    broken.write_bytes(b"bad")
    assert post(client, "/copias/broken.zip/verificar").status_code == 400
    link = archive.parent / "link.zip"
    try:
        link.symlink_to(archive)
    except (OSError, NotImplementedError):
        return
    assert post(client, "/copias/link.zip/verificar").status_code == 404


def test_review_move_does_not_change_location_until_confirmed(client, add_garment, db):
    gid = add_garment("Prenda", location=1)
    review = post(
        client, "/prendas/traslado/revisar", {"garment_ids": [str(gid)], "destination_id": "2"}
    )
    assert review.status_code == 200 and b"Espacio A" in review.data and b"Espacio B" in review.data
    assert db.execute("SELECT location_id FROM garments WHERE id=?", (gid,)).fetchone()[0] == 1
    assert (
        post(
            client, "/prendas/mover", {"garment_ids": [str(gid)], "destination_id": "2"}
        ).status_code
        == 302
    )
    assert db.execute("SELECT location_id FROM garments WHERE id=?", (gid,)).fetchone()[0] == 2
    assert db.execute("SELECT count(*) FROM garment_movements").fetchone()[0] == 1


def test_photo_removal_requires_confirmation(client, add_garment, db):
    gid = add_garment(photos=photograph())
    image = db.execute("SELECT id FROM garment_images WHERE garment_id=?", (gid,)).fetchone()[0]
    url = f"/prendas/{gid}/fotos/{image}/eliminar"
    assert client.get(url).status_code == 200
    assert post(client, url).status_code == 400
    assert db.execute("SELECT count(*) FROM garment_images").fetchone()[0] == 1
    assert post(client, url, {"confirm": "1"}).status_code == 302
    assert db.execute("SELECT count(*) FROM garment_images").fetchone()[0] == 0


def test_bulk_adds_season_and_tag_without_replacing_existing(client, add_garment, db):
    gid = add_garment(seasons=["Verano"])
    with db:
        db.execute("INSERT INTO tags(name) VALUES ('Viaje')")
    assert (
        post(
            client,
            "/prendas/editar-lote",
            {"garment_ids": [str(gid)], "season": "Invierno", "tag_id": "1", "confirm": "1"},
        ).status_code
        == 302
    )
    assert {
        r[0] for r in db.execute("SELECT season FROM garment_seasons WHERE garment_id=?", (gid,))
    } == {"Verano", "Invierno"}
    assert (
        db.execute(
            "SELECT count(*) FROM garment_tags WHERE garment_id=? AND tag_id=1", (gid,)
        ).fetchone()[0]
        == 1
    )
    bad = post(
        client,
        "/prendas/editar-lote",
        {"garment_ids": [str(gid)], "season": "Marte", "tag_id": "1", "confirm": "1"},
    )
    assert bad.status_code == 400


def test_photo_reorder_is_scoped_and_persistent(client, add_garment, db, app):
    from armario import create_app

    gid = add_garment(photos=[photograph("red"), photograph("blue"), photograph("green")])
    ids = [
        r[0]
        for r in db.execute("SELECT id FROM garment_images WHERE garment_id=? ORDER BY id", (gid,))
    ]
    assert (
        post(
            client, f"/prendas/{gid}/fotos/{ids[2]}/ordenar", {"direction": "anterior"}
        ).status_code
        == 302
    )
    detail = (
        create_app({"TESTING": True, "DATA_DIR": app.config["DATA_DIR"]})
        .test_client()
        .get(f"/prendas/{gid}")
        .data
    )
    names = {
        r["id"]: r["filename"].encode()
        for r in db.execute("SELECT id,filename FROM garment_images")
    }
    assert detail.index(names[ids[0]]) < detail.index(names[ids[2]]) < detail.index(names[ids[1]])
    assert (
        post(client, f"/prendas/{gid}/fotos/9999/ordenar", {"direction": "anterior"}).status_code
        == 404
    )


def test_migrate_populated_v7_creates_recoverable_backup(client, add_garment, db, app):
    from armario.db import SCHEMA_VERSION, migrate

    gid = add_garment(photos=photograph())
    with db:
        for table in ("outfit_origins", "ai_jobs", "garment_profiles", "ai_settings"):
            db.execute(f"DROP TABLE {table}")
        db.execute("ALTER TABLE garment_images DROP COLUMN sort_order")
        db.execute("PRAGMA user_version=7")
    migrate(app.config["DATA_DIR"])
    backup = next((app.config["DATA_DIR"] / "backups").glob("before-schema-7-*.zip"))
    from armario.backups import verify_backup

    assert verify_backup(backup)["schema_version"] == 7
    assert db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    assert (
        db.execute("SELECT sort_order FROM garment_images WHERE garment_id=?", (gid,)).fetchone()[0]
        is not None
    )
