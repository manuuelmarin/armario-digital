import io
import re

import pytest
from PIL import Image

from armario import create_app
from armario.db import connect


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATA_DIR": tmp_path / "data"})


@pytest.fixture
def client(app):
    return app.test_client()


def post(client, path, data=None, **kwargs):
    client.get("/")
    with client.session_transaction() as session:
        csrf = session["csrf"]
    return client.post(path, data={"csrf": csrf, **(data or {})}, **kwargs)


def photograph(color="navy", orientation=None):
    buffer = io.BytesIO()
    image = Image.new("RGB", (800, 1000), color)
    exif = Image.Exif()
    if orientation:
        exif[274] = orientation
    image.save(buffer, "JPEG", exif=exif)
    buffer.seek(0)
    return buffer, "prenda.jpg"


@pytest.fixture
def add_garment(client):
    def add(name="Camisa azul", location=1, **extra):
        response = post(
            client,
            "/prendas/nueva",
            {"name": name, "category_id": 2, "location_id": location, **extra},
        )
        assert response.status_code == 302, response.data.decode()
        return int(re.search(r"/prendas/(\d+)", response.location)[1])

    return add


@pytest.fixture
def db(app):
    connection = connect(app.config["DATA_DIR"] / "wardrobe.sqlite")
    yield connection
    connection.close()
