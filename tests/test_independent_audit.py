"""Independent, fictional regression probes: assertions express expected behavior."""

import base64
import io
import json
import re
from html.parser import HTMLParser

import pytest
from PIL import Image

from armario.ai_jobs import decoded_job
from armario.assistant import default_constraints
from armario.backups import create_backup
from armario.profiles import source
from tests.conftest import photograph, post
from tests.test_local_ai import FakeOllama, enqueue_outfit, profile_data, profile_form, worker
from tests.test_local_ai import enabled as enabled
from tests.test_local_ai import wardrobe as wardrobe
from tests.test_project_audit import completed_job


class GenerationForm(HTMLParser):
    """Collect successful controls and browser defaults from the generator form."""

    def __init__(self):
        super().__init__()
        self.inside = False
        self.values = {}
        self.select_name = None
        self.options = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form" and "editor" in attrs.get("class", "").split():
            self.inside = True
        elif self.inside and tag == "input" and attrs.get("name"):
            if attrs.get("type") not in {"checkbox", "radio"} or "checked" in attrs:
                key, value = attrs["name"], attrs.get("value", "")
                self.values.setdefault(key, []).append(value)
        elif self.inside and tag == "select":
            self.select_name, self.options = attrs.get("name"), []
        elif self.inside and tag == "option" and self.select_name:
            self.options.append((attrs.get("value", ""), "selected" in attrs))

    def handle_endtag(self, tag):
        if self.inside and tag == "select" and self.select_name:
            choice = next((v for v, selected in self.options if selected), self.options[0][0])
            self.values.setdefault(self.select_name, []).append(choice)
            self.select_name = None
        elif self.inside and tag == "form":
            self.inside = False

    def payload(self):
        return {k: v if len(v) > 1 else v[0] for k, v in self.values.items()}


def test_visible_cover_equals_source_after_reorder_and_delete(app, client, db, add_garment):
    gid = add_garment(photos=[photograph("red"), photograph("blue"), photograph("green")])
    rows = db.execute(
        "SELECT id, filename FROM garment_images WHERE garment_id=? ORDER BY id", (gid,)
    ).fetchall()
    assert (
        post(
            client, f"/prendas/{gid}/fotos/{rows[2][0]}/ordenar", {"direction": "anterior"}
        ).status_code
        == 302
    )
    assert (
        post(client, f"/prendas/{gid}/fotos/{rows[0][0]}/eliminar", {"confirm": "1"}).status_code
        == 302
    )
    html = client.get(f"/prendas/{gid}").get_data(as_text=True)
    visible = re.search(r'<img data-main-photo\s+src="/imagenes/([^\"]+)', html).group(1)
    vision_source = source(db, gid)["name"]
    listing_source = db.execute(
        "SELECT filename FROM garment_images WHERE garment_id=? ORDER BY is_primary DESC,id LIMIT 1",
        (gid,),
    ).fetchone()[0]
    assert post(client, "/ajustes/ia", {"enabled": "1"}).status_code == 302
    assert post(client, f"/prendas/{gid}/analizar").status_code == 302
    fake = FakeOllama()
    assert worker(app, fake).run_once() and len(fake.calls) == 1
    with Image.open(app.config["DATA_DIR"] / "images" / visible) as image:
        visible_rgb = image.convert("RGB").getpixel((20, 20))
    with Image.open(io.BytesIO(base64.b64decode(fake.calls[0]["image"]))) as image:
        vision_rgb = image.convert("RGB").getpixel((20, 20))
    assert max(abs(a - b) for a, b in zip(visible_rgb, vision_rgb, strict=True)) <= 3
    assert visible == rows[2][1]
    assert visible == vision_source == listing_source, (
        f"visible={visible} RGB={visible_rgb}, vision={vision_source} RGB={vision_rgb}, catalogue={listing_source}"
    )


