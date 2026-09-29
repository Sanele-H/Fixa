"""Sending SMS. Africa's Talking (sandbox or live) when keys are set, otherwise an outbox.

An SMS must never break the request that caused it: `send_safely` swallows and logs failures.
Only the sender's user id and a masked number are logged, never the message (it can hold a phone
number and an address).
"""

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)

AFRICASTALKING_SANDBOX_URL = "https://api.sandbox.africastalking.com/version1/messaging"
AFRICASTALKING_LIVE_URL = "https://api.africastalking.com/version1/messaging"
AFRICASTALKING_SUCCESS_CODES = {100, 101, 102}  # processed, sent, queued
REQUEST_TIMEOUT_SECONDS = 10
SOUTH_AFRICA_DIALLING_CODE = "27"


@dataclass
class SmsResult:
    ok: bool
    message_id: str | None = None
    error: str | None = None


class SmsSender(Protocol):
    def send(self, to: str, message: str) -> SmsResult: ...


def to_international(phone: str) -> str:
    """ "082 000 0001" -> "+27820000001", the format Africa's Talking needs."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith(SOUTH_AFRICA_DIALLING_CODE) and len(digits) == 11:
        return f"+{digits}"
    return f"+{SOUTH_AFRICA_DIALLING_CODE}{digits.removeprefix('0')}"


def mask(phone: str) -> str:
    """Enough of a number to tell messages apart in a log, not enough to use it."""
    return "***" + phone[-3:]


class AfricasTalkingSender:
    """Africa's Talking bulk SMS over its REST API. The username "sandbox" uses the sandbox,
    where messages show up in the web simulator instead of on real phones."""

    def __init__(self, username: str, api_key: str, client: httpx.Client | None = None):
        self.username = username
        self.api_key = api_key
        self.url = AFRICASTALKING_SANDBOX_URL if username == "sandbox" else AFRICASTALKING_LIVE_URL
        self.client = client or httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS)

    def send(self, to: str, message: str) -> SmsResult:
        try:
            response = self.client.post(
                self.url,
                headers={"apiKey": self.api_key, "Accept": "application/json"},
                data={"username": self.username, "to": to_international(to), "message": message},
            )
            response.raise_for_status()
            recipients = response.json()["SMSMessageData"]["Recipients"]
        except (httpx.HTTPError, KeyError, ValueError) as problem:
            return SmsResult(ok=False, error=f"Africa's Talking request failed: {problem!r}")
        if not recipients or recipients[0].get("statusCode") not in AFRICASTALKING_SUCCESS_CODES:
            status = recipients[0].get("status") if recipients else "no recipient"
            return SmsResult(ok=False, error=f"Africa's Talking refused it: {status}")
        return SmsResult(ok=True, message_id=recipients[0].get("messageId"))


@dataclass
class OutboxSender:
    """Keeps messages in memory instead of sending them. Used when no keys are set (local
    development) and in tests."""

    sent: list[tuple[str, str]] = field(default_factory=list)

    def send(self, to: str, message: str) -> SmsResult:
        self.sent.append((to_international(to), message))
        return SmsResult(ok=True, message_id=f"outbox-{len(self.sent)}")


DEFAULT_OUTBOX = OutboxSender()


def get_sms_sender() -> SmsSender:
    """Africa's Talking if AFRICASTALKING_API_KEY is set, else the outbox. FastAPI dependency;
    tests replace it."""
    api_key = os.environ.get("AFRICASTALKING_API_KEY")
    if not api_key:
        return DEFAULT_OUTBOX
    return AfricasTalkingSender(os.environ.get("AFRICASTALKING_USERNAME", "sandbox"), api_key)


def send_safely(sender: SmsSender, to: str, message: str, purpose: str) -> SmsResult:
    """Send one SMS and never raise. A failure is logged (masked number, no text)."""
    try:
        result = sender.send(to, message)
    except Exception:  # anything at all: the job must not fail because an SMS did
        logger.exception("SMS for %s to %s failed", purpose, mask(to))
        return SmsResult(ok=False, error="sender crashed")
    if not result.ok:
        logger.warning("SMS for %s to %s not sent: %s", purpose, mask(to), result.error)
    return result
