import io

from PIL import Image

from armario import create_app

from .conftest import photograph, post


def test_photo_metadata_filters_archive_and_restart(client, add_garment, db, app):
    gid = add_garment(
        photos=photograph(),
        seasons=["Verano", "Primavera"],
        favorite="1",
        brand="Lino",
        size="M",
        color="Azul",
        price="29,95",
    )
    row = db.execute("SELECT * FROM garments WHERE id=?", (gid,)).fetchone()
    assert row["price_cents"] == 2995
    assert row["favorite"] == 1
    assert db.execute("SELECT count(*) FROM garment_seasons").fetchone()[0] == 2
    image = db.execute("SELECT * FROM garment_images").fetchone()
    assert client.get("/imagenes/" + image["thumbnail"]).status_code == 200
    assert (
        b"Camisa azul"
        in client.get("/?location_id=1&category_id=2&season=Verano&favorite=1&q=azul").data
    )
    assert b"Camisa azul" not in client.get("/?location_id=2").data
    assert post(client, f"/prendas/{gid}/archivar").status_code == 302
    assert b"Camisa azul" not in client.get("/").data
    assert b"Camisa azul" in client.get("/?archived=1").data
    assert post(client, f"/prendas/{gid}/archivar").status_code == 302
    restarted = create_app({"TESTING": True, "DATA_DIR": app.config["DATA_DIR"]}).test_client()
    assert b"Camisa azul" in restarted.get("/").data


def test_edit_logs_move_and_removes_unselected_seasons(client, add_garment, db):
    gid = add_garment(seasons=["Verano"])
    response = post(
        client,
        f"/prendas/{gid}/editar",
        {"name": "Camisa nueva", "category_id": 2, "location_id": 2, "seasons": ["Invierno"]},
    )
    assert response.status_code == 302
    row = db.execute("SELECT * FROM garments WHERE id=?", (gid,)).fetchone()
    assert (row["name"], row["location_id"]) == ("Camisa nueva", 2)
    assert [r[0] for r in db.execute("SELECT season FROM garment_seasons")] == ["Invierno"]
    assert db.execute("SELECT count(*) FROM garment_movements").fetchone()[0] == 1


def test_invalid_fields_are_atomic(client, add_garment, db):
    gid = add_garment()
    for changes in (
        {"price": "nan"},
        {"price": "-1"},
        {"price": "2.333"},
        {"purchased_on": "2026-02-30"},
        {"seasons": ["Marte"]},
        {"name": ""},
        {"category_id": 999},
    ):
        data = {"name": "Alterada", "category_id": 2, "location_id": 2, **changes}
        assert post(client, f"/prendas/{gid}/editar", data).status_code in (400, 409)
    row = db.execute("SELECT * FROM garments WHERE id=?", (gid,)).fetchone()
    assert row["name"] == "Camisa azul" and row["location_id"] == 1
    assert db.execute("SELECT count(*) FROM garment_movements").fetchone()[0] == 0


def test_invalid_photo_rolls_back_metadata_and_files(client, app, db):
    response = post(
        client,
        "/prendas/nueva",
        {
            "name": "Fallida",
            "category_id": 2,
            "location_id": 1,
            "photos": [
                photograph(),
                (io.BytesIO(b"<svg><script>alert(1)</script></svg>"), "foto.png"),
            ],
        },
    )
    assert response.status_code == 400
    assert db.execute("SELECT count(*) FROM garments").fetchone()[0] == 0
    assert not list((app.config["DATA_DIR"] / "images").iterdir())


def test_duplicate_photo_and_orientation(client, add_garment, db, app):
    gid = add_garment(photos=photograph(orientation=6))
    assert (
        post(
            client,
            f"/prendas/{gid}/editar",
            {
                "name": "Camisa azul",
                "category_id": 2,
                "location_id": 1,
                "photos": photograph(orientation=6),
            },
        ).status_code
        == 302
    )
    assert db.execute("SELECT count(*) FROM garment_images").fetchone()[0] == 1
    assert len(list((app.config["DATA_DIR"] / "images").iterdir())) == 3
    row = db.execute("SELECT * FROM garment_images").fetchone()
    with Image.open(app.config["DATA_DIR"] / "images" / row["filename"]) as image:
        assert image.size == (1000, 800)
        assert not image.getexif()
    with Image.open(app.config["DATA_DIR"] / "images" / row["thumbnail"]) as image:
        assert max(image.size) <= 560


