"""Portable, verified SQLite snapshots and offline directory-swap restoration."""

import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
import uuid
import zipfile
from contextlib import contextmanager
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .db import SCHEMA_VERSION, connect
from .images import MAX_PIXELS

IMAGE_NAME = re.compile(r"^[0-9a-f]{32}(?:-thumb|-preview)?\.webp$")
MAX_UNPACKED_BYTES = 4 * 1024**3


@lru_cache(maxsize=SCHEMA_VERSION)
def schema_contract(version):
    """Derive required tables/columns from the same migrations used at startup."""
    reference = sqlite3.connect(":memory:")
    try:
        for number in range(1, version + 1):
            script = next(Path(__file__).with_name("migrations").glob(f"{number:03d}_*.sql"))
            reference.executescript(script.read_text(encoding="utf-8"))
        return tuple(
            (name, tuple(row[1] for row in reference.execute(f'PRAGMA table_info("{name}")')))
            for (name,) in reference.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        )
    finally:
        reference.close()


def check_structure(db, version):
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for name, required in schema_contract(version):
        if name not in tables:
            raise ValueError(
                f"La estructura del esquema {version} está incompleta: falta la tabla {name}."
            )
        actual = {row[1] for row in db.execute(f'PRAGMA table_info("{name}")')}
        if not set(required) <= actual:
            raise ValueError(
                f"La estructura del esquema {version} está incompleta: faltan columnas en {name}."
            )
    if (
        version >= 9
        and db.execute("SELECT count(*) FROM ai_settings WHERE id=1").fetchone()[0] != 1
    ):
        raise ValueError("La estructura de ajustes de asistencia está incompleta.")


class InstanceBusy(RuntimeError):
    pass


@contextmanager
def process_lock(root):
    """One server or recovery command per data directory, including on Windows."""
    root = Path(root).resolve()
    root.parent.mkdir(parents=True, exist_ok=True)
    handle = (root.parent / f".{root.name}.lock").open("a+b")
    try:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            if not handle.read(1):
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        raise InstanceBusy(
            "Cierra Armario Digital antes de iniciar otra instancia o restaurar."
        ) from exc
    try:
        yield
    finally:
        handle.close()


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def referenced_images(db):
    names = set()
    columns = {row[1] for row in db.execute("PRAGMA table_info(garment_images)")}
    selection = "filename,thumbnail,preview" if "preview" in columns else "filename,thumbnail"
    for row in db.execute(f"SELECT {selection} FROM garment_images"):
        for name in row:
            if name is None:
                continue
            if not IMAGE_NAME.fullmatch(name):
                raise ValueError("La base de datos contiene una ruta de imagen inválida.")
            names.add("images/" + name)
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "board_items" in tables:
        for row in db.execute("SELECT filename,thumbnail,preview FROM board_items"):
            for name in row:
                if name is None:
                    continue
                if not IMAGE_NAME.fullmatch(name):
                    raise ValueError("El tablero contiene una ruta de imagen inválida.")
                names.add("images/" + name)
    return names


def check_database(path, expected_version=None):
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if expected_version is not None and type(expected_version) is not int:
            raise ValueError("La versión del esquema debe ser un entero.")
        if expected_version is not None and version != expected_version:
            raise ValueError("La versión del manifiesto no coincide con la base de datos.")
        if not 1 <= version <= SCHEMA_VERSION:
            raise ValueError("Esta copia pertenece a una versión incompatible.")
        check_structure(db, version)
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("La base de datos está dañada.")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("La copia tiene relaciones inconsistentes.")
        names = referenced_images(db)
        counts = {
            t: db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            for t in ("garments", "outfits", "outfit_items")
        }
        return version, names, counts
    finally:
        db.close()


def check_image(path):
    try:
        with Image.open(path, formats=("WEBP",)) as image:
            if image.width * image.height > MAX_PIXELS:
                raise ValueError(f"La imagen {path.name} supera el límite de resolución.")
            image.load()
    except FileNotFoundError:
        raise
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ValueError(f"La imagen {path.name} no se puede leer.") from exc


def verify_image_baselines(database_path, images, root):
    database = sqlite3.connect(database_path)
    try:
        checksums = dict(database.execute("SELECT name,sha256 FROM image_integrity"))
    finally:
        database.close()
    for name in images:
        if checksums.get(name[7:]) != digest(root / name):
            raise ValueError(f"La imagen {name} no coincide con su huella original.")


