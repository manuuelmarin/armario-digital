from .conftest import photograph, post


def test_grouped_import_selects_cover(client, db):
    result = post(
        client,
        "/prendas/importar",
        {
            "photos": [photograph("red"), photograph("blue")],
            "photo_groups": ["1", "1"],
            "cover_index": "1",
            "category_id": "2",
            "location_id": "1",
            "photo_names": ["Camisa", "Espalda"],
        },
    )
    assert result.status_code == 302
    assert db.execute("SELECT count(*) FROM garments").fetchone()[0] == 1
    assert [r[0] for r in db.execute("SELECT is_primary FROM garment_images ORDER BY id")] == [0, 1]


def test_location_coverage_and_repeated_favorite(client, db, add_garment):
    first = add_garment()
    second = add_garment("Abrigo", location=2)
    with db:
        db.execute("INSERT INTO outfits(name) VALUES ('Trabajo')")
        db.executemany("INSERT INTO outfit_items VALUES (1,?)", [(first,), (second,)])
    assert "1 de 2 en Espacio A" in client.get("/outfits?location_id=1").get_data(as_text=True)
    assert "Trabajo" not in client.get("/outfits?location_id=1&complete=1").get_data(as_text=True)
    for _ in range(2):
        assert post(client, f"/prendas/{first}/favorito", {"desired": "1"}).status_code == 302
    assert db.execute("SELECT favorite FROM garments WHERE id=?", (first,)).fetchone()[0] == 1
    assert "Precio registrado en 0 de 1" in client.get("/resumen").get_data(as_text=True)


def test_missing_photo_text_contrast():
    import re
    from pathlib import Path

    css = Path("armario/static/components.css").read_text()
    tokens = Path("armario/static/tokens.css").read_text()
    assert "color: var(--muted)" in css.split(".photo-placeholder {")[1].split("}")[0]
    foreground = re.search(r"--muted: (#\w+)", tokens)[1]

    def luminance(color):
        channels = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        return sum(
            weight * (v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
            for weight, v in zip((0.2126, 0.7152, 0.0722), channels, strict=True)
        )

    backgrounds = re.findall(r"\.card-image(?:\.tone-\d)? \{[^}]*background: (#\w+)", css)
    assert len(backgrounds) == 4
    for background in backgrounds:
        assert (luminance(background) + 0.05) / (luminance(foreground) + 0.05) >= 4.5