def test_image_size_and_count_limits(client, add_garment, app, monkeypatch):
    from armario import images

    monkeypatch.setattr(images, "MAX_IMAGE_BYTES", 10)
    assert (
        post(
            client,
            "/prendas/nueva",
            {"name": "Grande", "category_id": 1, "location_id": 1, "photos": photograph()},
        ).status_code
        == 400
    )
    monkeypatch.setattr(images, "MAX_IMAGE_BYTES", 10 * 1024**2)
    monkeypatch.setattr(images, "MAX_PIXELS", 20)
    assert (
        post(
            client,
            "/prendas/nueva",
            {"name": "Grande", "category_id": 1, "location_id": 1, "photos": photograph()},
        ).status_code
        == 400
    )
    response = post(
        client,
        "/prendas/nueva",
        {
            "name": "Muchas",
            "category_id": 1,
            "location_id": 1,
            "photos": [photograph() for _ in range(7)],
        },
    )
    assert response.status_code == 400


def test_six_valid_photos_can_exceed_old_total_request_limit(client):
    # JPEG decoders allow trailing bytes; use padding to exercise the multipart limit.
    raw, _ = photograph()
    jpeg = raw.getvalue() + b"\0" * (6 * 1024 * 1024)
    response = post(
        client,
        "/prendas/nueva",
        {
            "name": "Prenda con fotos",
            "category_id": 1,
            "location_id": 1,
            "photos": [(io.BytesIO(jpeg), f"foto{i}.jpg") for i in range(6)],
        },
    )
    assert response.status_code == 302


def test_bulk_move_is_atomic_and_preserves_outfits(client, add_garment, db):
    first, second = add_garment(), add_garment("Pantalón")
    assert (
        post(
            client, "/outfits/nuevo", {"name": "Oficina", "garment_ids": [first, second]}
        ).status_code
        == 302
    )
    assert (
        post(
            client, "/prendas/mover", {"garment_ids": [first, 999], "destination_id": 2}
        ).status_code
        == 400
    )
    assert db.execute("SELECT count(*) FROM garment_movements").fetchone()[0] == 0
    for _ in range(2):
        assert (
            post(
                client, "/prendas/mover", {"garment_ids": [first, second], "destination_id": 2}
            ).status_code
            == 302
        )
    assert db.execute("SELECT count(*) FROM garment_movements").fetchone()[0] == 2
    assert db.execute("SELECT count(*) FROM outfit_items").fetchone()[0] == 2
    assert b"Espacio B" in client.get("/outfits").data
    assert post(client, f"/prendas/{first}/archivar").status_code == 302
    assert (
        post(client, "/prendas/mover", {"garment_ids": [first], "destination_id": 3}).status_code
        == 400
    )


def test_delete_blocks_relations_and_preserves_images(client, add_garment, db, app):
    gid = add_garment(photos=photograph())
    post(client, "/outfits/nuevo", {"name": "Look", "garment_ids": [gid]})
    assert post(client, f"/prendas/{gid}/eliminar", {"confirm": "1"}).status_code == 409
    assert len(list((app.config["DATA_DIR"] / "images").iterdir())) == 3
    oid = db.execute("SELECT id FROM outfits").fetchone()[0]
    assert post(client, f"/outfits/{oid}/eliminar", {"confirm": "1"}).status_code == 302
    assert post(client, f"/prendas/{gid}/eliminar", {"confirm": "1"}).status_code == 302
    assert not list((app.config["DATA_DIR"] / "images").iterdir())


def test_locations_categories_and_favorites(client, add_garment, db):
    gid = add_garment()
    assert post(client, "/ubicaciones/nueva", {"name": "Valencia"}).status_code == 302
    assert (
        post(client, "/ubicaciones/1/renombrar", {"name": "Espacio A renombrado"}).status_code
        == 302
    )
    assert b"Espacio A renombrado" in client.get(f"/prendas/{gid}").data
    assert post(client, "/ubicaciones/1/eliminar", {"confirm": "1"}).status_code == 409
    assert post(client, "/ubicaciones/4/eliminar", {"confirm": "1"}).status_code == 302
    assert post(client, "/ajustes/categorias", {"name": "Bañadores"}).status_code == 302
    assert db.execute("SELECT count(*) FROM categories WHERE name='Bañadores'").fetchone()[0] == 1
    assert post(client, f"/prendas/{gid}/favorito").status_code == 302
    assert db.execute("SELECT favorite FROM garments").fetchone()[0] == 1


