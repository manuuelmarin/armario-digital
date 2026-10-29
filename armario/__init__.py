import os
import secrets
import sqlite3
import threading
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, abort, g, render_template, request, session
from werkzeug.exceptions import HTTPException, SecurityError

from . import db

VERSION = "0.2.0"


def default_data_dir():
    if value := os.environ.get("ARMARIO_DATA_DIR"):
        return Path(value).expanduser().resolve()
    if os.name == "nt":
        return (
            Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            / "ArmarioDigital"
        )
    return Path.home() / ".local" / "share" / "armario-digital"


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATA_DIR=default_data_dir(),
        # Six photographs may each be up to 10 MiB; leave room for form fields.
        MAX_CONTENT_LENGTH=64 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        TRUSTED_HOSTS=["localhost", "127.0.0.1", "[::1]"],
        MUTATION_LOCK=threading.RLock(),
        DEMO_MODE=False,
        DEV_MODE=False,
    )
    if config:
        app.config.update(config)
    root = Path(app.config["DATA_DIR"]).resolve()
    app.config["DATA_DIR"] = root
    db.migrate(root)
    secret = root / "session.key"
    try:
        with secret.open("x", encoding="ascii") as stream:
            stream.write(secrets.token_hex(32))
        secret.chmod(0o600)
    except FileExistsError:
        pass
    app.secret_key = secret.read_text(encoding="ascii")
    app.teardown_appcontext(db.close_db)

    @app.before_request
    def guard_local_requests():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        if request.method == "POST":
            if not secrets.compare_digest(session["csrf"], request.form.get("csrf", "")):
                abort(400, "La sesión del formulario ha caducado. Recarga e inténtalo de nuevo.")
            origin = request.headers.get("Origin")
            if origin and urlsplit(origin).netloc != request.host:
                abort(403, "Origen de solicitud no permitido.")
            app.config["MUTATION_LOCK"].acquire()
            g.mutation_locked = True

    @app.teardown_request
    def release_mutation_lock(error=None):
        if g.pop("mutation_locked", False):
            app.config["MUTATION_LOCK"].release()

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
        if response.status_code == 200 and not app.config["DEV_MODE"]:
            if request.endpoint == "static":
                response.headers["Cache-Control"] = "public, max-age=86400"
            elif request.endpoint == "inventory.image":
                response.headers["Cache-Control"] = "private, max-age=31536000, immutable"
            else:
                response.headers["Cache-Control"] = "no-store"
        else:
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.context_processor
    def common():
        from .domain import SEASONS

        connection = db.get_db()
        return {
            "locations": connection.execute("SELECT * FROM locations ORDER BY id").fetchall(),
            "categories": connection.execute("SELECT * FROM categories ORDER BY id").fetchall(),
            "seasons": SEASONS,
            "version": VERSION,
            "demo_mode": app.config["DEMO_MODE"],
            "view_names": {
                "inventory": "Mi armario",
                "looks": "Outfits",
                "trips": "Maletas",
                "settings": "Mi espacio",
            },
        }

    @app.errorhandler(ValueError)
    def invalid(error):
        return render_template("error.html", message=str(error)), 400

    @app.errorhandler(sqlite3.IntegrityError)
    def conflict(error):
        return render_template(
            "error.html",
            message="Este elemento está en uso o ya existe. Puedes archivar una prenda para conservar sus relaciones.",
        ), 409

    @app.errorhandler(HTTPException)
    def http_error(error):
        if isinstance(error, SecurityError):
            # Untrusted hosts have no URL adapter; do not render links or query data.
            return "Host no permitido.", 400
        return render_template("error.html", message=error.description), error.code

    from . import inventory, looks, settings, trips

    for module in (inventory, looks, trips, settings):
        app.register_blueprint(module.bp)
    return app
