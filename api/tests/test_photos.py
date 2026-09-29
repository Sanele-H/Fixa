"""Photo upload, cleaning, storage and signed viewing links."""

import io
import json
import os
import re
from pathlib import Path

import httpx
import pytest
from PIL import Image

from fixa_api import photos
from fixa_api.fixtures import FIXTURES_PATH
from fixa_api.main import app
from fixa_api.models import Photo
from fixa_api.photos import (
    LocalPhotoStore,
    SupabasePhotoStore,
    clean_image,
    get_photo_store,
    signed_photo_url,
)

LINDIWE = "082 000 0001"  # cust_001
OTHER_CUSTOMER = "082 000 0002"
PLUMBER = "071 000 0001"
ELECTRICIAN = "071 000 0006"

GPS_IFD_TAG = 0x8825
ORIENTATION_TAG = 0x0112


def make_image(size=(400, 300), fmt="JPEG", exif_gps=False, orientation=None) -> bytes:
    image = Image.new("RGB", size, (200, 30, 30))
    exif = Image.Exif()
    if exif_gps:
        exif[GPS_IFD_TAG] = {1: "S", 2: (26.0, 11.0, 30.0), 3: "E", 4: (28.0, 2.0, 0.0)}
    if orientation:
        exif[ORIENTATION_TAG] = orientation
    buffer = io.BytesIO()
    image.save(buffer, fmt, exif=exif) if fmt == "JPEG" else image.save(buffer, fmt)
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def local_store(tmp_path):
    """Every test saves photos into its own temporary folder, never into api/uploads."""
    store = LocalPhotoStore(tmp_path)
    app.dependency_overrides[get_photo_store] = lambda: store
    yield store
    app.dependency_overrides.pop(get_photo_store, None)


@pytest.fixture
def lindiwe(log_in):
    return log_in(LINDIWE)


def upload(client, headers, data=None, name="leak.jpg", content_type="image/jpeg"):
    files = {"photo": (name, make_image() if data is None else data, content_type)}
    return client.post("/api/photos", files=files, headers=headers)


def open_result(content: bytes) -> Image.Image:
    return Image.open(io.BytesIO(content))


# --- cleaning an upload ---------------------------------------------------------------------


def test_an_upload_comes_back_with_an_id_and_a_signed_link(seeded_client, lindiwe):
    response = upload(seeded_client, lindiwe)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == set(json.loads((FIXTURES_PATH / "photo.json").read_text(encoding="utf-8")))
    assert re.fullmatch(r"photo_[0-9a-f]{16}", body["photo_id"])
    assert re.fullmatch(rf"/api/photos/{body['photo_id']}\?exp=\d+&sig=[0-9a-f]{{32}}", body["url"])


def test_gps_and_other_metadata_are_stripped(seeded_client, lindiwe):
    source = make_image(exif_gps=True)
    assert open_result(source).getexif().get_ifd(GPS_IFD_TAG)  # the test photo really has GPS

    url = upload(seeded_client, lindiwe, source).json()["url"]
    saved = open_result(seeded_client.get(url).content)

    assert not saved.getexif()
    assert "exif" not in saved.info


def test_a_sideways_photo_is_turned_upright_before_the_metadata_goes(seeded_client, lindiwe):
    source = make_image(size=(400, 300), orientation=6)  # "rotate 90 degrees" in the metadata

    saved = open_result(
        seeded_client.get(upload(seeded_client, lindiwe, source).json()["url"]).content
    )

    assert saved.size == (300, 400)


def test_a_big_photo_is_shrunk_and_a_png_becomes_a_jpeg(seeded_client, lindiwe):
    big = upload(seeded_client, lindiwe, make_image(size=(4000, 3000)))
    png = upload(seeded_client, lindiwe, make_image(fmt="PNG"), "leak.png", "image/png")

    big_saved = open_result(seeded_client.get(big.json()["url"]).content)
    png_saved = open_result(seeded_client.get(png.json()["url"]).content)

    assert max(big_saved.size) == photos.MAX_SIDE_PX
    assert (big_saved.format, png_saved.format) == ("JPEG", "JPEG")


@pytest.mark.parametrize(
    ("data", "name", "content_type"),
    [
        (b"just some text", "leak.jpg", "image/jpeg"),
        (
            b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
            "a.svg",
            "image/svg+xml",
        ),
        (b"%PDF-1.4 not a photo", "a.pdf", "application/pdf"),
        (make_image(fmt="GIF"), "a.gif", "image/gif"),
        (b"", "empty.jpg", "image/jpeg"),
    ],
)
def test_anything_that_is_not_a_real_photo_is_refused(
    seeded_client, lindiwe, data, name, content_type
):
    response = upload(seeded_client, lindiwe, data, name, content_type)

    assert response.status_code == 415
    assert response.json()["detail"]["error"] == "not_an_image"


