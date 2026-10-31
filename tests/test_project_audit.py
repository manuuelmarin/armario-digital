"""Regressions found by the project audit, using only fictional wardrobes."""

import base64
import io
import json
import zipfile

import pytest
from PIL import Image, ImageDraw

from armario.ai_jobs import decoded_job, enqueue
from armario.assistant import default_constraints
from armario.backups import create_backup
from armario.profiles import image_payload, save_profile, source, vision_snapshot
from armario.recommendations import current_snapshot, make_snapshot, rank_result

from .conftest import photograph, post
from .test_local_ai import FakeOllama, profile_data, profile_form, worker
from .test_local_ai import enabled as enabled
from .test_local_ai import wardrobe as wardrobe


def completed_job(db, constraints, required_gid):
    snapshot = make_snapshot(db, constraints)
    number = next(i for i, plan in enumerate(snapshot["plans"], 1) if required_gid in plan)
    result = rank_result(
        {
            "rankings": [
                {
                    "candidate_id": number,
                    "harmony": 4,
                    "style": 4,
                    "balance": 4,
                    "reason": "Combinación de prueba",
                }
            ]
        },
        snapshot,
    )
    with db:
        jid = enqueue(db, "outfit", snapshot)
        db.execute(
            "UPDATE ai_jobs SET status='completed',result_json=? WHERE id=?",
            (json.dumps(result), jid),
        )
    return jid, snapshot, result["outfits"][0]["garment_ids"]


@pytest.mark.parametrize(
    "key,kind,permission", [("jacket", "chaqueta", False), ("accessory", "accesorio", True)]
)
def test_replacing_optional_layer_keeps_its_role(
    client, db, wardrobe, add_garment, key, kind, permission
):
    alternative = add_garment(name="Otra pieza")
    post(
        client,
        f"/prendas/{alternative}/descripcion",
        profile_form(db, alternative, profile_data(kind)),
    )
    constraints = {**default_constraints(), "length": "largo", "accessories": permission}
    jid, _, chosen = completed_job(db, constraints, wardrobe[key])
    response = post(
        client, f"/ia/tareas/{jid}/sustituir", {"proposal": "1", "garment_id": str(wardrobe[key])}
    )
    assert response.status_code == 302
    new = decoded_job(db.execute("SELECT * FROM ai_jobs ORDER BY id DESC LIMIT 1").fetchone())
    for plan in new["input"]["plans"]:
        assert alternative in plan
        assert set(chosen) - {wardrobe[key]} <= set(plan)
        assert wardrobe[key] not in plan


def test_replacing_one_piece_does_not_silently_turn_into_two_pieces(client, db, wardrobe):
    jid, _, _ = completed_job(db, default_constraints(), wardrobe["dress"])
    response = post(
        client,
        f"/ia/tareas/{jid}/sustituir",
        {"proposal": "1", "garment_id": str(wardrobe["dress"])},
    )
    assert response.status_code == 400  # There is no second dress/one-piece garment.


def test_reused_garment_id_cannot_validate_an_old_generation(client, db, wardrobe, add_garment):
    gid = wardrobe["dress"]  # Highest rowid, reusable after deletion in SQLite.
    jid, snapshot, _ = completed_job(db, {**default_constraints(), "fixed": [gid]}, gid)
    previous = db.execute("SELECT created_at FROM garments WHERE id=?", (gid,)).fetchone()[0]
    with db:
        db.execute("DELETE FROM garments WHERE id=?", (gid,))
    new_id = add_garment(name="Una prenda física diferente")
    assert new_id == gid
    with db:
        db.execute("UPDATE garments SET created_at=? WHERE id=?", (previous, gid))
        save_profile(db, gid, profile_data("vestido"), 0, {"origin": "manual", "schema": 1})
    assert not current_snapshot(db, snapshot)
    assert (
        post(
            client, f"/ia/tareas/{jid}/guardar", {"proposal": "1", "name": "No guardar"}
        ).status_code
        == 400
    )


def test_external_photo_change_during_inference_discards_result(
    app, client, db, enabled, add_garment
):
    gid = add_garment(photos=photograph())
    post(client, f"/prendas/{gid}/analizar")
    path = app.config["DATA_DIR"] / "images" / source(db, gid)["name"]
    fake = FakeOllama(callback=lambda: path.write_bytes(b"changed outside the app"))
    assert worker(app, fake).run_once()
    assert db.execute("SELECT status FROM ai_jobs").fetchone()[0] == "stale"
    assert not db.execute("SELECT 1 FROM garment_profiles").fetchone()


