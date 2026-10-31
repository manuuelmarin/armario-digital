"""Synthetic integration and failure tests; never download or execute model weights."""

import copy
import json
import threading

import pytest

from armario.ai_client import (
    TEXT_MODEL,
    VISION_MODEL,
    ModelError,
    ModelTimeout,
    OllamaClient,
    read_json,
)
from armario.ai_jobs import AIWorker, decoded_job
from armario.backups import create_backup, restore_backup, verify_backup
from armario.db import SCHEMA_VERSION, connect, migrate
from armario.profiles import blank_profile, revision, save_profile, source, validate_profile
from armario.recommendations import constraints_from_form, make_snapshot, rank_result

from .conftest import photograph, post


def profile_data(kind="camisa", length="no_visible"):
    profile = blank_profile()
    profile.update(
        description="Prenda azul de líneas sencillas con superficie lisa.",
        details="Cierre visible.",
    )
    profile["identification"].update(type=kind, subtype="Corte recto")
    profile["palette"]["main"] = "Azul marino, predominante"
    profile["pattern"]["kind"] = "Liso"
    profile["shape"]["leg_length"] = length
    profile["aesthetics"].update(styles=["casual", "minimalista"], formality=2)
    return validate_profile(profile)


def profile_form(db, gid, profile=None, **extra):
    data = profile or profile_data()
    current = source(db, gid)
    fields = {
        "revision": str(revision(db, gid)),
        "source_name": current["name"],
        "source_hash": current["hash"],
        "confirm": "1",
    }
    for key, value in data.items():
        if isinstance(value, dict):
            for name, part in value.items():
                fields[f"{key}.{name}"] = ", ".join(part) if isinstance(part, list) else str(part)
        else:
            fields[key] = value
    return {**fields, **extra}


class FakeOllama:
    """Protocol double only: these ratings provide no evidence of fashion quality."""

    def __init__(self, callback=None, error=None):
        self.calls = []
        self.callback = callback
        self.error = error

    def models(self):
        return {VISION_MODEL: "a" * 64, TEXT_MODEL: "b" * 64}

    def chat(self, model, system, content, schema, image=None):
        self.calls.append({"model": model, "content": content, "image": image})
        if self.callback:
            self.callback()
        if self.error:
            raise self.error
        if model == VISION_MODEL:
            return profile_data(), "a" * 64
        return {
            "rankings": [
                {
                    "candidate_id": plan["candidate_id"],
                    "harmony": 4,
                    "style": 4,
                    "balance": 3,
                    "reason": "Paleta azul coherente, líneas sencillas y formalidad cercana.",
                }
                for plan in json.loads(content)["candidates"][:3]
            ]
        }, "b" * 64


@pytest.fixture
def enabled(client):
    assert post(client, "/ajustes/ia", {"enabled": "1"}).status_code == 302


@pytest.fixture
def wardrobe(client, add_garment, db, enabled):
    result = {}
    for key, kind, length in (
        ("shirt", "camisa", "no_visible"),
        ("tee", "camiseta", "no_visible"),
        ("trousers", "pantalon", "largo"),
        ("trousers2", "pantalon", "largo"),
        ("shorts", "pantalon_corto", "corto"),
        ("shoes", "calzado", "no_visible"),
        ("jacket", "chaqueta", "no_visible"),
        ("accessory", "accesorio", "no_visible"),
        ("dress", "vestido", "no_visible"),
    ):
        gid = add_garment(name=f"Prenda de prueba {key}")
        assert (
            post(
                client,
                f"/prendas/{gid}/descripcion",
                profile_form(db, gid, profile_data(kind, length)),
            ).status_code
            == 302
        )
        result[key] = gid
    return result


def worker(app, fake=None):
    return AIWorker(app.config["DATA_DIR"], app.config["MUTATION_LOCK"], fake or FakeOllama())


def enqueue_outfit(client, **fields):
    response = post(
        client,
        "/outfits/generar",
        {"mode": "recommended", "jacket": "no", "length": "largo", **fields},
    )
    assert response.status_code == 302, response.data.decode()
    return int(response.location.rsplit("/", 1)[1])


