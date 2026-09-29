"""translate(): protect the values, send the text to a backend, put the values back, flag doubts.

Chat must never break because translation did: if the backend fails, the reader gets the original
text, flagged, and can still read "See original".
"""

import logging
import re
from collections import OrderedDict

from lang.backends import TranslationBackend, get_backend
from lang.models import Lang, Translation
from lang.protection import ProtectedValue, protect, restore
from lang.quality import FLAG_REASON_AMOUNT_CHANGED, FLAG_REASON_UNAVAILABLE, find_quality_problem

logger = logging.getLogger(__name__)

# isiZulu and isiXhosa attach "at" to a value with a hyphen ("ngo-9am"), but backends leave a space
# after the hyphen ("ngo- 9am"). Only closes the gap before a number, price or phone number.
HYPHEN_GAP_PATTERN = re.compile(r"\b(\w+-) +(?=[R+\d])")
HYPHEN_PREFIX_LANGS = {"zu", "xh"}

# Azure drops the spaces next to protected values ("It takes[[0]] to get", "in[[0]]minutes"). In
# English a value is never glued to a word, so put the spaces back and remove any before
# punctuation. isiZulu and isiXhosa attach prefixes on purpose ("ngo-10:00"), so they're left alone.
GLUED_BEFORE_PLACEHOLDER_PATTERN = re.compile(r"(?<=[A-Za-z])(?=\[\[\d+\]\])")
GLUED_AFTER_PLACEHOLDER_PATTERN = re.compile(r"(\[\[\d+\]\])(?=[A-Za-z])")
SPACE_BEFORE_PUNCTUATION_PATTERN = re.compile(r"(\[\[\d+\]\])\s+([?!.,])")
SPACING_FIX_LANGS = {"en"}

# "9am" means nothing to someone who reads isiZulu, and a bare "9" loses whether it's morning or
# night. So the digits stay protected and am/pm becomes the local word for that time of day:
# "9am" -> "ngo-9 ekuseni". Words from our isiZulu and isiXhosa speaker (P3).
AM_PM_TIME_PATTERN = re.compile(r"^(\d{1,2})(:\d{2})?\s?(am|pm)$", re.IGNORECASE)
TIME_OF_DAY_WORDS: dict[str, dict[str, str]] = {
    "zu": {
        "morning": "ekuseni",
        "afternoon": "ntambama",
        "evening": "kusihlwa",
        "night": "ebusuku",
    },
    "xh": {
        "morning": "ntseni",
        "afternoon": "njakalanga",
        "evening": "ngokuhlwa",
        "night": "busuku",
    },
}
MORNING_START_HOUR = 5  # 24-hour clock: 5:00 to 11:59 is morning
AFTERNOON_START_HOUR = 12
EVENING_START_HOUR = 18
NIGHT_START_HOUR = 22

# Each text is translated once, which saves the free Azure allowance and keeps wording consistent.
CACHE_MAX_ENTRIES = 5000
_translation_cache: OrderedDict[tuple[str, str, str | None], Translation] = OrderedDict()


def translate(
    text: str,
    target_lang: Lang,
    source_lang: Lang | None = None,
    backend: TranslationBackend | None = None,
) -> Translation:
    """Translate text into target_lang, never changing prices, times, dates, phones or addresses.

    source_lang is the sender's language when known; otherwise the backend detects it.
    backend is for tests and the translation test; normally TRANSLATION_BACKEND picks it, and only
    those translations are cached.
    """
    if source_lang == target_lang or not text.strip():
        return Translation(
            text=text, original=text, source_lang=source_lang or target_lang, flagged=False
        )

    cache_key = (text, target_lang, source_lang)
    if backend is None and cache_key in _translation_cache:
        _translation_cache.move_to_end(cache_key)
        return _translation_cache[cache_key]

    try:
        chosen_backend = backend or get_backend()
    except Exception as error:  # A missing key, an unknown backend name, a library not installed
        logger.warning("Translation backend not set up, showing the original: %s", error)
        return unavailable_translation(text, source_lang)

    translation = translate_uncached(text, target_lang, source_lang, chosen_backend)
    if translation.flagged:
        logger.warning(
            "Flagged translation (%s, %s to %s): %r",
            translation.flag_reason,
            translation.source_lang,
            target_lang,
            text,
        )
    elif backend is None:
        remember_translation(cache_key, translation)
    return translation