def test_manual_review_does_not_approve_a_tampered_photo(app, client, db, enabled, add_garment):
    gid = add_garment(photos=photograph())
    fields = profile_form(db, gid)
    (app.config["DATA_DIR"] / "images" / source(db, gid)["name"]).write_bytes(b"modified")
    assert post(client, f"/prendas/{gid}/descripcion", fields).status_code == 400
    assert not db.execute("SELECT 1 FROM garment_profiles").fetchone()


def test_transparent_black_cutout_retains_contrast_for_vision(
    app, client, db, enabled, add_garment
):
    picture = Image.new("RGBA", (400, 500), (0, 0, 0, 0))
    ImageDraw.Draw(picture).rectangle((100, 100, 300, 400), fill=(0, 0, 0, 255))
    buffer = io.BytesIO()
    picture.save(buffer, "PNG")
    buffer.seek(0)
    gid = add_garment(photos=(buffer, "cutout.png"))
    payload = image_payload(app.config["DATA_DIR"], vision_snapshot(db, gid))
    with Image.open(io.BytesIO(base64.b64decode(payload))) as received:
        assert min(received.getpixel((10, 10))) > 240
        assert max(received.getpixel((200, 250))) < 15


@pytest.mark.parametrize("table", ["ai_settings", "garment_profiles", "ai_jobs", "outfit_origins"])
def test_backup_rejects_missing_tables_from_declared_schema(app, db, table):
    with db:
        db.execute(f"DROP TABLE {table}")
    with pytest.raises(ValueError, match="estructura|esquema|tabla"):
        create_backup(app.config["DATA_DIR"])


def test_worker_does_not_misattribute_new_prompts_to_old_jobs(
    app, client, db, enabled, add_garment
):
    gid = add_garment(photos=photograph())
    post(client, f"/prendas/{gid}/analizar")
    with db:
        db.execute("UPDATE ai_jobs SET prompt_version='previous-instructions'")
    fake = FakeOllama()
    assert worker(app, fake).run_once()
    assert db.execute("SELECT status FROM ai_jobs").fetchone()[0] == "stale"
    assert not fake.calls


@pytest.mark.parametrize("damage", ["column", "settings"])
def test_backup_and_startup_reject_incomplete_structure(app, db, damage):
    from armario import create_app

    with db:
        if damage == "column":
            db.execute("ALTER TABLE ai_jobs DROP COLUMN model_digest")
        else:
            db.execute("DELETE FROM ai_settings")
    with pytest.raises(ValueError, match="estructura"):
        create_backup(app.config["DATA_DIR"])
    with pytest.raises(ValueError, match="estructura"):
        create_app({"TESTING": True, "DATA_DIR": app.config["DATA_DIR"]})


def test_old_snapshot_requires_explicit_regeneration(app, client, db, wardrobe):
    snapshot = make_snapshot(db, default_constraints())
    snapshot.pop("version")
    with db:
        jid = enqueue(db, "outfit", snapshot)
    fake = FakeOllama()
    assert worker(app, fake).run_once()
    assert db.execute("SELECT status FROM ai_jobs WHERE id=?", (jid,)).fetchone()[0] == "stale"
    assert not fake.calls
    assert post(client, f"/ia/tareas/{jid}/reintentar").status_code == 302
    assert worker(app, fake).run_once()
    assert (
        db.execute("SELECT status FROM ai_jobs ORDER BY id DESC LIMIT 1").fetchone()[0]
        == "completed"
    )


def test_text_generation_checks_actual_photo_before_model_call(
    app, client, db, wardrobe, add_garment
):
    gid = add_garment(photos=photograph())
    assert post(client, f"/prendas/{gid}/descripcion", profile_form(db, gid)).status_code == 302
    with db:
        jid = enqueue(db, "outfit", make_snapshot(db, {**default_constraints(), "fixed": [gid]}))
    (app.config["DATA_DIR"] / "images" / source(db, gid)["name"]).unlink()
    fake = FakeOllama()
    assert worker(app, fake).run_once()
    assert db.execute("SELECT status FROM ai_jobs WHERE id=?", (jid,)).fetchone()[0] == "stale"
    assert not fake.calls


@pytest.mark.parametrize(
    "field,value", [("format", True), ("schema_version", None), ("schema_version", 9.0)]
)
def test_backup_rejects_untyped_format_metadata(app, tmp_path, field, value):
    from armario.backups import verify_backup

    source = create_backup(app.config["DATA_DIR"])
    changed = tmp_path / "bad-manifest.zip"
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(changed, "w") as target:
        for entry in original.infolist():
            data = original.read(entry)
            if entry.filename == "manifest.json":
                manifest = json.loads(data)
                manifest[field] = value
                data = json.dumps(manifest).encode()
            target.writestr(entry, data)
    with pytest.raises(ValueError):
        verify_backup(changed)
