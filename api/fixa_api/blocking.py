"""Refusing requests for illegal electricity work, and restricting accounts that keep trying.

Job posts, quotes, chat messages and logged off-app jobs are checked with the language package.
A flagged text is never published, stored as a live post or delivered. The person gets a 422 with
the reason and the legal route in their own language, and the attempt is logged for the team.
After MAX_BLOCKS refused attempts in BLOCK_WINDOW the account is restricted until the team
reviews it (delete its row in account_restriction to lift it).
"""

import datetime as dt
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from fixa_api.models import AccountRestriction, BlockLog, Customer, Provider
from lang import find_prohibited, refusal_message

MAX_BLOCKS = 3
BLOCK_WINDOW = dt.timedelta(days=30)
LOGGED_TEXT_LIMIT = 500
RESTRICTED_MESSAGES = {
    "en": "Your account is paused while our team reviews it. Please contact support.",
    "zu": (
        "I-akhawunti yakho imiswe kancane ngenkathi ithimba lethu liyibuyekeza. "
        "Sicela uthinte usizo."
    ),
    "xh": (
        "I-akhawunti yakho imiswe okwethutyana ngelixa iqela lethu liyihlola. "
        "Nceda uqhagamshelane nenkxaso."
    ),
}


class ProhibitedRequestError(Exception):
    """A refused request. main.py turns it into the 422 {"error", "category", "message"}."""

    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category
        self.message = message


def ensure_not_restricted(session: Session, user: Customer | Provider) -> None:
    """403 for an account the team has paused. Reading still works; publishing doesn't."""
    if session.get(AccountRestriction, user.id) is not None:
        message = RESTRICTED_MESSAGES.get(user.lang) or RESTRICTED_MESSAGES["en"]
        raise HTTPException(
            status_code=403, detail={"error": "account_restricted", "message": message}
        )


def recent_block_count(session: Session, user: Customer | Provider, now: dt.datetime) -> int:
    since = now - BLOCK_WINDOW
    query = select(BlockLog).where(BlockLog.user_id == user.id, BlockLog.at >= since)
    return len(list(session.exec(query)))


def refuse_if_prohibited(session: Session, user: Customer | Provider, text: str, kind: str) -> None:
    """Raise ProhibitedRequestError if the text asks for or offers illegal electricity work, after
    logging it (and restricting the account if this was one attempt too many). Does nothing for
    text that is fine. Call it before anything is stored or sent."""
    ensure_not_restricted(session, user)
    category = find_prohibited(text)
    if category is None:
        return
    now = dt.datetime.now(dt.UTC)
    session.add(
        BlockLog(
            id=f"block_{uuid.uuid4().hex[:10]}",
            user_id=user.id,
            kind=kind,
            category=category,
            text=text[:LOGGED_TEXT_LIMIT],
            at=now,
        )
    )
    session.flush()
    if recent_block_count(session, user, now) >= MAX_BLOCKS and (
        session.get(AccountRestriction, user.id) is None
    ):
        session.add(
            AccountRestriction(
                user_id=user.id, since=now, reason=f"{MAX_BLOCKS} refused requests in 30 days"
            )
        )
    session.commit()  # the log must survive the refusal
    raise ProhibitedRequestError(category, refusal_message(category, user.lang))