def test_saved_outfit_replacement_preserves_original_location_filter(
    app, client, db, wardrobe, add_garment
):
    other = add_garment(name="Otra camisa en Espacio B", location=2)
    assert (
        post(
            client, f"/prendas/{other}/descripcion", profile_form(db, other, profile_data("camisa"))
        ).status_code
        == 302
    )
    jid = enqueue_outfit(client, location_id="1", style="minimalista", occasion="Cena")
    assert worker(app).run_once()
    job = decoded_job(db.execute("SELECT * FROM ai_jobs WHERE id=?", (jid,)).fetchone())
    chosen = job["result"]["outfits"][0]["garment_ids"]
    upper = next(g for g in chosen if g in {wardrobe["shirt"], wardrobe["tee"]})
    saved = post(client, f"/ia/tareas/{jid}/guardar", {"proposal": "1", "name": "Outfit inicial"})
    assert saved.status_code == 302
    oid = int(saved.location.rsplit("/", 1)[1])
    provenance = json.loads(
        db.execute(
            "SELECT provenance_json FROM outfit_origins WHERE outfit_id=?", (oid,)
        ).fetchone()[0]
    )
    assert provenance["constraints"]["location_id"] == 1
    assert provenance["constraints"]["style"] == "minimalista"
    html = client.get(f"/outfits/generar?outfit_id={oid}&replace={upper}").get_data(as_text=True)
    form = GenerationForm()
    form.feed(html)
    # Submit the form as rendered, without changing its controls.
    replacement = post(client, "/outfits/generar", form.payload())
    assert replacement.status_code == 302
    new = decoded_job(db.execute("SELECT * FROM ai_jobs ORDER BY id DESC LIMIT 1").fetchone())
    plans = new["input"]["plans"]
    saved_foreign = False
    if any(other in plan for plan in plans):
        assert worker(app).run_once()
        done = decoded_job(db.execute("SELECT * FROM ai_jobs WHERE id=?", (new["id"],)).fetchone())
        number = next(
            i
            for i, proposal in enumerate(done["result"]["outfits"], 1)
            if other in proposal["garment_ids"]
        )
        saved_foreign = (
            post(
                client,
                f"/ia/tareas/{new['id']}/guardar",
                {"proposal": str(number), "name": "Conjunto en otra ubicación"},
            ).status_code
            == 302
        )
    assert (
        new["input"]["constraints"]["location_id"] == 1
        and new["input"]["constraints"]["style"] == "minimalista"
        and all(other not in plan for plan in plans)
    ), (
        f"original location=1, new location={new['input']['constraints']['location_id']}, style={new['input']['constraints']['style']!r}, other-location garment={other}, plans={plans}, saved={saved_foreign}"
    )


@pytest.mark.parametrize("with_alternative", [True, False])
def test_replacing_a_proposal_preserves_earlier_exclusions(
    client, db, wardrobe, add_garment, with_alternative
):
    if with_alternative:
        extra = add_garment(name="Tercera camisa")
        assert (
            post(
                client,
                f"/prendas/{extra}/descripcion",
                profile_form(db, extra, profile_data("camisa")),
            ).status_code
            == 302
        )
    constraints = {**default_constraints(), "length": "largo", "excluded": [wardrobe["shirt"]]}
    jid, _, chosen = completed_job(db, constraints, wardrobe["tee"])
    assert wardrobe["shirt"] not in chosen and wardrobe["tee"] in chosen
    response = post(
        client, f"/ia/tareas/{jid}/sustituir", {"proposal": "1", "garment_id": str(wardrobe["tee"])}
    )
    if not with_alternative:
        assert response.status_code == 400
        assert db.execute("SELECT max(id) FROM ai_jobs").fetchone()[0] == jid
        return
    assert response.status_code == 302
    new = decoded_job(db.execute("SELECT * FROM ai_jobs ORDER BY id DESC LIMIT 1").fetchone())
    assert all(wardrobe["shirt"] not in plan for plan in new["input"]["plans"]), (
        f"previous excluded={wardrobe['shirt']}; new constraints={new['input']['constraints']}; plans={new['input']['plans']}"
    )


