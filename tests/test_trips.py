from .conftest import post


def setup_trip(client, name="Fin de semana"):
    response = post(client, "/maletas/nueva", {"name": name, "origin_id": 1, "destination_id": 2})
    assert response.status_code == 302
    return int(response.location.rsplit("/", 1)[1])


def test_outfit_edit_preserves_existing_archived_piece(client, add_garment, db):
    gid = add_garment()
    post(client, "/outfits/nuevo", {"name": "Original", "garment_ids": [gid]})
    oid = db.execute("SELECT id FROM outfits").fetchone()[0]
    post(client, f"/prendas/{gid}/archivar")
    assert client.get(f"/outfits/{oid}/editar").status_code == 200
    assert (
        post(
            client,
            f"/outfits/{oid}/editar",
            {"name": "Editado", "garment_ids": [gid], "favorite": "1"},
        ).status_code
        == 302
    )
    assert post(client, "/outfits/nuevo", {"name": "Otro", "garment_ids": [gid]}).status_code == 400
    assert db.execute("SELECT name FROM outfits").fetchone()[0] == "Editado"


def test_trip_deduplication_objects_and_no_implicit_moves(client, add_garment, db):
    first, second = add_garment(), add_garment("En destino", location=2)
    post(client, "/outfits/nuevo", {"name": "Look", "garment_ids": [first, second]})
    tid = setup_trip(client)
    for payload in (
        {"garment_ids": [first]},
        {"outfit_id": 1},
        {"outfit_id": 1},
        {"label": "Cargador"},
        {"label": "Cargador"},
    ):
        assert post(client, f"/maletas/{tid}/anadir", payload).status_code == 302
    assert db.execute("SELECT count(*) FROM trip_items").fetchone()[0] == 3
    assert db.execute("SELECT location_id FROM garments WHERE id=?", (first,)).fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM garment_movements").fetchone()[0] == 0
    assert b"Ya en destino" in client.get(f"/maletas/{tid}").data
    assert post(client, f"/prendas/{first}/eliminar", {"confirm": "1"}).status_code == 409
    assert post(client, "/outfits/1/eliminar", {"confirm": "1"}).status_code == 302
    assert db.execute("SELECT count(*) FROM trip_items").fetchone()[0] == 3


def test_transfer_only_selected_packed_origin_and_is_idempotent(client, add_garment, db):
    first, second, distant, unprepared = (
        add_garment("Uno"),
        add_garment("Dos"),
        add_garment("Lejana", location=3),
        add_garment("Sin preparar"),
    )
    tid = setup_trip(client)
    post(client, f"/maletas/{tid}/anadir", {"garment_ids": [first, second, distant, unprepared]})
    for gid in (first, second, distant):
        iid = db.execute("SELECT id FROM trip_items WHERE garment_id=?", (gid,)).fetchone()[0]
        assert post(client, f"/maletas/{tid}/elementos/{iid}/preparar").status_code == 302
    assert db.execute("SELECT count(*) FROM garment_movements").fetchone()[0] == 0
    preview = client.get(f"/maletas/{tid}/trasladar")
    assert preview.status_code == 200 and b"Confirmar traslado" in preview.data
    assert (
        post(
            client, f"/maletas/{tid}/trasladar", {"confirm": "1", "garment_ids": [distant]}
        ).status_code
        == 400
    )
    assert (
        post(
            client, f"/maletas/{tid}/trasladar", {"confirm": "1", "garment_ids": [unprepared]}
        ).status_code
        == 400
    )
    for _ in range(2):
        assert (
            post(
                client, f"/maletas/{tid}/trasladar", {"confirm": "1", "garment_ids": [first]}
            ).status_code
            == 302
        )
    mapping = {r[0]: r[1] for r in db.execute("SELECT id,location_id FROM garments")}
    assert mapping == {first: 2, second: 1, distant: 3, unprepared: 1}
    assert db.execute("SELECT count(*) FROM garment_movements").fetchone()[0] == 1


def test_stale_transfer_rejects_entire_selection(client, add_garment, db):
    first, second = add_garment("Uno"), add_garment("Dos")
    tid = setup_trip(client)
    post(client, f"/maletas/{tid}/anadir", {"garment_ids": [first, second]})
    with db:
        db.execute("UPDATE trip_items SET packed=1")
    post(client, "/prendas/mover", {"garment_ids": [second], "destination_id": 3})
    response = post(
        client, f"/maletas/{tid}/trasladar", {"confirm": "1", "garment_ids": [first, second]}
    )
    assert response.status_code == 400
    assert db.execute("SELECT location_id FROM garments WHERE id=?", (first,)).fetchone()[0] == 1


def test_trip_dates_edit_remove_and_delete(client, add_garment, db):
    assert (
        post(
            client, "/maletas/nueva", {"name": "Mal", "origin_id": 1, "destination_id": 1}
        ).status_code
        == 400
    )
    assert (
        post(
            client,
            "/maletas/nueva",
            {
                "name": "Mal",
                "origin_id": 1,
                "destination_id": 2,
                "starts_on": "2026-10-29",
                "ends_on": "2026-10-01",
            },
        ).status_code
        == 400
    )
    tid = setup_trip(client)
    gid = add_garment()
    post(client, f"/maletas/{tid}/anadir", {"garment_ids": [gid]})
    iid = db.execute("SELECT id FROM trip_items").fetchone()[0]
    assert post(client, f"/maletas/{tid}/elementos/999/quitar").status_code == 404
    assert post(client, f"/maletas/{tid}/elementos/{iid}/quitar").status_code == 302
    assert client.get(f"/maletas/{tid}/editar").status_code == 200
    assert (
        post(
            client,
            f"/maletas/{tid}/editar",
            {"name": "Actualizado", "origin_id": 1, "destination_id": 3},
        ).status_code
        == 302
    )
    assert client.get(f"/maletas/{tid}/eliminar").status_code == 200
    assert post(client, f"/maletas/{tid}/eliminar", {"confirm": "1"}).status_code == 302
    assert db.execute("SELECT count(*) FROM garments").fetchone()[0] == 1