def test_a_file_pretending_to_be_a_jpeg_by_its_name_is_still_refused(seeded_client, lindiwe):
    assert upload(seeded_client, lindiwe, b"MZ\x90\x00 an exe", "photo.jpg").status_code == 415


def test_an_upload_over_three_megabytes_is_refused(seeded_client, lindiwe):
    response = upload(seeded_client, lindiwe, os.urandom(photos.MAX_UPLOAD_BYTES + 10))

    assert response.status_code == 413
    assert response.json()["detail"]["error"] == "too_big"


def test_a_decompression_bomb_is_refused(seeded_client, lindiwe):
    bomb = make_image(size=(9000, 9000), fmt="PNG")  # a few KB of file, 81 million pixels

    assert len(bomb) < photos.MAX_UPLOAD_BYTES
    assert upload(seeded_client, lindiwe, bomb, "b.png", "image/png").status_code == 415


def test_uploading_needs_a_sign_in(seeded_client):
    assert upload(seeded_client, {}).status_code == 401


def test_a_provider_can_upload_too(seeded_client, log_in):
    assert upload(seeded_client, log_in(PLUMBER)).status_code == 200


def test_thirty_photos_a_day_at_most(seeded_client, lindiwe, monkeypatch):
    monkeypatch.setattr("fixa_api.routes.photos.MAX_UPLOADS_PER_DAY", 2)
    assert upload(seeded_client, lindiwe).status_code == 200
    assert upload(seeded_client, lindiwe).status_code == 200

    assert upload(seeded_client, lindiwe).status_code == 429


def test_a_failing_store_means_nothing_is_recorded(seeded_client, seeded_session, lindiwe):
    class Broken:
        def save(self, key, data):
            raise OSError("disk full")

        def load(self, key):
            return None

    app.dependency_overrides[get_photo_store] = lambda: Broken()

    response = upload(seeded_client, lindiwe)

    assert response.status_code == 502
    assert seeded_session.query(Photo).count() == 0


# --- viewing --------------------------------------------------------------------------------


def test_the_signed_link_works_without_a_sign_in_header(seeded_client, lindiwe):
    url = upload(seeded_client, lindiwe).json()["url"]

    response = seeded_client.get(url)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "private" in response.headers["cache-control"]


def test_a_link_without_its_signature_is_a_404(seeded_client, lindiwe):
    photo_id = upload(seeded_client, lindiwe).json()["photo_id"]

    assert seeded_client.get(f"/api/photos/{photo_id}").status_code == 404
    assert seeded_client.get(f"/api/photos/{photo_id}?exp=9999999999&sig=abc").status_code == 404


def test_a_tampered_or_borrowed_signature_does_not_work(seeded_client, lindiwe):
    first = upload(seeded_client, lindiwe).json()
    second = upload(seeded_client, lindiwe).json()
    sig = re.search(r"sig=([0-9a-f]+)", first["url"]).group(1)
    exp = re.search(r"exp=(\d+)", first["url"]).group(1)

    assert (
        seeded_client.get(f"/api/photos/{second['photo_id']}?exp={exp}&sig={sig}").status_code
        == 404
    )
    assert (
        seeded_client.get(
            f"/api/photos/{first['photo_id']}?exp={int(exp) + 1}&sig={sig}"
        ).status_code
        == 404
    )


def test_an_old_link_has_expired(seeded_client, lindiwe):
    photo_id = upload(seeded_client, lindiwe).json()["photo_id"]

    assert seeded_client.get(signed_photo_url(photo_id, now=1)).status_code == 404


def test_the_uploader_can_view_with_their_token(seeded_client, lindiwe):
    photo_id = upload(seeded_client, lindiwe).json()["photo_id"]

    assert seeded_client.get(f"/api/photos/{photo_id}", headers=lindiwe).status_code == 200


def test_someone_else_cannot_view_a_photo_that_is_not_on_a_job_they_can_see(
    seeded_client, lindiwe, log_in
):
    photo_id = upload(seeded_client, lindiwe).json()["photo_id"]

    assert seeded_client.get(f"/api/photos/{photo_id}", headers=log_in(PLUMBER)).status_code == 404
    assert (
        seeded_client.get(f"/api/photos/{photo_id}", headers=log_in(OTHER_CUSTOMER)).status_code
        == 404
    )


def test_an_unknown_photo_is_a_404(seeded_client, lindiwe):
    assert seeded_client.get("/api/photos/photo_nope", headers=lindiwe).status_code == 404
    assert (
        seeded_client.get("/api/photos/..%2F..%2Fetc%2Fpasswd", headers=lindiwe).status_code == 404
    )