def translate_uncached(
    text: str, target_lang: Lang, source_lang: Lang | None, backend: TranslationBackend
) -> Translation:
    """Protect, translate, restore and check one text."""
    protected = protect(text)
    try:
        backend_translation = backend.translate(protected.text, target_lang, source_lang)
    except Exception:  # Any failure at all: chat must never break because translation did
        logger.exception("Translation failed, showing the original")
        return unavailable_translation(text, source_lang)

    placeholder_text = backend_translation.text
    if target_lang in SPACING_FIX_LANGS:
        placeholder_text = fix_spacing_around_placeholders(placeholder_text)
    values = [localize_time(value, target_lang) for value in protected.values]
    restored = restore(placeholder_text, values)
    translated_text = restored.text
    if target_lang in HYPHEN_PREFIX_LANGS:
        translated_text = HYPHEN_GAP_PATTERN.sub(r"\1", translated_text)

    if restored.missing or restored.unexpected:
        flag_reason = FLAG_REASON_AMOUNT_CHANGED
    else:
        flag_reason = find_quality_problem(protected.text, backend_translation.text)
    return Translation(
        text=translated_text,
        original=text,
        source_lang=backend_translation.source_lang,
        flagged=flag_reason is not None,
        flag_reason=flag_reason,
    )


def unavailable_translation(text: str, source_lang: Lang | None) -> Translation:
    """The original text, flagged, for when translation isn't possible right now."""
    return Translation(
        text=text,
        original=text,
        source_lang=source_lang or "en",
        flagged=True,
        flag_reason=FLAG_REASON_UNAVAILABLE,
    )


def get_time_of_day(hour_24: int) -> str:
    """Morning, afternoon, evening or night for an hour on the 24-hour clock."""
    if MORNING_START_HOUR <= hour_24 < AFTERNOON_START_HOUR:
        return "morning"
    if AFTERNOON_START_HOUR <= hour_24 < EVENING_START_HOUR:
        return "afternoon"
    if EVENING_START_HOUR <= hour_24 < NIGHT_START_HOUR:
        return "evening"
    return "night"


def localize_time(value: ProtectedValue, target_lang: Lang) -> ProtectedValue:
    """Turn an am/pm time into digits plus the local time-of-day word ("9am" -> "9 ekuseni")."""
    match = AM_PM_TIME_PATTERN.match(value.text)
    if value.kind != "time" or target_lang not in TIME_OF_DAY_WORDS or not match:
        return value
    hour_text, minutes_text, am_or_pm = match.groups()
    hour_12 = int(hour_text) % 12
    hour_24 = hour_12 + 12 if am_or_pm.lower() == "pm" else hour_12
    word = TIME_OF_DAY_WORDS[target_lang][get_time_of_day(hour_24)]
    return value.model_copy(update={"text": f"{hour_text}{minutes_text or ''} {word}"})


def fix_spacing_around_placeholders(text: str) -> str:
    """Put back the spaces a backend dropped around [[n]] placeholders in English text."""
    text = GLUED_BEFORE_PLACEHOLDER_PATTERN.sub(" ", text)
    text = GLUED_AFTER_PLACEHOLDER_PATTERN.sub(r"\1 ", text)
    return SPACE_BEFORE_PUNCTUATION_PATTERN.sub(r"\1\2", text)


def remember_translation(cache_key: tuple[str, str, str | None], translation: Translation) -> None:
    """Keep a good translation, dropping the oldest once the cache is full."""
    _translation_cache[cache_key] = translation
    if len(_translation_cache) > CACHE_MAX_ENTRIES:
        _translation_cache.popitem(last=False)
