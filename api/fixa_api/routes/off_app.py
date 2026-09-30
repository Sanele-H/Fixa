"""Off-app jobs and the SMS reply webhook."""

import datetime as dt
import logging
import os
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from fixa_api import off_app
from fixa_api.auth import require_role
from fixa_api.blocking import refuse_if_prohibited
from fixa_api.db import get_session
from fixa_api.models import Provider
from fixa_api.sms import SmsSender, get_sms_sender

logger = logging.getLogger(__name__)
router = APIRouter(tags=["off-app jobs"])

ProviderUser = Annotated[Provider, Depends(require_role("provider"))]
DbSession = Annotated[Session, Depends(get_session)]
Sender = Annotated[SmsSender, Depends(get_sms_sender)]


class NewOffAppJob(BaseModel):
    customer_phone: str = Field(max_length=30)
    trade_task: str = Field(min_length=1, max_length=60)
    date: dt.date
    suburb: str = Field(min_length=1, max_length=60)
    amount_rands: int | None = Field(default=None, gt=0, le=1_000_000)


@router.post("/api/off-app-jobs", status_code=201)
def log_off_app_job(body: NewOffAppJob, provider: ProviderUser, session: DbSession, sender: Sender):
    """Log a past job. The customer is texted to confirm it, and it only counts once they do.
    The customer's number is never sent back."""
    refuse_if_prohibited(session, provider, body.trade_task, "off_app_job")
    try:
        job = off_app.log_off_app_job(
            session,
            provider,
            sender,
            body.customer_phone,
            body.trade_task,
            body.date,
            body.suburb,
            body.amount_rands,
        )
    except off_app.OffAppError as problem:
        raise HTTPException(
            status_code=problem.status_code,
            detail={"error": problem.error, "message": problem.detail},
        ) from None
    return {
        "id": job.id,
        "state": job.state,
        "trade_task": job.trade_task,
        "date": job.date.isoformat(),
        "suburb": job.suburb,
        "amount_rands": job.amount_rands,
    }


def check_webhook_secret(secret: str | None) -> None:
    """Africa's Talking doesn't sign its callbacks, so the callback address carries a secret:
    set SMS_WEBHOOK_SECRET and register .../api/sms/inbound?secret=<it>. Without one (local
    development) anyone could post replies, so set it wherever the API is public."""
    expected = os.environ.get("SMS_WEBHOOK_SECRET")
    if not expected:
        logger.warning("SMS_WEBHOOK_SECRET is not set: the SMS webhook accepts anyone")
        return
    if not secret or not secrets.compare_digest(secret, expected):
        raise HTTPException(status_code=403, detail="Not allowed")


@router.post("/api/sms/inbound")
def receive_sms(
    session: DbSession,
    from_phone: Annotated[str, Form(alias="from", max_length=30)],
    text: Annotated[str, Form(max_length=500)],
    secret: str | None = None,
) -> dict[str, str]:
    """Africa's Talking posts a customer's reply here. It always answers the same way, so a
    stranger learns nothing about which numbers or codes exist."""
    check_webhook_secret(secret)
    outcome = off_app.handle_reply(session, from_phone, text)
    logger.info("SMS reply handled: %s", outcome)
    return {"status": "ok"}