def test_retry_requires_reselection_when_fixed_id_was_reused(
    app, client, db, wardrobe, add_garment
):
    old_gid = wardrobe["dress"]  # Highest SQLite rowid, so deletion makes it reusable.
    jid = enqueue_outfit(client, garment_ids=[str(old_gid)], length="any")
    assert post(client, f"/prendas/{old_gid}/eliminar", {"confirm": "1"}).status_code == 302
    new_gid = add_garment(name="Otra prenda física")
    assert new_gid == old_gid
    assert (
        post(
            client,
            f"/prendas/{new_gid}/descripcion",
            profile_form(db, new_gid, profile_data("vestido")),
        ).status_code
        == 302
    )
    fake = FakeOllama()
    assert worker(app, fake).run_once()
    assert not fake.calls
    assert db.execute("SELECT status FROM ai_jobs WHERE id=?", (jid,)).fetchone()[0] == "stale"
    before_count = db.execute("SELECT count(*) FROM ai_jobs").fetchone()[0]
    retried = post(client, f"/ia/tareas/{jid}/reintentar")
    after_count = db.execute("SELECT count(*) FROM ai_jobs").fetchone()[0]
    if after_count > before_count:
        new = decoded_job(db.execute("SELECT * FROM ai_jobs ORDER BY id DESC LIMIT 1").fetchone())
        pytest.fail(
            f"retry accepted reused garment id {new_gid} as fixed={new['input']['constraints']['fixed']}; plans={new['input']['plans']}"
        )
    assert retried.status_code in {200, 302, 400}


def test_missing_source_is_not_advertised_as_ready(app, client, db, wardrobe, add_garment):
    gid = add_garment(name="Prenda con foto alterada", photos=photograph())
    assert post(client, f"/prendas/{gid}/descripcion", profile_form(db, gid)).status_code == 302
    (app.config["DATA_DIR"] / "images" / source(db, gid)["name"]).unlink()
    detail = client.get(f"/prendas/{gid}").get_data(as_text=True)
    generator = client.get("/outfits/generar").get_data(as_text=True)
    ready_match = re.search(r">Prenda con foto alterada</a>\s*·\s*([^<]+)", generator)
    assert ready_match is not None
    ready_message = ready_match.group(1).strip()
    response = post(
        client,
        "/outfits/generar",
        {
            "mode": "recommended",
            "location_id": "1",
            "jacket": "no",
            "length": "largo",
            "garment_ids": str(gid),
        },
    )
    if response.status_code == 302:
        jid = int(response.location.rsplit("/", 1)[1])
        fake = FakeOllama()
        assert worker(app, fake).run_once() and not fake.calls
        assert db.execute("SELECT status FROM ai_jobs WHERE id=?", (jid,)).fetchone()[0] == "stale"
    else:
        assert response.status_code == 400
    assert ready_message != "Lista para combinar", (
        f"detail says reviewed={'Revisada por ti' in detail}; generator says {ready_message!r}; request status={response.status_code}"
    )


def test_backup_rejects_schema_with_missing_foreign_keys(app, client, db, add_garment, tmp_path):
    gid = add_garment()
    assert (
        post(
            client, "/outfits/nuevo", {"name": "Outfit con relación", "garment_ids": [str(gid)]}
        ).status_code
        == 302
    )
    assert len(db.execute("PRAGMA foreign_key_list(outfit_items)").fetchall()) == 2
    # Simulate an incomplete schema, while retaining all rows, column names and user_version.
    db.execute("PRAGMA foreign_keys=OFF")
    db.executescript("""
        CREATE TABLE weakened_outfit_items(outfit_id INTEGER NOT NULL, garment_id INTEGER NOT NULL,
                                           PRIMARY KEY(outfit_id, garment_id));
        INSERT INTO weakened_outfit_items SELECT * FROM outfit_items;
        DROP TABLE outfit_items;
        ALTER TABLE weakened_outfit_items RENAME TO outfit_items;
    """)
    db.execute("PRAGMA foreign_keys=ON")
    assert db.execute("PRAGMA foreign_key_list(outfit_items)").fetchall() == []
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    with pytest.raises(ValueError, match="claves externas"):
        create_backup(app.config["DATA_DIR"])
