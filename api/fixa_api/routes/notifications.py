"""The inbox behind the bell, and push subscriptions. See fixa_api/notifications.py and push.py."""

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from fixa_api import notifications, push, safety
from fixa_api.auth import current_user
from fixa_api.db import get_session
from fixa_api.models import Customer, Provider, PushSubscription
from fixa_api.sms import SmsSender, get_sms_sender

router = APIRouter(prefix="/api", tags=["notifications"])

User = Annotated[Customer | Provider, Depends(current_user)]
DbSession = Annotated[Session, Depends(get_session)]
Sender = Annotated[SmsSender, Depends(get_sms_sender)]


class SubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class SubscriptionIn(BaseModel):
    endpoint: str
    keys: SubscriptionKeys


class Unsubscribe(BaseModel):
    endpoint: str


@router.get("/notifications")
def read_notifications(user: User, session: DbSession, sender: Sender):
    """{unread, items: [{id, kind, title, body, job_id, created_at, read}]}, newest first, in
    the reader's language."""
    safety.sweep_missed_timers(session, sender)  # a missed timer shows up even without the loop
    return notifications.read_inbox(session, user)


@router.post("/notifications/read")
def mark_all_read(user: User, session: DbSession):
    notifications.mark_read(session, user, None)
    return notifications.read_inbox(session, user)


@router.post("/notifications/{notification_id}/read")
def mark_one_read(notification_id: str, user: User, session: DbSession):
    notifications.mark_read(session, user, notification_id)
    return notifications.read_inbox(session, user)


@router.get("/push/key")
def read_push_key():
    """The key a browser subscribes with. 404 when push isn't set up on this server."""
    key = push.public_key()
    if key is None:
        raise HTTPException(status_code=404, detail="Push notifications aren't set up")
    return {"public_key": key}


@router.post("/push/subscriptions", status_code=201)
def subscribe(body: SubscriptionIn, user: User, session: DbSession):
    """Remember this browser for the person. Subscribing again replaces the old keys, and the
    same browser sending it twice at once (the app does on opening the inbox) is fine."""
    try:
        save_subscription(session, user, body)
    except IntegrityError:  # the other copy of the same request saved it first
        session.rollback()
        save_subscription(session, user, body)
    return {"subscribed": True}


def save_subscription(session: Session, user: Customer | Provider, body: SubscriptionIn) -> None:
    subscription = session.get(PushSubscription, body.endpoint) or PushSubscription(
        endpoint=body.endpoint,
        user_id=user.id,
        p256dh=body.keys.p256dh,
        auth=body.keys.auth,
        created_at=dt.datetime.now(dt.UTC),
    )
    subscription.user_id, subscription.p256dh, subscription.auth = (
        user.id,
        body.keys.p256dh,
        body.keys.auth,
    )
    session.add(subscription)
    session.commit()


@router.post("/push/subscriptions/remove")
def unsubscribe(body: Unsubscribe, user: User, session: DbSession):
    subscription = session.get(PushSubscription, body.endpoint)
    if subscription is not None and subscription.user_id == user.id:
        session.delete(subscription)
        session.commit()
    return {"subscribed": False}
