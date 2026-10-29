"""Validate and re-encode photographs; file names never come from the client."""

import hashlib
import io
import uuid
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 24_000_000


def store_image(upload, root):
    data = upload.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Cada fotografía debe ocupar menos de 10 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
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
    names = (f"{token}.webp", f"{token}-thumb.webp")
    try:
        image.thumbnail((2400, 2400))
        image.save(root / names[0], "WEBP", quality=92, method=4, exif=b"")
        image.thumbnail((560, 560))
        image.save(root / names[1], "WEBP", quality=85, method=4, exif=b"")
    except Exception:
        remove_files(root, names)
        raise
    return {"filename": names[0], "thumbnail": names[1], "digest": hashlib.sha256(data).hexdigest()}


def remove_files(root, names):
    for name in names:
        (root / name).unlink(missing_ok=True)
