"""Web push: a notification on the phone's lock screen, even when Fixa isn't open.

Needs VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY (generate them with `python -m fixa_api.push`) and
VAPID_SUBJECT (a mailto: address). Without the keys push is simply off: the inbox still fills up.

Sending happens on a background thread with its own database session, so a slow or dead push
service never holds up the request that caused it. A subscription the push service says is gone
(404 or 410) is deleted.
"""

import base64
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from sqlmodel import Session, select

from fixa_api.db import engine
from fixa_api.models import PushSubscription

logger = logging.getLogger(__name__)

GONE_STATUSES = {404, 410}
PUSH_TIME_TO_LIVE_SECONDS = 60 * 60  # a notification older than an hour isn't worth showing
DEFAULT_SUBJECT = "mailto:team@fixa.app"

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="push")


def public_key() -> str | None:
    """The key browsers subscribe with (applicationServerKey), or None when push is off."""
    if not os.environ.get("VAPID_PRIVATE_KEY"):
        return None
    return os.environ.get("VAPID_PUBLIC_KEY") or None


def subject() -> str:
    value = os.environ.get("VAPID_SUBJECT", "").strip()
    if not value:
        return DEFAULT_SUBJECT
    return value if value.startswith(("mailto:", "https://")) else f"mailto:{value}"


def send_to_user(user_id: str, title: str, body: str, url: str) -> None:
    """Queue a push to every browser the person subscribed. Returns at once; never raises."""
    if public_key() is None:
        return
    payload = json.dumps({"title": title, "body": body, "url": url})
    _executor.submit(_send_now, user_id, payload)


def _send_now(user_id: str, payload: str) -> None:
    from pywebpush import WebPushException, webpush

    with Session(engine) as session:
        subscriptions = session.exec(
            select(PushSubscription).where(PushSubscription.user_id == user_id)
        ).all()
        for subscription in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": subscription.endpoint,
                        "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                    },
                    data=payload,
                    vapid_private_key=os.environ["VAPID_PRIVATE_KEY"],
                    vapid_claims={"sub": subject()},
                    ttl=PUSH_TIME_TO_LIVE_SECONDS,
                )
            except WebPushException as problem:
                status = problem.response.status_code if problem.response is not None else None
                if status in GONE_STATUSES:
                    session.delete(subscription)
                    session.commit()
                else:
                    logger.warning("Push to %s failed: %s", user_id, status or problem)
            except Exception:  # a push must never take anything else down
                logger.exception("Push to %s crashed", user_id)


def generate_keys() -> tuple[str, str]:
    """A new (public, private) VAPID key pair, both base64url without padding."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    private = ec.generate_private_key(ec.SECP256R1())
    private_bytes = private.private_numbers().private_value.to_bytes(32, "big")
    public_bytes = private.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )

    def encode(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    return encode(public_bytes), encode(private_bytes)


if __name__ == "__main__":
    public, private = generate_keys()
    print("Add these to .env (keep the private key out of git and chat):")
    print(f"VAPID_PUBLIC_KEY={public}")
    print(f"VAPID_PRIVATE_KEY={private}")