def test_disabled_is_offline_and_manual_flows_work(client, add_garment, monkeypatch, db):
    def forbidden(*args, **kwargs):
        pytest.fail("No debe haber conexión de red al navegar ni al crear manualmente.")

    monkeypatch.setattr(OllamaClient, "request", forbidden)
    gid = add_garment(photos=photograph())
    for route in (
        "/",
        "/ajustes/ia",
        "/ia/tareas",
        "/ia/analizar",
        "/outfits/generar",
        f"/prendas/{gid}/descripcion",
    ):
        assert client.get(route).status_code == 200
    assert post(client, f"/prendas/{gid}/analizar").status_code == 400
    assert db.execute("SELECT count(*) FROM ai_jobs").fetchone()[0] == 0
    assert post(client, f"/prendas/{gid}/descripcion", profile_form(db, gid)).status_code == 302
    assert (
        post(client, "/outfits/nuevo", {"name": "Manual", "garment_ids": [str(gid)]}).status_code
        == 302
    )


def test_vision_review_then_text_generation_save_and_replace(
    app, client, db, wardrobe, add_garment, tmp_path
):
    gid = add_garment(photos=photograph())
    fake = FakeOllama()
    runner = worker(app, fake)
    response = post(client, f"/prendas/{gid}/analizar")
    assert response.status_code == 302
    jid = int(response.location.rsplit("/", 1)[1])
    assert post(client, f"/prendas/{gid}/analizar").status_code == 400
    assert runner.run_once()
    assert (
        db.execute("SELECT count(*) FROM garment_profiles WHERE garment_id=?", (gid,)).fetchone()[0]
        == 0
    )
    proposal = decoded_job(db.execute("SELECT * FROM ai_jobs WHERE id=?", (jid,)).fetchone())
    assert proposal["status"] == "completed"
    assert fake.calls[0]["image"]
    assert client.get(f"/prendas/{gid}/descripcion?job={jid}").status_code == 200
    assert (
        post(
            client,
            f"/prendas/{gid}/descripcion",
            profile_form(
                db, gid, proposal["result"], job_id=str(jid), description="Mi corrección manual."
            ),
        ).status_code
        == 302
    )
    assert (
        json.loads(
            db.execute(
                "SELECT profile_json FROM garment_profiles WHERE garment_id=?", (gid,)
            ).fetchone()[0]
        )["description"]
        == "Mi corrección manual."
    )
    generated = enqueue_outfit(
        client, garment_ids=[str(gid)], jacket="yes", accessories="1", occasion="Una cena"
    )
    assert runner.run_once()
    job = decoded_job(db.execute("SELECT * FROM ai_jobs WHERE id=?", (generated,)).fetchone())
    assert job["status"] == "completed", job["error"]
    assert fake.calls[1]["model"] == TEXT_MODEL and fake.calls[1]["image"] is None
    assert "Mi corrección manual." in fake.calls[1]["content"]
    assert "images" not in json.loads(fake.calls[1]["content"])
    assert client.get(f"/ia/tareas/{generated}").status_code == 200
    chosen = job["result"]["outfits"][0]["garment_ids"]
    assert gid in chosen and wardrobe["jacket"] in chosen
    saved = post(
        client, f"/ia/tareas/{generated}/guardar", {"proposal": "1", "name": "Conjunto revisado"}
    )
    assert saved.status_code == 302
    assert client.get(saved.location).status_code == 200
    assert db.execute("SELECT count(*) FROM outfit_origins").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM garment_movements").fetchone()[0] == 0
    replacement = post(
        client,
        f"/ia/tareas/{generated}/sustituir",
        {"proposal": "1", "garment_id": str(wardrobe["trousers"])},
    )
    if wardrobe["trousers"] not in chosen:
        replacement = post(
            client,
            f"/ia/tareas/{generated}/sustituir",
            {"proposal": "1", "garment_id": str(wardrobe["trousers2"])},
        )
    assert replacement.status_code == 302
    new = decoded_job(db.execute("SELECT * FROM ai_jobs ORDER BY id DESC LIMIT 1").fetchone())
    assert len(new["input"]["constraints"]["fixed"]) == len(chosen) - 1
    excluded = new["input"]["constraints"]["excluded"]
    assert all(
        set(chosen) - set(excluded) <= set(plan) and not set(excluded) & set(plan)
        for plan in new["input"]["plans"]
    )
    restored = tmp_path / "ai-restored"
    archive = create_backup(app.config["DATA_DIR"])
    assert verify_backup(archive)["schema_version"] == SCHEMA_VERSION
    restore_backup(archive, restored)
    other = connect(restored / "wardrobe.sqlite")
    try:
        assert (
            json.loads(other.execute("SELECT provenance_json FROM outfit_origins").fetchone()[0])[
                "digest"
            ]
            == "b" * 64
        )
        assert (
            json.loads(
                other.execute(
                    "SELECT profile_json FROM garment_profiles WHERE garment_id=?", (gid,)
                ).fetchone()[0]
            )["description"]
            == "Mi corrección manual."
        )
        assert other.execute("SELECT count(*) FROM outfit_items").fetchone()[0] == len(chosen)
        assert other.execute("SELECT count(*) FROM garment_images").fetchone()[0] == 1
        assert other.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        other.close()