# --- photos on jobs -------------------------------------------------------------------------


def post_job(client, headers, **changes):
    body = {
        "description": "Geyser leaking",
        "lang": "en",
        "trade": "plumbing",
        "urgency": "urgent",
        "size": "small",
        "suburb": "Braamfontein",
    } | changes
    return client.post("/api/jobs", json=body, headers=headers)


def test_a_job_shows_its_photo_to_the_providers_who_can_see_the_job(seeded_client, lindiwe, log_in):
    photo_id = upload(seeded_client, lindiwe).json()["photo_id"]
    job = post_job(seeded_client, lindiwe, photo_id=photo_id).json()

    assert job["photo_url"].startswith(f"/api/photos/{photo_id}?exp=")
    assert seeded_client.get(job["photo_url"]).status_code == 200
    plumber = log_in(PLUMBER)
    seen = seeded_client.get(f"/api/jobs/{job['id']}", headers=plumber).json()
    assert seeded_client.get(seen["photo_url"]).status_code == 200
    assert seeded_client.get(f"/api/photos/{photo_id}", headers=plumber).status_code == 200
    assert (
        seeded_client.get(f"/api/photos/{photo_id}", headers=log_in(ELECTRICIAN)).status_code == 404
    )


def test_the_feed_carries_the_photo_link_too(seeded_client, lindiwe, log_in):
    photo_id = upload(seeded_client, lindiwe).json()["photo_id"]
    job = post_job(seeded_client, lindiwe, photo_id=photo_id).json()

    feed = seeded_client.get("/api/feed", headers=log_in(PLUMBER)).json()

    shown = next(item for item in feed if item["id"] == job["id"])
    assert seeded_client.get(shown["photo_url"]).status_code == 200


def test_a_job_without_a_photo_has_no_photo_url(seeded_client, lindiwe):
    assert post_job(seeded_client, lindiwe).json()["photo_url"] is None


def test_only_your_own_unused_photo_can_go_on_a_job(seeded_client, lindiwe, log_in):
    mine = upload(seeded_client, lindiwe).json()["photo_id"]
    theirs = upload(seeded_client, log_in(OTHER_CUSTOMER)).json()["photo_id"]

    assert post_job(seeded_client, lindiwe, photo_id=theirs).status_code == 422
    assert post_job(seeded_client, lindiwe, photo_id="photo_nope").status_code == 422
    assert post_job(seeded_client, lindiwe, photo_id=mine).status_code == 201
    again = post_job(seeded_client, lindiwe, photo_id=mine)
    assert again.status_code == 422
    assert again.json()["detail"]["error"] == "invalid_photo"


# --- the stores -----------------------------------------------------------------------------


def test_the_local_store_saves_and_loads_and_never_leaves_its_folder(tmp_path):
    store = LocalPhotoStore(tmp_path)

    store.save("photo_abc", b"data")

    assert store.load("photo_abc") == b"data"
    assert store.load("photo_missing") is None
    with pytest.raises(ValueError):
        store.save("../escape", b"data")
    assert not (tmp_path.parent / "escape.jpg").exists()


def supabase_store(handler) -> SupabasePhotoStore:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SupabasePhotoStore("https://x.supabase.co/", "service-key", "photos", client)


def test_the_supabase_store_posts_and_gets_with_the_service_key():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(
            (
                request.method,
                str(request.url),
                request.headers["authorization"],
                request.headers["apikey"],
            )
        )
        return httpx.Response(200, content=b"jpegbytes")

    store = supabase_store(handler)
    store.save("photo_abc", b"jpegbytes")

    assert store.load("photo_abc") == b"jpegbytes"
    url = "https://x.supabase.co/storage/v1/object/photos/photo_abc.jpg"
    assert seen == [
        ("POST", url, "Bearer service-key", "service-key"),
        ("GET", url, "Bearer service-key", "service-key"),
    ]


def test_the_supabase_store_says_none_for_a_missing_photo_and_raises_on_errors():
    assert supabase_store(lambda request: httpx.Response(404)).load("photo_abc") is None
    with pytest.raises(httpx.HTTPStatusError):
        supabase_store(lambda request: httpx.Response(500)).load("photo_abc")


def test_the_store_comes_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("PHOTO_DIR", str(tmp_path))
    assert isinstance(get_photo_store(), LocalPhotoStore)
    assert get_photo_store().directory == Path(tmp_path)

    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "k")
    assert isinstance(get_photo_store(), SupabasePhotoStore)


def test_clean_image_output_is_deterministic_in_type():
    assert clean_image(make_image(fmt="PNG"))[:3] == b"\xff\xd8\xff"  # a JPEG
