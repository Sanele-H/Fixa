"""Warn the recipient when a message looks like a common scam.

Owner: Role 3. "Keep simple or fake" in the plan: a few rules are enough for the demo.

The API sends warning CODES, not sentences, and the frontend shows them in the reader's
language. Add a code here and a matching string in frontend/src/i18n/strings.js together.
"""

from enum import StrEnum


class ScamWarning(StrEnum):
    """Kinds of suspicious request. Values are what the API sends."""

    UPFRONT_PAYMENT = "upfront_payment"
    SECRET_CODE_REQUEST = "secret_code_request"
    LINK = "link"


def find_scam_warnings(text: str) -> list[ScamWarning]:
    """Return every ScamWarning that `text` triggers, in enum order, without duplicates.

    Args:
        text: A message after contact masking, in the sender's language.

    TODO (Role 3, Day 3): rules for asking for money upfront, PINs/OTPs/passwords and links,
    in every pilot language.
    """
    raise NotImplementedError("TODO Role 3: scam warning rules")
