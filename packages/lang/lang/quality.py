"""Cheap checks that catch a bad translation, so the app can show the original alongside it.

These come from Sanele's Azure and Gemini test (27 Sep): Setswana and Sepedi came back in English,
one sentence came back as a single word, and Setswana repeated a phrase. Each check returns a
flag reason, and translate() flags the message with the first one that fails.
"""

import re

FLAG_REASON_AMOUNT_CHANGED = "amount changed"
FLAG_REASON_NOT_TRANSLATED = "not translated"
FLAG_REASON_LENGTH_MISMATCH = "length mismatch"
FLAG_REASON_REPEATED_TEXT = "repeated text"
FLAG_REASON_UNAVAILABLE = "translation unavailable"

# Starting guesses from Sanele's page, to tune once we see real failures.
MIN_LENGTH_RATIO = 0.5
MAX_LENGTH_RATIO = 2.0
MIN_CHARACTERS_FOR_LENGTH_CHECK = 20  # "Yebo" → "Yes" is fine; short texts vary a lot
MIN_WORDS_FOR_SAME_TEXT_CHECK = 3  # "OK" or "R450?" may rightly come back unchanged
REPEATED_RUN_WORD_COUNT = 4

PLACEHOLDER_PATTERN = re.compile(r"\[\[\s*\d+\s*\]\]?")
WORD_PATTERN = re.compile(r"\w+")


def get_words(text: str) -> list[str]:
    """Lowercase words with placeholders and punctuation removed."""
    return WORD_PATTERN.findall(PLACEHOLDER_PATTERN.sub(" ", text).lower())


def is_not_translated(source_text: str, translated_text: str) -> bool:
    """True when the backend handed the text back unchanged, ignoring case and punctuation."""
    source_words = get_words(source_text)
    return len(source_words) >= MIN_WORDS_FOR_SAME_TEXT_CHECK and source_words == get_words(
        translated_text
    )


def is_length_mismatch(source_text: str, translated_text: str) -> bool:
    """True when the translation is less than half or more than twice the original's length."""
    source_length = len(source_text.strip())
    if source_length < MIN_CHARACTERS_FOR_LENGTH_CHECK:
        return False
    length_ratio = len(translated_text.strip()) / source_length
    return not MIN_LENGTH_RATIO <= length_ratio <= MAX_LENGTH_RATIO


def has_repeated_run(source_text: str, translated_text: str) -> bool:
    """True when the same run of 4 or more words appears twice in the translation but not in the
    original, which is how a backend looks when it gets stuck in a loop."""

    def repeated_runs(text: str) -> set[tuple[str, ...]]:
        words = get_words(text)
        runs = [
            tuple(words[index : index + REPEATED_RUN_WORD_COUNT])
            for index in range(len(words) - REPEATED_RUN_WORD_COUNT + 1)
        ]
        return {run for run in runs if runs.count(run) > 1}

    return bool(repeated_runs(translated_text) - repeated_runs(source_text))


def find_quality_problem(source_text: str, translated_text: str) -> str | None:
    """Return the flag reason for the first check that fails, or None if the translation looks OK.

    Both texts are the protected versions (values swapped for placeholders), so a long phone
    number or address doesn't distort the length check.
    """
    if is_not_translated(source_text, translated_text):
        return FLAG_REASON_NOT_TRANSLATED
    if is_length_mismatch(source_text, translated_text):
        return FLAG_REASON_LENGTH_MISMATCH
    if has_repeated_run(source_text, translated_text):
        return FLAG_REASON_REPEATED_TEXT
    return None