@pytest.mark.parametrize(
    "jacket,length,accessories", [("yes", "corto", "0"), ("no", "largo", "1"), ("any", "any", "0")]
)
def test_hard_filters_apply_to_every_candidate(client, db, wardrobe, jacket, length, accessories):
    jid = enqueue_outfit(
        client,
        jacket=jacket,
        length=length,
        accessories=accessories,
        garment_ids=[str(wardrobe["shirt"])],
    )
    snapshot = decoded_job(db.execute("SELECT * FROM ai_jobs WHERE id=?", (jid,)).fetchone())[
        "input"
    ]
    assert len(snapshot["plans"]) <= 10
    for plan in snapshot["plans"]:
        assert wardrobe["shirt"] in plan and wardrobe["shoes"] in plan
        assert (wardrobe["jacket"] in plan) if jacket == "yes" else True
        assert (wardrobe["jacket"] not in plan) if jacket == "no" else True
        if length == "corto":
            assert wardrobe["shorts"] in plan
        if length == "largo":
            assert wardrobe["shorts"] not in plan
        if accessories == "0":
            assert wardrobe["accessory"] not in plan


def test_unknown_length_and_wrong_location_cannot_satisfy_constraints(client, db, wardrobe):
    for name in ("trousers", "trousers2"):
        assert (
            post(
                client,
                f"/prendas/{wardrobe[name]}/descripcion",
                profile_form(db, wardrobe[name], profile_data("pantalon")),
            ).status_code
            == 302
        )
    assert post(client, "/outfits/generar", {"length": "largo"}).status_code == 400
    assert (
        post(
            client,
            "/outfits/generar",
            {"location_id": "2", "garment_ids": [str(wardrobe["shirt"])]},
        ).status_code
        == 400
    )
    assert (
        post(
            client, "/outfits/generar", {"jacket": "no", "garment_ids": [str(wardrobe["jacket"])]}
        ).status_code
        == 400
    )


def test_stale_photo_and_manual_revision_discard_vision(app, client, db, enabled, add_garment):
    gid = add_garment(photos=[photograph("blue"), photograph("red")])
    post(client, f"/prendas/{gid}/analizar")
    image = db.execute("SELECT max(id) FROM garment_images").fetchone()[0]
    fake = FakeOllama(callback=lambda: post(client, f"/prendas/{gid}/fotos/{image}/principal"))
    assert worker(app, fake).run_once()
    assert (
        db.execute("SELECT status FROM ai_jobs ORDER BY id DESC LIMIT 1").fetchone()[0] == "stale"
    )
    assert not db.execute("SELECT 1 FROM garment_profiles").fetchone()
    post(client, f"/prendas/{gid}/analizar")
    fake = FakeOllama(
        callback=lambda: post(client, f"/prendas/{gid}/descripcion", profile_form(db, gid))
    )
    assert worker(app, fake).run_once()
    assert (
        db.execute("SELECT status FROM ai_jobs ORDER BY id DESC LIMIT 1").fetchone()[0] == "stale"
    )
    assert revision(db, gid) == 1


def test_photo_tampering_fails_before_vision_call(app, client, db, enabled, add_garment):
    gid = add_garment(photos=photograph())
    post(client, f"/prendas/{gid}/analizar")
    (app.config["DATA_DIR"] / "images" / source(db, gid)["name"]).write_bytes(b"modified")
    fake = FakeOllama()
    assert worker(app, fake).run_once()
    assert not fake.calls
    assert db.execute("SELECT status FROM ai_jobs").fetchone()[0] == "stale"


def test_review_detects_revision_photo_and_invalid_groups(client, db, enabled, add_garment):
    gid = add_garment(photos=[photograph("blue"), photograph("red")])
    old_form = profile_form(db, gid)
    assert post(client, f"/prendas/{gid}/descripcion", old_form).status_code == 302
    assert post(client, f"/prendas/{gid}/descripcion", old_form).status_code == 400
    form = profile_form(db, gid)
    image = db.execute("SELECT max(id) FROM garment_images").fetchone()[0]
    post(client, f"/prendas/{gid}/fotos/{image}/principal")
    assert post(client, f"/prendas/{gid}/descripcion", form).status_code == 400
    invalid = profile_form(db, gid, profile_data(), **{"shape.leg_length": "largo"})
    assert post(client, f"/prendas/{gid}/descripcion", invalid).status_code == 400
    assert revision(db, gid) == 1