def test_browser_security_and_error_pages(client, add_garment):
    assert client.post("/prendas/nueva", data={"name": "Sin token"}).status_code == 400
    assert (
        post(
            client,
            "/ubicaciones/nueva",
            {"name": "Intrusa"},
            headers={"Origin": "https://example.com"},
        ).status_code
        == 403
    )
    assert client.get("/", headers={"Host": "evil.example"}).status_code == 400
    gid = add_garment(name='<script>alert("x")</script>')
    assert b"<script>alert" not in client.get(f"/prendas/{gid}").data
    assert b"&lt;script&gt;" in client.get(f"/prendas/{gid}").data
    assert client.get("/imagenes/session.key").status_code == 404
    assert client.get("/prendas/99999").status_code == 404
    assert client.get("/?page=nan").status_code == 400
    assert client.get("/?location_id=invalid").status_code == 400
    headers = client.get("/").headers
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"


def test_all_pages_render_and_pagination(client, add_garment):
    for path in (
        "/",
        "/prendas/nueva",
        "/outfits",
        "/outfits/nuevo",
        "/maletas",
        "/maletas/nueva",
        "/ubicaciones",
        "/ajustes",
    ):
        response = client.get(path)
        assert response.status_code == 200, path
    for i in range(49):
        add_garment(name=f"Prenda {i}")
    assert client.get("/").data.count(b'class="garment-card"') == 48
    assert client.get("/?page=2").data.count(b'class="garment-card"') == 1


def test_search_accepts_accents_case_and_literal_symbols(client, add_garment):
    add_garment(name="Pantalón cáñamo 50%")
    assert b"Pantal" in client.get("/?q=PANTALON+CANAMO").data
    assert b'class="garment-card"' in client.get("/?q=50%25").data
    assert b'class="garment-card"' not in client.get("/?q=_").data


def test_primary_photo_is_used_across_views_and_scoped_to_garment(client, add_garment, db):
    gid = add_garment(photos=[photograph("navy"), photograph("red")])
    other = add_garment(photos=photograph("green"))
    images = db.execute(
        "SELECT * FROM garment_images WHERE garment_id=? ORDER BY id", (gid,)
    ).fetchall()
    other_image = db.execute(
        "SELECT id FROM garment_images WHERE garment_id=?", (other,)
    ).fetchone()[0]
    assert post(client, f"/prendas/{gid}/fotos/{other_image}/principal").status_code == 404
    assert post(client, f"/prendas/{gid}/fotos/{images[1]['id']}/principal").status_code == 302
    assert images[1]["thumbnail"].encode() in client.get("/").data
    detail = client.get(f"/prendas/{gid}").data
    assert detail.index(images[1]["filename"].encode()) < detail.index(
        images[0]["filename"].encode()
    )
    assert post(client, f"/prendas/{gid}/fotos/{images[1]['id']}/eliminar").status_code == 302
    assert images[0]["thumbnail"].encode() in client.get("/").data


def test_bulk_import_is_atomic_and_keeps_each_photo(client, db, app):
    invalid = post(
        client,
        "/prendas/importar",
        {
            "category_id": 2,
            "location_id": 1,
            "photos": [photograph(), (io.BytesIO(b"invalid"), "bad.png")],
        },
    )
    assert invalid.status_code == 400
    assert db.execute("SELECT count(*) FROM garments").fetchone()[0] == 0
    assert not list((app.config["DATA_DIR"] / "images").iterdir())
    response = post(
        client,
        "/prendas/importar",
        {"category_id": 2, "location_id": 2, "photos": [photograph("red"), photograph("blue")]},
    )
    assert response.status_code == 302
    assert db.execute("SELECT count(*) FROM garments WHERE location_id=2").fetchone()[0] == 2
    assert db.execute("SELECT count(*) FROM garment_images").fetchone()[0] == 2
    assert db.execute("SELECT count(*) FROM image_integrity").fetchone()[0] == 6
