from .conftest import post


def test_collections_and_tags_filter_and_preserve_archived(client, add_garment, db):
    first, second = add_garment("Lino"), add_garment("Lana")
    assert post(client, "/colecciones/nueva", {"name": "Viaje"}).status_code == 302
    assert (
        post(
            client, "/colecciones/1/guardar", {"name": "Viaje", "garment_ids": [first, second]}
        ).status_code
        == 302
    )
    assert post(client, "/etiquetas/nueva", {"name": "Ligera"}).status_code == 302
    assert (
        post(
            client, "/etiquetas/1/actualizar", {"name": "Ligera", "garment_ids": [first]}
        ).status_code
        == 302
    )
    assert b"Lino" in client.get("/?tag_id=1&collection_id=1").data
    assert b"Lana" not in client.get("/?tag_id=1&collection_id=1").data
    post(client, f"/prendas/{first}/archivar")
    assert (
        post(client, "/colecciones/1/guardar", {"name": "Viaje", "garment_ids": []}).status_code
        == 302
    )
    assert db.execute("SELECT garment_id FROM collection_items").fetchone()[0] == first
    assert post(client, "/etiquetas/1/actualizar", {"name": "Ligera"}).status_code == 302
    assert db.execute("SELECT garment_id FROM garment_tags").fetchone()[0] == first
    assert post(client, "/organizacion/coleccion/1/eliminar", {"confirm": "1"}).status_code == 302
    assert db.execute("SELECT count(*) FROM garments").fetchone()[0] == 2
    assert db.execute("SELECT count(*) FROM garment_movements").fetchone()[0] == 0


def test_organization_rejects_unknown_items_and_renders(client, add_garment):
    add_garment()
    assert client.get("/colecciones").status_code == 200
    assert post(client, "/colecciones/nueva", {"name": "Favoritas"}).status_code == 302
    assert client.get("/colecciones/1").status_code == 200
    assert (
        post(
            client, "/colecciones/1/guardar", {"name": "Favoritas", "garment_ids": [999]}
        ).status_code
        == 400
    )
    assert post(client, "/etiquetas/nueva", {"name": "Lino"}).status_code == 302
    assert client.get("/etiquetas/1").status_code == 200