@pytest.mark.parametrize("change", ["archive", "location", "profile", "delete"])
def test_generation_cannot_save_after_wardrobe_changes(app, client, db, wardrobe, change):
    jid = enqueue_outfit(client, garment_ids=[str(wardrobe["shirt"])])
    assert worker(app).run_once()
    gid = wardrobe["shirt"]
    with db:
        if change == "archive":
            db.execute("UPDATE garments SET archived=1 WHERE id=?", (gid,))
        elif change == "location":
            db.execute("UPDATE garments SET location_id=2 WHERE id=?", (gid,))
        elif change == "delete":
            db.execute("DELETE FROM garments WHERE id=?", (gid,))
        else:
            save_profile(db, gid, profile_data(), revision(db, gid), {"origin": "manual"})
    assert (
        post(
            client, f"/ia/tareas/{jid}/guardar", {"proposal": "1", "name": "No guardar"}
        ).status_code
        == 400
    )
    assert db.execute("SELECT count(*) FROM outfits").fetchone()[0] == 0
    assert client.get(f"/ia/tareas/{jid}").status_code == 200


def test_ranking_rejects_hallucinations_duplicates_and_low_ratings(client, db, wardrobe):
    from werkzeug.datastructures import MultiDict

    snapshot = make_snapshot(db, constraints_from_form(MultiDict({"length": "largo"})))
    good = {"candidate_id": 1, "harmony": 4, "style": 4, "balance": 4, "reason": "Compatible"}
    for result in (
        {"rankings": [{**good, "candidate_id": 99}]},
        {"rankings": [good, good]},
        {"rankings": [{**good, "harmony": 1, "style": 1, "balance": 1}]},
        {"rankings": [{**good, "garment_ids": [999]}]},
    ):
        with pytest.raises(ValueError):
            rank_result(result, snapshot)
    snapshot["constraints"]["mode"] = "surprise"
    assert len(rank_result({"rankings": [good]}, snapshot)["outfits"]) == 1


def test_queue_pause_cancel_timeout_and_restart(app, client, db, wardrobe):
    jid = enqueue_outfit(client)
    post(client, "/ia/cola", {"action": "pause"})
    fake = FakeOllama()
    runner = worker(app, fake)
    assert runner.run_once() is False and not fake.calls
    post(client, "/ia/cola", {"action": "resume"})
    fake.error = ModelTimeout("Tiempo agotado")
    assert runner.run_once()
    assert db.execute("SELECT paused FROM ai_settings").fetchone()[0] == 1
    assert db.execute("SELECT status FROM ai_jobs WHERE id=?", (jid,)).fetchone()[0] == "failed"
    response = post(client, f"/ia/tareas/{jid}/reintentar")
    assert response.status_code == 302
    second = int(response.location.rsplit("/", 1)[1])
    post(client, f"/ia/tareas/{second}/cancelar")
    assert (
        db.execute("SELECT status FROM ai_jobs WHERE id=?", (second,)).fetchone()[0] == "cancelled"
    )
    with db:
        db.execute("UPDATE ai_jobs SET status='running' WHERE id=?", (second,))
    runner.recover()
    assert db.execute("SELECT status FROM ai_jobs WHERE id=?", (second,)).fetchone()[0] == "failed"
    assert post(client, "/ia/cola", {"action": "clear"}).status_code == 400
    assert post(client, "/ia/cola", {"action": "clear", "confirm": "1"}).status_code == 302
    assert db.execute("SELECT count(*) FROM ai_jobs").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM garment_profiles").fetchone()[0] == 9


def test_inference_does_not_block_writes_and_cancel_discards_response(app, client, db, wardrobe):
    jid = enqueue_outfit(client)
    started, release = threading.Event(), threading.Event()

    def block():
        started.set()
        assert release.wait(5)

    runner = worker(app, FakeOllama(callback=block))
    thread = threading.Thread(target=runner.run_once)
    thread.start()
    try:
        assert started.wait(3)
        assert post(client, f"/prendas/{wardrobe['shirt']}/favorito").status_code == 302
        assert post(client, f"/ia/tareas/{jid}/cancelar").status_code == 302
    finally:
        release.set()
        thread.join(3)
    assert not thread.is_alive()
    assert db.execute("SELECT status,result_json FROM ai_jobs WHERE id=?", (jid,)).fetchone()[
        :
    ] == ("cancelled", None)


