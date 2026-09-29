"""Photos: checking and cleaning an upload, where it is stored, and signed links to view it.

Uploads are re-encoded, not just saved. That proves the file is a real image, drops the EXIF
data (a phone's photo can carry the GPS location of a home), and keeps files small.

Viewing: a photo link in a job carries an expiring signature, so a plain <img src> works without
the app adding a header. The same route also accepts the signed-in user's token.
"""

import hashlib
import hmac
import io
import os
import time
from pathlib import Path
from typing import Protocol

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

from fixa_api.auth import jwt_secret

MAX_UPLOAD_BYTES = 3 * 1024 * 1024  # the app shrinks photos to a few hundred KB first
MAX_PIXELS = 25_000_000  # refuse "decompression bombs": tiny files that unpack to huge images
MAX_SIDE_PX = 1600
JPEG_QUALITY = 82
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
PHOTO_URL_LIFETIME_SECONDS = 60 * 60
SIGNATURE_LENGTH = 32
DEFAULT_PHOTO_DIRECTORY = Path(__file__).resolve().parents[1] / "uploads"
PHOTO_URL_PREFIX = "/api/photos/"


class PhotoError(Exception):
    """An upload that can't be accepted. `error` is a short code."""

    def __init__(self, status_code: int, error: str, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.error = error
        self.detail = detail


def clean_image(data: bytes) -> bytes:
    """A JPEG of the photo with no metadata, at most MAX_SIDE_PX on its longest side."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise PhotoError(413, "too_big", "That photo is too big. Try a smaller one.")
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        with Image.open(io.BytesIO(data)) as opened:
            if opened.format not in ALLOWED_FORMATS:
                raise PhotoError(415, "not_an_image", "Send a JPEG, PNG or WebP photo.")
            opened.load()
            upright = ImageOps.exif_transpose(opened)
            upright.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX))
            output = io.BytesIO()
            upright.convert("RGB").save(output, "JPEG", quality=JPEG_QUALITY, optimize=True)
    except PhotoError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise PhotoError(415, "not_an_image", "That file isn't a photo we can read.") from None
    return output.getvalue()


# --- storage --------------------------------------------------------------------------------


class PhotoStore(Protocol):
    def save(self, key: str, data: bytes) -> None: ...
    def load(self, key: str) -> bytes | None: ...


class LocalPhotoStore:
    """Photos as files in a folder. For laptops; api/uploads is ignored by git."""

    def __init__(self, directory: Path):
        self.directory = directory

    def path_for(self, key: str) -> Path:
        if not key.replace("_", "").isalnum():  # never let a key climb out of the folder
            raise ValueError("bad photo key")
        return self.directory / f"{key}.jpg"

    def save(self, key: str, data: bytes) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path_for(key).write_bytes(data)

    def load(self, key: str) -> bytes | None:
        path = self.path_for(key)
        return path.read_bytes() if path.exists() else None


class SupabasePhotoStore:
    """Photos in a private Supabase Storage bucket, using the service key (kept on the server).
    Written from Supabase's storage REST API; try it once with real keys before going live."""

    def __init__(
        self, base_url: str, service_key: str, bucket: str, client: httpx.Client | None = None
    ):
        self.base_url = base_url.rstrip("/")
        self.bucket = bucket
        self.headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key}
        self.client = client or httpx.Client(timeout=15)

    def url_for(self, key: str) -> str:
        return f"{self.base_url}/storage/v1/object/{self.bucket}/{key}.jpg"

    def save(self, key: str, data: bytes) -> None:
        response = self.client.post(
            self.url_for(key), content=data, headers={**self.headers, "Content-Type": "image/jpeg"}
        )
        response.raise_for_status()

    def load(self, key: str) -> bytes | None:
        response = self.client.get(self.url_for(key), headers=self.headers)
        if response.status_code in (400, 404):
            return None
        response.raise_for_status()
        return response.content


def get_photo_store() -> PhotoStore:
    """Supabase Storage when SUPABASE_URL and SUPABASE_SERVICE_KEY are set, else a local folder
    (PHOTO_DIR, default api/uploads). FastAPI dependency; tests replace it."""
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY")
    if url and key:
        return SupabasePhotoStore(url, key, os.environ.get("SUPABASE_PHOTO_BUCKET", "photos"))
    return LocalPhotoStore(Path(os.environ.get("PHOTO_DIR") or DEFAULT_PHOTO_DIRECTORY))


# --- signed links ---------------------------------------------------------------------------


def sign(photo_id: str, expires_at: int) -> str:
    message = f"{photo_id}.{expires_at}".encode()
    digest = hmac.new(jwt_secret().encode(), message, hashlib.sha256).hexdigest()
    return digest[:SIGNATURE_LENGTH]


def signed_photo_url(photo_id: str, now: float | None = None) -> str:
    """A link to the photo that works for an hour without any sign-in header."""
    expires_at = int((now if now is not None else time.time()) + PHOTO_URL_LIFETIME_SECONDS)
    return f"{PHOTO_URL_PREFIX}{photo_id}?exp={expires_at}&sig={sign(photo_id, expires_at)}"


def signature_is_valid(photo_id: str, expires: int | None, signature: str | None) -> bool:
    if expires is None or not signature or expires < time.time():
        return False
    return hmac.compare_digest(sign(photo_id, expires), signature)


def photo_id_from_url(photo_url: str) -> str:
    return photo_url.removeprefix(PHOTO_URL_PREFIX).split("?")[0]
