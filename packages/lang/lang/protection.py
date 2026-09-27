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

STREET_WORDS = (
    "street|st|road|rd|avenue|ave|drive|dr|crescent|cres|lane|close|way|place|"
    "straat|weg|laan|rylaan|singel"
)
MONTH_WORDS = (
    "jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|"
    "sep|sept|september|oct|october|nov|november|dec|december"
)

# Order matters: earlier patterns win, so a phone number is never split into smaller numbers.
PROTECTED_PATTERNS = [
    ("email", r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    ("link", r"(?:https?://|www\.)\S+"),
    ("phone", r"(?<!\w)(?:\+27|0)(?:[\s-]?\d){9}(?!\d)"),
    ("address", rf"\b\d{{1,5}}[a-z]?\s+(?:[A-Z][\w'-]*\s+){{1,3}}(?:{STREET_WORDS})\b\.?"),
    ("price", r"\bR\s?\d{1,3}(?:[\s,]\d{3})*(?:[.,]\d{2})?(?!\d)"),
    ("price", r"\b\d{1,3}(?:[\s,]\d{3})*\s?(?:rand|randi)\b"),
    ("date", r"\b\d{4}-\d{2}-\d{2}\b"),
    ("date", r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b"),
    ("date", rf"\b\d{{1,2}}\s(?:{MONTH_WORDS})\b\.?"),
    ("time", r"\b\d{1,2}[:h]\d{2}\b"),
    ("time", r"\b\d{1,2}\s?(?:am|pm)\b"),
    ("number", r"\b\d+(?:[.,]\d+)?\s?(?:mm|cm|m|kg|l|litres?|m2)?\b"),
]
COMPILED_PATTERNS = [
    (kind, re.compile(pattern, re.IGNORECASE)) for kind, pattern in PROTECTED_PATTERNS
]


class ProtectedValue(BaseModel):
    """One value taken out of the text, in the order it appeared."""

    kind: str  # "price", "time", "date", "phone", "address", "email", "link" or "number"
    text: str


class ProtectedText(BaseModel):
    """Text ready for a translation backend, plus the values to put back afterwards."""

    text: str
    values: list[ProtectedValue]


class RestoredText(BaseModel):
    """Translated text with the values back in place."""

    text: str
    missing: list[ProtectedValue]  # Placeholders the backend dropped. Non-empty means flag it.


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
    """Put the protected values back into translated text, and list any the backend dropped."""
    found_indexes: set[int] = set()

    def put_value_back(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if index >= len(values):
            return match.group(0)
        found_indexes.add(index)
        return values[index].text

    restored_text = PLACEHOLDER_PATTERN.sub(put_value_back, translated_text)
    missing = [value for index, value in enumerate(values) if index not in found_indexes]
    return RestoredText(text=restored_text, missing=missing)
