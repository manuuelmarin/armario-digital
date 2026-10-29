import io
from pathlib import Path

from PIL import Image

from armario import create_app
from armario.backups import create_backup, verify_backup
from armario.db import SCHEMA_VERSION, connect, migrate
from armario.demo import seed_demo
from armario.images import store_image

from .conftest import post


def test_clean_installation_requires_explicit_first_space(tmp_path):
    root = tmp_path / "fresh"
    app = create_app({"TESTING": True, "DATA_DIR": root})
    client = app.test_client()
    db = connect(root / "wardrobe.sqlite")
    try:
        assert db.execute("SELECT count(*) FROM locations").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM garments").fetchone()[0] == 0
        assert b"Empieza por un lugar" in client.get("/").data
        assert client.get("/prendas/nueva").location.endswith("/empezar")
        assert post(client, "/empezar", {"name": " "}).status_code == 400
        assert post(client, "/empezar", {"name": "Armario del estudio"}).location.endswith(
            "/prendas/nueva"
        )
        assert db.execute("SELECT name FROM locations").fetchone()[0] == "Armario del estudio"
        assert client.get("/empezar").location.endswith("/")
        assert client.get("/prendas/nueva").status_code == 200
    finally:
        db.close()


def test_filter_tabs_preserve_search_and_sort(client, add_garment):
    from html.parser import HTMLParser

    add_garment(name="Alfa")
    add_garment(name="Zulu")
    page = client.get("/?q=a&category_id=2&sort=name&season=Verano").data.decode()

    class Links(HTMLParser):
        links = []

        def handle_starttag(self, tag, attrs):
            attributes = dict(attrs)
            if tag == "a" and "tab" in attributes.get("class", "").split():
                self.links.append(attributes["href"])

    parser = Links()
    parser.feed(page)
    assert any(
        "location_id=2" in link
        and "q=a" in link
        and "sort=name" in link
        and "season=Verano" in link
        for link in parser.links
    )
    ordered = client.get("/?sort=name").data
    assert ordered.index(b"Alfa") < ordered.index(b"Zulu")
    newest = client.get("/").data
    assert newest.index(b"Zulu") < newest.index(b"Alfa")
    assert client.get("/?sort=not-a-sort").status_code == 400


def test_favorite_on_card_returns_to_filtered_collection(client, add_garment):
    gid = add_garment()
    response = post(
        client,
        f"/prendas/{gid}/favorito",
        {"return_view": "inventory", "location_id": "1", "sort": "name"},
    )
    assert response.status_code == 302
    assert "location_id=1" in response.location and "sort=name" in response.location
    assert "/prendas/" not in response.location


def test_responsive_derivatives_are_real_sizes_and_never_upscaled(tmp_path):
    for size in ((3000, 4000), (80, 100)):
        upload = io.BytesIO()
        Image.new("RGB", size, "ivory").save(upload, "PNG")
        upload.seek(0)
        image = store_image(upload, tmp_path)
        for key, width_key in (
            ("filename", "width"),
            ("preview", "preview_width"),
            ("thumbnail", "thumbnail_width"),
        ):
            with Image.open(tmp_path / image[key]) as derivative:
                assert derivative.width == image[width_key]
                assert derivative.width <= size[0]
                assert not derivative.getexif()
        assert image["width"] >= image["preview_width"] >= image["thumbnail_width"]
        assert image["preview_width"] <= 1024 and image["thumbnail_width"] <= 512


