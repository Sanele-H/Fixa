"""Pull prices, times and numbers out before translation and put them back unchanged after.

Owner: Role 1. This is the green-highlighted part of the demo: "R450" and "10:00" must come
through exactly. backend/tests/test_token_protection.py lists the cases to beat.

Also keep fixa.domain.tokens.MASKED_CONTACT_TOKEN unchanged.

Open question for your 30-message test: which placeholder format survives each backend best?
Try a few and record the results.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProtectedText:
    """Text ready to send to a translation backend.

    Attributes:
        text: The original text with each protected value swapped for a numbered placeholder.
        protected_values: The values that were swapped out. Placeholder N stands for item N.
    """

    text: str
    protected_values: tuple[str, ...]


@dataclass(frozen=True)
class RestoredText:
    """A translation with the protected values put back.

    Attributes:
        text: The final translated text.
        missing_values: Values whose placeholder the backend lost. If this is not empty,
            the translation must be flagged as unsure.
    """

    text: str
    missing_values: tuple[str, ...]


def protect_tokens(text: str) -> ProtectedText:
    """Swap prices, times, dates, measurements, plain numbers and masked contacts for placeholders.

    TODO (Role 1, Day 3).
    """
    raise NotImplementedError("TODO Role 1: protect_tokens")


def restore_tokens(translated_text: str, protected_text: ProtectedText) -> RestoredText:
    """Put protected values back into `translated_text`, tolerating placeholders the backend
    re-spaced, and report any that went missing.

    TODO (Role 1, Day 3).
    """
    raise NotImplementedError("TODO Role 1: restore_tokens")
