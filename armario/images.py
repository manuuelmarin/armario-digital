"""Validate and re-encode photographs; file names never come from the client."""

import hashlib
import io
import uuid
import warnings
from pathlib import Path
from typing import BinaryIO, TypedDict

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 24_000_000


class ImageMetadata(TypedDict):
    filename: str
    thumbnail: str
    preview: str
    digest: str
    width: int
    height: int
    preview_width: int
    thumbnail_width: int


def store_image(upload: BinaryIO, root: Path) -> ImageMetadata:
    data = upload.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Cada fotografía debe ocupar menos de 10 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=("JPEG", "PNG", "WEBP")) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("Utiliza una fotografía JPEG, PNG o WebP.")
                if source.width * source.height > MAX_PIXELS:
                    raise ValueError("La fotografía supera los 24 megapíxeles.")
                source.load()
                image = ImageOps.exif_transpose(source).convert("RGBA")
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise ValueError("No se ha podido leer la fotografía.") from exc
    token = uuid.uuid4().hex
    names = (f"{token}.webp", f"{token}-preview.webp", f"{token}-thumb.webp")
    try:
        image.thumbnail((4096, 4096), Image.Resampling.LANCZOS)
        width, height = image.size
        image.save(root / names[0], "WEBP", quality=94, method=4, exif=b"")
        image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        preview_width = image.width
        image.save(root / names[1], "WEBP", quality=90, method=4, exif=b"")
        image.thumbnail((512, 512), Image.Resampling.LANCZOS)
        thumbnail_width = image.width
        image.save(root / names[2], "WEBP", quality=87, method=4, exif=b"")
    except Exception:
        remove_files(root, names)
        raise
    return {
        "filename": names[0],
        "preview": names[1],
        "thumbnail": names[2],
        "digest": hashlib.sha256(data).hexdigest(),
        "width": width,
        "height": height,
        "preview_width": preview_width,
        "thumbnail_width": thumbnail_width,
    }


def remove_files(root, names):
    for name in names:
        if name:
            (root / name).unlink(missing_ok=True)


def record_integrity(db, root, names):
    """Record a baseline after creating files, in the same transaction as their rows."""
    for name in names:
        with (root / name).open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        db.execute("INSERT INTO image_integrity(name, sha256) VALUES (?, ?)", (name, checksum))