def test_v2_images_and_locations_survive_upgrade_and_old_backup(tmp_path):
    root = tmp_path / "v2"
    root.mkdir()
    (root / "images").mkdir()
    db = connect(root / "wardrobe.sqlite")
    migrations = Path(__file__).parents[1] / "armario" / "migrations"
    try:
        for name in ("001_core.sql", "002_trips.sql"):
            db.executescript((migrations / name).read_text(encoding="utf-8"))
        with db:
            db.execute("PRAGMA user_version=2")
            db.execute("INSERT INTO locations(name) VALUES ('Espacio existente')")
            db.execute(
                "INSERT INTO garments(name,category_id,location_id) VALUES ('Artículo existente',1,1)"
            )
            db.execute("INSERT INTO outfits(name) VALUES ('Combinación existente')")
            db.execute("INSERT INTO outfit_items VALUES (1,1)")
            db.execute(
                "INSERT INTO garment_images(garment_id,filename,thumbnail,digest) VALUES (1,?,?,?)",
                ("a" * 32 + ".webp", "a" * 32 + "-thumb.webp", "legacy"),
            )
        for name in ("a" * 32 + ".webp", "a" * 32 + "-thumb.webp"):
            Image.new("RGB", (80, 100), "ivory").save(root / "images" / name, "WEBP")
    finally:
        db.close()
    backup = create_backup(root, expected_version=2)
    assert verify_backup(backup)["schema_version"] == 2
    migrate(root)
    connection = connect(root / "wardrobe.sqlite")
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert connection.execute("SELECT name FROM locations").fetchone()[0] == "Espacio existente"
        assert connection.execute("SELECT count(*) FROM outfit_items").fetchone()[0] == 1
        assert connection.execute("SELECT preview FROM garment_images").fetchone()[0] is None
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        connection.close()
    assert verify_backup(create_backup(root))["garments"] == 1
    client = create_app({"TESTING": True, "DATA_DIR": root}).test_client()
    assert b"srcset=" in client.get("/").data


def test_demo_is_explicit_idempotent_and_separate_from_empty_installation(tmp_path):
    normal = tmp_path / "normal"
    demo = tmp_path / "demo"
    create_app({"TESTING": True, "DATA_DIR": normal})
    app = create_app({"TESTING": True, "DATA_DIR": demo, "DEMO_MODE": True})
    seed_demo(demo)
    seed_demo(demo)
    for root, expected in ((normal, 0), (demo, 12)):
        connection = connect(root / "wardrobe.sqlite")
        try:
            assert connection.execute("SELECT count(*) FROM garments").fetchone()[0] == expected
        finally:
            connection.close()
    assert b"Demo" in app.test_client().get("/").data
    assert verify_backup(create_backup(demo))["garments"] == 12


def test_private_html_and_immutable_images_have_distinct_cache_policies(client, add_garment, db):
    from .conftest import photograph

    add_garment(photos=photograph())
    image = db.execute("SELECT thumbnail FROM garment_images").fetchone()[0]
    assert client.get("/").headers["Cache-Control"] == "no-store"
    assert "private" in client.get("/imagenes/" + image).headers["Cache-Control"]
    assert "immutable" in client.get("/imagenes/" + image).headers["Cache-Control"]
    assert "public" in client.get("/static/app.css").headers["Cache-Control"]


def test_outfit_detail_search_and_duplicate_preserve_items(client, add_garment, db):
    garments = [add_garment(name=f"Prenda {i}") for i in range(5)]
    assert (
        post(
            client,
            "/outfits/nuevo",
            {"name": "Día soleado", "occasion": "Viaje", "favorite": "1", "garment_ids": garments},
        ).status_code
        == 302
    )
    oid = db.execute("SELECT id FROM outfits").fetchone()[0]
    assert "Día soleado".encode() in client.get("/outfits?q=dia&favorite=1").data
    assert "Día soleado".encode() not in client.get("/outfits?q=inexistente").data
    page = client.get(f"/outfits/{oid}")
    assert page.status_code == 200
    for i in range(5):
        assert f"Prenda {i}".encode() in page.data
    assert post(client, f"/prendas/{garments[0]}/archivar").status_code == 302
    response = post(client, f"/outfits/{oid}/duplicar")
    assert response.status_code == 302
    duplicate = db.execute("SELECT id FROM outfits WHERE id!=?", (oid,)).fetchone()[0]
    assert (
        db.execute("SELECT count(*) FROM outfit_items WHERE outfit_id=?", (duplicate,)).fetchone()[
            0
        ]
        == 5
    )
    assert db.execute("SELECT count(*) FROM garment_movements").fetchone()[0] == 0