def test_batch_is_atomic_and_disabled_cancels_pending(app, client, db, enabled, add_garment):
    photographed = add_garment(photos=photograph())
    no_photo = add_garment()
    assert (
        post(
            client, "/ia/analizar", {"garment_ids": [str(photographed), str(no_photo)]}
        ).status_code
        == 400
    )
    assert not db.execute("SELECT 1 FROM ai_jobs").fetchone()
    assert post(client, "/ia/analizar", {"garment_ids": [str(photographed)]}).status_code == 302
    assert post(client, "/ajustes/ia").status_code == 302
    assert db.execute("SELECT status FROM ai_jobs").fetchone()[0] == "cancelled"
    assert worker(app).run_once() is False


def test_ai_backup_restore_and_populated_v8_migration(
    app, client, db, wardrobe, tmp_path, add_garment
):
    gid = add_garment(photos=photograph())
    post(client, "/outfits/nuevo", {"name": "Anterior", "garment_ids": [str(gid)]})
    root = app.config["DATA_DIR"]
    with db:
        tag_id = db.execute("INSERT INTO tags(name) VALUES ('Etiqueta anterior')").lastrowid
        collection_id = db.execute(
            "INSERT INTO collections(name) VALUES ('Colección anterior')"
        ).lastrowid
        db.execute("INSERT INTO garment_tags VALUES (?,?)", (gid, tag_id))
        db.execute("INSERT INTO collection_items VALUES (?,?)", (collection_id, gid))
        trip_id = db.execute(
            "INSERT INTO trips(name,origin_id,destination_id) VALUES ('Viaje anterior',1,2)"
        ).lastrowid
        db.execute(
            "INSERT INTO trip_items(trip_id,garment_id,packed) VALUES (?,?,1)", (trip_id, gid)
        )
        board_id = db.execute("INSERT INTO boards(name) VALUES ('Tablero anterior')").lastrowid
        db.execute(
            "INSERT INTO board_items(board_id,caption,x,y,width) VALUES (?,'Idea anterior',100,120,250)",
            (board_id,),
        )
        for table in ("outfit_origins", "ai_jobs", "garment_profiles", "ai_settings"):
            db.execute(f"DROP TABLE {table}")
        db.execute("PRAGMA user_version=8")
    migrate(root)
    before = next((root / "backups").glob("before-schema-8-*.zip"))
    assert verify_backup(before)["schema_version"] == 8
    assert db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    assert db.execute("SELECT count(*) FROM outfit_items").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM garment_images").fetchone()[0] == 1
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    assert db.execute("SELECT enabled FROM ai_settings").fetchone()[0] == 0
    assert (
        db.execute("SELECT tag_id FROM garment_tags WHERE garment_id=?", (gid,)).fetchone()[0]
        == tag_id
    )
    assert (
        db.execute(
            "SELECT garment_id FROM collection_items WHERE collection_id=?", (collection_id,)
        ).fetchone()[0]
        == gid
    )
    assert db.execute(
        "SELECT garment_id,packed FROM trip_items WHERE trip_id=?", (trip_id,)
    ).fetchone()[:] == (gid, 1)
    assert db.execute("SELECT x,y,width FROM board_items WHERE board_id=?", (board_id,)).fetchone()[
        :
    ] == (100, 120, 250)
    post(client, "/ajustes/ia", {"enabled": "1"})
    post(client, f"/prendas/{gid}/descripcion", profile_form(db, gid))
    post(client, f"/prendas/{gid}/analizar")
    archive = create_backup(root)
    restored = tmp_path / "restored"
    restore_backup(archive, restored)
    other = connect(restored / "wardrobe.sqlite")
    try:
        assert other.execute("SELECT count(*) FROM garment_profiles").fetchone()[0] == 1
        assert other.execute("SELECT status FROM ai_jobs").fetchone()[0] == "queued"
        assert source(other, gid) == source(db, gid)
    finally:
        other.close()


def test_profiles_and_model_json_validate_strictly():
    assert read_json('{"ok":1}') == {"ok": 1}
    for raw in ('{"ok":1,"ok":2}', "```json\n{}\n```", "not JSON"):
        with pytest.raises(ModelError):
            read_json(raw)
    for mutate in (
        lambda p: p.update(extra="ignored?"),
        lambda p: p["aesthetics"].update(formality=True),
        lambda p: p["palette"].update(main="x" * 81),
    ):
        data = copy.deepcopy(profile_data())
        mutate(data)
        with pytest.raises(ValueError):
            validate_profile(data)
