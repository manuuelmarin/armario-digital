import io

from PIL import Image

from armario.backups import create_backup, verify_backup

from .conftest import photograph, post


def test_board_image_survives_backup_and_coordinates_are_validated(client, app, db, tmp_path):
    assert post(client, "/inspiracion/nuevo", {"name": "Ideas"}).status_code == 302
    assert (
        post(
            client,
            "/inspiracion/1/anadir",
            {"caption": "Idea", "link": "https://example.com", "photo": photograph()},
        ).status_code
        == 302
    )
    item = db.execute("SELECT * FROM board_items").fetchone()
    assert client.get("/inspiracion/1").status_code == 200
    assert client.get("/inspiracion/1/lienzo.css").status_code == 200
    assert (
        post(
            client,
            "/inspiracion/1/elemento/1/guardar",
            {"x": 500, "y": 20, "width": 300, "caption": "Idea", "link": "javascript:alert(1)"},
        ).status_code
        == 400
    )
    assert (
        post(
            client,
            "/inspiracion/1/elemento/1/guardar",
            {"x": 500, "y": 20, "width": 300, "caption": "Idea", "link": "https://example.com"},
        ).status_code
        == 302
    )
    backup = create_backup(app.config["DATA_DIR"])
    assert verify_backup(backup)["schema_version"] >= 7
    path = app.config["DATA_DIR"] / "images" / item["preview"]
    Image.new("RGB", (20, 20), "red").save(path, "WEBP")
    assert post(client, "/copias").status_code == 400


def test_inspiration_rejects_invalid_images_and_unsafe_links(client, app, db):
    post(client, "/inspiracion/nuevo", {"name": "Ideas"})
    response = post(
        client, "/inspiracion/1/anadir", {"link": "javascript:alert(1)", "photo": photograph()}
    )
    assert response.status_code == 400
    response = post(
        client, "/inspiracion/1/anadir", {"caption": "X", "photo": (io.BytesIO(b"bad"), "bad.png")}
    )
    assert response.status_code == 400
    assert db.execute("SELECT count(*) FROM board_items").fetchone()[0] == 0
    assert not list((app.config["DATA_DIR"] / "images").iterdir())


def test_weather_is_on_demand_and_keeps_cache_when_offline(client, db, monkeypatch):
    from armario import weather

    calls = []

    def fetch(lat, lon):
        calls.append((lat, lon))
        return [{"date": "2026-10-29", "max": 20, "min": 10, "rain": 25}]

    monkeypatch.setattr(weather, "get_forecast", fetch)
    assert client.get("/tiempo").status_code == 200
    assert not calls
    assert (
        post(
            client, "/tiempo/actualizar", {"label": "Lugar", "latitude": 40, "longitude": -3}
        ).status_code
        == 302
    )
    assert calls == [(40, -3)]
    assert b"2026-10-29" in client.get("/tiempo").data
    assert (
        post(
            client, "/tiempo/actualizar", {"label": "Otro", "latitude": "nan", "longitude": 0}
        ).status_code
        == 400
    )
    assert db.execute("SELECT label FROM weather_cache").fetchone()[0] == "Lugar"

    def offline(*args):
        raise ValueError("sin conexión")

    monkeypatch.setattr(weather, "get_forecast", offline)
    assert (
        post(
            client, "/tiempo/actualizar", {"label": "Otro", "latitude": 40, "longitude": -3}
        ).status_code
        == 400
    )
    assert db.execute("SELECT label FROM weather_cache").fetchone()[0] == "Lugar"


def test_board_supports_many_items_without_exceeding_coordinate_bounds(client, db):
    post(client, "/inspiracion/nuevo", {"name": "Muchas ideas"})
    for i in range(40):
        assert post(client, "/inspiracion/1/anadir", {"caption": f"Idea {i}"}).status_code == 302
    assert db.execute("SELECT count(*) FROM board_items").fetchone()[0] == 40
