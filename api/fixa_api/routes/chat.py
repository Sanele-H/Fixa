"""Chat on a job. The app polls GET every 3 seconds with ?after=<message_id>."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from fixa_api import messages
from fixa_api.auth import current_user, find_user_by_id
from fixa_api.blocking import refuse_if_prohibited
from fixa_api.db import get_session
from fixa_api.models import Customer, Job, Provider
from fixa_api.notifications import notify

router = APIRouter(prefix="/api", tags=["chat"])

User = Annotated[Customer | Provider, Depends(current_user)]
DbSession = Annotated[Session, Depends(get_session)]


class NewMessage(BaseModel):
    text: str = Field(min_length=1, max_length=messages.MAX_MESSAGE_CHARS)
    # Only a customer with several quoting providers needs this, to say who the message is for.
    provider_id: str | None = None


def find_chat_job(session: Session, job_id: str, user: Customer | Provider) -> Job:
    """The job, or 404 for anyone who isn't in its chat (the same 404 as a job that isn't there)."""
    job = session.get(Job, job_id)
    if job is None or not messages.is_chat_party(session, job, user):
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/messages")
def read_messages(job_id: str, user: User, session: DbSession, after: str | None = None):
    job = find_chat_job(session, job_id, user)
    return [
        messages.message_view(message, user)
        for message in messages.read_messages(session, job, user, after)
    ]


@router.post("/jobs/{job_id}/messages", status_code=201)
def send_message(job_id: str, body: NewMessage, user: User, session: DbSession):
    job = find_chat_job(session, job_id, user)
    refuse_if_prohibited(session, user, body.text, "message")
    try:
        message = messages.send_message(session, job, user, body.text, body.provider_id)
    except messages.ChatError as problem:
        raise HTTPException(status_code=problem.status_code, detail=problem.detail) from None
    recipient = find_user_by_id(session, message.recipient_id)
    notify(session, recipient, "message", job.id, name=user.display_name)
    return messages.message_view(message, user)
