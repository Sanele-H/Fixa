"""Photo upload and viewing."""

import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from fixa_api import photos
from fixa_api.auth import current_user
from fixa_api.db import get_session
from fixa_api.job_views import can_see_job
from fixa_api.models import Customer, Job, Photo, Provider

router = APIRouter(prefix="/api", tags=["photos"])

MAX_UPLOADS_PER_DAY = 30
User = Annotated[Customer | Provider, Depends(current_user)]
DbSession = Annotated[Session, Depends(get_session)]
Store = Annotated[photos.PhotoStore, Depends(photos.get_photo_store)]
optional_bearer = HTTPBearer(auto_error=False)


@router.post("/photos")
def upload_photo(photo: UploadFile, user: User, session: DbSession, store: Store):
    """Save a photo. It is re-encoded first, so it holds no location data. Attach it to a job by
    sending its photo_id when posting the job."""
    now = dt.datetime.now(dt.UTC)
    since = now - dt.timedelta(days=1)
    recent = session.exec(select(Photo).where(Photo.owner_id == user.id, Photo.created_at >= since))
    if len(list(recent)) >= MAX_UPLOADS_PER_DAY:
        raise HTTPException(status_code=429, detail="Too many photos today. Try again tomorrow.")
    try:
        data = photos.clean_image(photo.file.read(photos.MAX_UPLOAD_BYTES + 1))
    except photos.PhotoError as problem:
        raise HTTPException(
            status_code=problem.status_code,
            detail={"error": problem.error, "message": problem.detail},
        ) from None
    photo_id = f"photo_{uuid.uuid4().hex[:16]}"
    try:
        store.save(photo_id, data)
    except Exception:
        raise HTTPException(status_code=502, detail="Couldn't save the photo. Try again.") from None
    session.add(Photo(id=photo_id, owner_id=user.id, size_bytes=len(data), created_at=now))
    session.commit()
    return {"photo_id": photo_id, "url": photos.signed_photo_url(photo_id)}


def may_view(session: Session, photo: Photo, viewer: Customer | Provider) -> bool:
    """The uploader, or anyone who may see the job the photo is attached to."""
    if photo.owner_id == viewer.id:
        return True
    job = session.exec(
        select(Job).where(Job.photo_url == f"{photos.PHOTO_URL_PREFIX}{photo.id}")
    ).first()
    return job is not None and can_see_job(session, job, viewer)


@router.get("/photos/{photo_id}")
def read_photo(
    photo_id: str,
    request: Request,
    session: DbSession,
    store: Store,
    exp: int | None = None,
    sig: str | None = None,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_bearer)] = None,
):
    """The photo, for a valid signed link (what a job's photo_url is) or a signed-in user who
    may see it. Anyone else gets a 404, the same as for a photo that doesn't exist."""
    row = session.get(Photo, photo_id)
    allowed = photos.signature_is_valid(photo_id, exp, sig)
    if not allowed and credentials is not None:
        viewer = current_user(credentials, session)
        allowed = row is not None and may_view(session, row, viewer)
    data = store.load(photo_id) if allowed and row is not None else None
    if data is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    return Response(
        data,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )
