"""Keep prices, times, dates, phone numbers and addresses exact through translation.

protect() swaps each value for a numbered placeholder before the text goes to a translation
backend, and restore() puts the values back afterwards. A backend never sees "R450", so it can't
turn it into "R45" or "450 rand". If a placeholder goes missing in translation, restore() reports
it, and translate() flags the message as "This may not have translated well".
"""

import re

from pydantic import BaseModel

PLACEHOLDER_FORMAT = "[[{index}]]"
# Backends sometimes add spaces inside the brackets or drop one bracket, so restore() accepts those.
PLACEHOLDER_PATTERN = re.compile(r"\[\[?\s*(\d+)\s*\]\]?")

# What scan_message() puts in place of a contact detail. It's protected like a value, so a backend
# can't reword it ("[oxhumana naye ufihliwe…]"), and translate() puts it back in the reader's
# language.
HIDDEN_CONTACT_TEXT = "[contact hidden until the job is confirmed]"

# The word for each time of day, said after the hour ("ngo-9 ekuseni"). From P3, a first-language
# isiZulu speaker; the isiXhosa words still need an isiXhosa speaker's check.
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
LOCAL_TIME_WORDS = "|".join(word for words in TIME_OF_DAY_WORDS.values() for word in words.values())

STREET_WORDS = (
    "street|st|road|rd|avenue|ave|drive|dr|crescent|cres|lane|close|way|place|"
    "straat|weg|laan|rylaan|singel"
)
MONTH_WORDS = (
    r"jan|january|feb|february|mar|march|apr|april|may(?!\s+be\b)|jun|june|jul|july|aug|august|"
    r"sep|sept|september|oct|october|nov|november|dec|december"
)

# Patterns run ignoring case, so "[A-Z]" in a street name also matches lowercase words. These two
# guards stop ordinary sentences reading as addresses: a number followed by a time or distance
# ("10 minutes down the road", "2 days to close it") isn't a street number, and small linking
# words ("down", "the") are never part of a street name. safety.py uses them too.
QUANTITY_WORDS = (
    "min|mins|minute|minutes|hr|hrs|hour|hours|day|days|week|weeks|month|months|"
    "km|m|metre|metres|meter|meters"
)
LINKING_WORDS = (
    "the|a|an|to|from|down|up|of|in|on|at|by|near|past|off|over|across|into|for|and|or|"
    "this|that|my|your|it|is"
)
NOT_A_QUANTITY = rf"(?!(?:{QUANTITY_WORDS})\b)"
NOT_A_LINKING_WORD = rf"(?!(?:{LINKING_WORDS})\b)"

# Rand amounts as South Africans write them: "R1 500" (the official style, with a space, a
# no-break space or a thin space), "R1,500", "R4500", "R2500.00" or "R1 500,50". A new line is
# never a thousands separator, and a spaced group that starts a phone number isn't part of the
# price, so "R450 082 123 4567" is R450. quotes.py reads amounts with the same pattern.
THOUSANDS_SPACE = "[    ]"
NOT_A_PHONE = r"(?!0\d{2}[ -]?\d{3}[ -]?\d{4}(?!\d))"
THOUSANDS_SEPARATOR = rf"(?:,|{THOUSANDS_SPACE}{NOT_A_PHONE})"
RAND_DIGITS = rf"\d+(?:{THOUSANDS_SEPARATOR}\d{{3}})*"
RAND_AMOUNT = rf"{RAND_DIGITS}(?:[.,]\d{{2}})?"

# Order matters: earlier patterns win, so a phone number is never split into smaller numbers.
# isiZulu and isiXhosa attach prefixes straight onto numbers ("ngoR1200", "ngo10:30", "e-12"),
# so numbers are bounded by "not a digit" rather than by a word boundary. The rand sign is a
# case-sensitive capital R, so "for 5 days" is not read as a price.
PROTECTED_PATTERNS = [
    ("hidden", re.escape(HIDDEN_CONTACT_TEXT)),
    ("email", r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    ("link", r"(?:https?://|www\.)\S+"),
    ("phone", r"(?<!\d)(?:\+27|0)(?:[\s-]?\d){9}(?!\d)"),
    (
        "address",
        rf"(?<!\d)\d{{1,5}}[a-z]?\s+{NOT_A_QUANTITY}"
        rf"(?:{NOT_A_LINKING_WORD}[A-Z][\w'-]*\s+){{1,3}}(?:{STREET_WORDS})\b\.?",
    ),
    ("price", rf"(?<!\d)(?-i:R){THOUSANDS_SPACE}?{RAND_AMOUNT}(?!\d)"),
    ("price", rf"(?<!\d){RAND_DIGITS}{THOUSANDS_SPACE}?(?:rand|randi)\b"),
    ("date", r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)"),
    ("date", r"(?<!\d)\d{1,2}/\d{1,2}(?:/\d{2,4})?(?!\d)"),
    ("date", rf"(?<!\d)\d{{1,2}}\s(?:{MONTH_WORDS})\b\.?"),
    # "9 ekuseni" is one time, so translate() can say it the reader's way ("9am")
    ("time", rf"(?<!\d)\d{{1,2}}(?:[:h]\d{{2}})?\s(?:{LOCAL_TIME_WORDS})\b"),
    ("time", r"(?<!\d)\d{1,2}(?::\d{2})?\s?(?:am|pm)\b"),  # before 10:30, so "3:30pm" stays whole
    ("time", r"(?<!\d)\d{1,2}[:h]\d{2}(?!\d)"),
    ("number", r"(?<![\d.,])\d+(?:[.,]\d+)?(?:\s?(?:mm|cm|m|kg|l|litres?|m2)\b)?"),
]
COMPILED_PATTERNS = [
    (kind, re.compile(pattern, re.IGNORECASE)) for kind, pattern in PROTECTED_PATTERNS
]


class ProtectedValue(BaseModel):
    """One value taken out of the text, in the order it appeared."""

    # "price", "time", "date", "phone", "address", "email", "link", "number", or "hidden" for the
    # hidden-contact marker
    kind: str
    text: str


class ProtectedText(BaseModel):
    """Text ready for a translation backend, plus the values to put back afterwards."""

    text: str
    values: list[ProtectedValue]


class RestoredText(BaseModel):
    """Translated text with the values back in place."""

    text: str
    missing: list[ProtectedValue]  # Placeholders the backend dropped. Non-empty means flag it.
    # Placeholders the backend made up or repeated, such as [[3]] when there were two values, or
    # [[0]] twice. Non-empty means flag it too.
    unexpected: list[str] = []


def find_protected_spans(text: str) -> list[tuple[int, int, str]]:
    """Return (start, end, kind) for every value to protect, left to right, never overlapping."""
    spans: list[tuple[int, int, str]] = []
    for kind, pattern in COMPILED_PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span()
            overlaps_earlier = any(
                start < taken_end and taken_start < end for taken_start, taken_end, _ in spans
            )
            if not overlaps_earlier:
                spans.append((start, end, kind))
    return sorted(spans)


def protect(text: str) -> ProtectedText:
    """Swap every price, time, date, phone number, address and other number for a placeholder."""
    values: list[ProtectedValue] = []
    pieces: list[str] = []
    position = 0
    for start, end, kind in find_protected_spans(text):
        pieces.append(text[position:start])
        pieces.append(PLACEHOLDER_FORMAT.format(index=len(values)))
        values.append(ProtectedValue(kind=kind, text=text[start:end].rstrip()))
        position = start + len(text[start:end].rstrip())
    pieces.append(text[position:])
    return ProtectedText(text="".join(pieces), values=values)


def restore(translated_text: str, values: list[ProtectedValue]) -> RestoredText:
    """Put the protected values back into translated text, and list any the backend dropped,
    made up or repeated. A made-up placeholder stays as it is; a repeated one gets its value."""
    found_indexes: set[int] = set()
    unexpected: list[str] = []

    def put_value_back(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if index >= len(values):
            unexpected.append(match.group(0))
            return match.group(0)
        if index in found_indexes:
            unexpected.append(match.group(0))
        found_indexes.add(index)
        return values[index].text

    restored_text = PLACEHOLDER_PATTERN.sub(put_value_back, translated_text)
    missing = [value for index, value in enumerate(values) if index not in found_indexes]
    return RestoredText(text=restored_text, missing=missing, unexpected=unexpected)
