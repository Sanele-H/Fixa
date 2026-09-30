"""Chat rules: who may talk on a job, who a message goes to, and what each reader is shown.

Every message is scanned by the language package before it is stored, so a phone number or
address typed before the job is confirmed never reaches the other side. The reader gets the
hidden-contact text translated into their own language, with the untranslated hidden-contact
text one tap away ("See original").
"""

import datetime as dt
import uuid
from typing import Any

from sqlmodel import Session, select

from fixa_api import job_states as states
from fixa_api.job_views import can_see_job, is_job_customer, is_job_provider, iso
from fixa_api.models import Customer, Job, Message, Provider, Quote
from lang import get_scam_warning_texts, scan_message, translate

MAX_MESSAGE_CHARS = 1000


class ChatError(Exception):
    """A chat request that can't be done. status_code is the HTTP answer."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def is_chat_party(session: Session, job: Job, user: Customer | Provider) -> bool:
    """The job's customer; its accepted provider; or, while the job still asks for quotes, a
    provider who can see it. Once a provider is chosen the others are out of the chat."""
    if is_job_customer(job, user) or is_job_provider(job, user):
        return True
    return (
        job.state in states.OPEN_FOR_QUOTES
        and user.role == "provider"
        and can_see_job(session, job, user)
    )


def customer_recipient(session: Session, job: Job, provider_id: str | None) -> str:
    """Which provider a customer's message goes to: the chosen one, else the one named, else the
    only one who has quoted. Messages are never shown to competing providers."""
    if job.provider_id:
        return job.provider_id
    quoted = {
        quote.provider_id for quote in session.exec(select(Quote).where(Quote.job_id == job.id))
    }
    if provider_id:
        if provider_id not in quoted:
            raise ChatError(422, "That provider has not quoted on this job")
        return provider_id
    if len(quoted) == 1:
        return next(iter(quoted))
    if not quoted:
        raise ChatError(409, "No provider has quoted on this job yet")
    raise ChatError(422, "Say which provider this message is for (provider_id)")


def send_message(
    session: Session, job: Job, sender: Customer | Provider, text: str, provider_id: str | None
) -> Message:
    """Scan, store and return one message from sender."""
    if job.state == states.CANCELLED:
        raise ChatError(409, "This job was cancelled")
    if not is_chat_party(session, job, sender):
        raise ChatError(404, "Job not found")
    recipient_id = (
        customer_recipient(session, job, provider_id)
        if sender.role == "customer"
        else job.customer_id
    )
    unlocked = job.state in states.UNLOCKED_STATES
    result = scan_message(text, sender.lang, contacts_unlocked=unlocked)
    message = Message(
        id=f"msg_{uuid.uuid4().hex[:10]}",
        job_id=job.id,
        sender_id=sender.id,
        recipient_id=recipient_id,
        original_text=text,
        safe_text=result.safe_text,
        original_lang=sender.lang,
        contacts_hidden=result.safe_text != text,
        scam_warnings=result.scam_warnings,
        sent_at=dt.datetime.now(dt.UTC),
    )
    session.add(message)
    session.commit()
    return message


def can_read(message: Message, job: Job, reader: Customer | Provider) -> bool:
    """A customer reads every thread on their job; a provider reads only their own."""
    if is_job_customer(job, reader):
        return True
    return reader.id in (message.sender_id, message.recipient_id)


def read_messages(
    session: Session, job: Job, reader: Customer | Provider, after_id: str | None
) -> list[Message]:
    """The messages this reader may see, oldest first, only those after after_id if given."""
    query = select(Message).where(Message.job_id == job.id).order_by(Message.sent_at, Message.id)
    messages = [message for message in session.exec(query) if can_read(message, job, reader)]
    if after_id:
        ids = [message.id for message in messages]
        if after_id in ids:
            messages = messages[ids.index(after_id) + 1 :]
    return messages


def message_view(message: Message, reader: Customer | Provider) -> dict[str, Any]:
    """The Message shape of the contract, in the reader's language. `original` is the safe text
    as written, never the raw text: the other side must not see a hidden number by tapping
    "See original"."""
    translation = translate(message.safe_text, reader.lang, message.original_lang)
    return {
        "id": message.id,
        "job_id": message.job_id,
        "sender_id": message.sender_id,
        "recipient_id": message.recipient_id,
        "text": translation.text,
        "original": message.safe_text,
        "original_lang": message.original_lang,
        "flagged": translation.flagged,
        "flag_reason": translation.flag_reason,
        "contacts_hidden": message.contacts_hidden,
        "scam_warnings": get_scam_warning_texts(message.scam_warnings, reader.lang),
        "sent_at": iso(message.sent_at),
    }


def safe_text_for(text: str, sender_lang: str) -> str:
    """Text a person wrote before the job is confirmed (a job post, a quote note), with contact
    details hidden."""
    return scan_message(text, sender_lang, contacts_unlocked=False).safe_text
