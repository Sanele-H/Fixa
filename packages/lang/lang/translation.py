"""translate(): protect the values, send the text to a backend, put the values back, flag doubts.

Chat must never break because translation did: if the backend fails, the reader gets the original
text, flagged, and can still read "See original".
"""

import logging

import anthropic

from lang.backends import TranslationBackend, TranslationFailedError, get_backend
from lang.models import Lang, Translation
from lang.protection import protect, restore

logger = logging.getLogger(__name__)

try:
    from google.api_core.exceptions import GoogleAPIError
except ImportError:  # The Google library is optional

    class GoogleAPIError(Exception):  # noqa: N818 - stands in for Google's own class name
        """Never raised: used only when the Google library isn't installed."""


BACKEND_ERRORS = (TranslationFailedError, anthropic.APIError, GoogleAPIError, OSError, KeyError)

FLAG_REASON_VALUES_LOST = "Some numbers, prices or times may not have come through"
FLAG_REASON_UNAVAILABLE = "Translation is not available right now, showing the original"


def translate(
    text: str,
    target_lang: Lang,
    source_lang: Lang | None = None,
    backend: TranslationBackend | None = None,
) -> Translation:
    """Translate text into target_lang, never changing prices, times, dates, phones or addresses.

    source_lang is the sender's language when known; otherwise the backend detects it.
    backend is for tests and the translation test; normally TRANSLATION_BACKEND picks it.
    """
    if source_lang == target_lang or not text.strip():
        return Translation(text=text, original=text, source_lang=target_lang, flagged=False)

    protected = protect(text)
    try:
        backend_translation = (backend or get_backend()).translate(
            protected.text, target_lang, source_lang
        )
    except BACKEND_ERRORS as error:
        logger.warning("Translation failed, showing the original: %s", error)
        return Translation(
            text=text,
            original=text,
            source_lang=source_lang or "en",
            flagged=True,
            flag_reason=FLAG_REASON_UNAVAILABLE,
        )

    restored = restore(backend_translation.text, protected.values)
    return Translation(
        text=restored.text,
        original=text,
        source_lang=backend_translation.source_lang,
        flagged=bool(restored.missing),
        flag_reason=FLAG_REASON_VALUES_LOST if restored.missing else None,
    )