def create_backup(root, prefix="manual", expected_version=SCHEMA_VERSION):
    """Caller holds the application mutation lock (or runs before serving)."""
    root = Path(root).resolve()
    folder = root / "backups"
    folder.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = folder / f"{prefix}-{stamp}-{uuid.uuid4().hex[:8]}.zip"
    temporary = destination.with_suffix(".partial")
    try:
        with tempfile.TemporaryDirectory(prefix="armario-snapshot-") as work:
            snapshot = Path(work) / "wardrobe.sqlite"
            source, target = connect(root / "wardrobe.sqlite"), connect(snapshot)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
            version, images, _ = check_database(snapshot, expected_version)
            files = {"wardrobe.sqlite": snapshot} | {name: root / name for name in images}
            for name in images:
                check_image(root / name)
            if version >= 5:
                verify_image_baselines(snapshot, images, root)
            manifest = {
                "format": 1,
                "schema_version": version,
                "created_at": stamp,
                "files": {name: digest(path) for name, path in sorted(files.items())},
            }
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, path in files.items():
                    archive.write(path, name)
                archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        verify_backup(temporary)
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def unpack_verified(archive_path, staging):
    """Reject traversal, symlinks, duplicate names, oversized ZIPs and bad hashes."""
    with zipfile.ZipFile(archive_path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)) or len(names) > 20002:
            raise ValueError("La copia contiene entradas duplicadas o demasiados archivos.")
        if sum(entry.file_size for entry in entries) > MAX_UNPACKED_BYTES:
            raise ValueError("La copia supera el límite de 4 GB descomprimidos.")
        if "manifest.json" not in names or archive.getinfo("manifest.json").file_size > 4 * 1024**2:
            raise ValueError("El manifiesto de la copia no es válido.")
        manifest = json.loads(archive.read("manifest.json"))
        if (
            not isinstance(manifest, dict)
            or type(manifest.get("format")) is not int
            or manifest.get("format") != 1
            or type(manifest.get("schema_version")) is not int
            or not isinstance(manifest.get("files"), dict)
        ):
            raise ValueError("El formato de la copia no es compatible.")
        files = manifest["files"]
        if set(names) != set(files) | {"manifest.json"} or "wardrobe.sqlite" not in files:
            raise ValueError("El contenido de la copia no coincide con su manifiesto.")
        for name, expected_hash in files.items():
            if name != "wardrobe.sqlite" and not (
                name.startswith("images/") and IMAGE_NAME.fullmatch(name[7:])
            ):
                raise ValueError("La copia contiene rutas no permitidas.")
            entry = archive.getinfo(name)
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("La copia contiene enlaces simbólicos.")
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            if name.startswith("images/"):
                check_image(target)
            if digest(target) != expected_hash:
                raise ValueError(f"El archivo {name} no supera la comprobación de integridad.")
        version, images, counts = check_database(
            staging / "wardrobe.sqlite", manifest.get("schema_version")
        )
        if images != set(files) - {"wardrobe.sqlite"}:
            raise ValueError("La copia no incluye exactamente las imágenes de su inventario.")
        if version >= 5:
            verify_image_baselines(staging / "wardrobe.sqlite", images, staging)
        (staging / "images").mkdir(exist_ok=True)
    return {"schema_version": version, **counts}


def verify_backup(path):
    with tempfile.TemporaryDirectory(prefix="armario-verify-") as work:
        return unpack_verified(path, Path(work))


def restore_backup(path, root):
    """Caller holds process_lock; no server may be running."""
    root = Path(root).resolve()
    root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{root.name}-restore-", dir=root.parent))
    old = root.with_name(f"{root.name}-before-restore-{uuid.uuid4().hex[:12]}")
    try:
        result = unpack_verified(path, staging)
        if root.exists():
            if (root / "wardrobe.sqlite").exists():
                try:
                    previous_version, _, _ = check_database(root / "wardrobe.sqlite")
                    create_backup(root, prefix="before-restore", expected_version=previous_version)
                except (sqlite3.DatabaseError, ValueError, FileNotFoundError):
                    # Preserve the complete original directory even when it cannot be backed up.
                    pass
            root.rename(old)
        try:
            staging.rename(root)
        except Exception:
            if old.exists():
                old.rename(root)
            raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return result, old if old.exists() else None
