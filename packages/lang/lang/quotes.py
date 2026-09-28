"""extract_quote(): pull a rand amount and a day or time out of a chat message.

Run it on the original message, never a translation, so the price on a quote card is exactly what
the tradesperson wrote. The day comes back in English ("Tuesday"), whichever language it was
written in, so P2 can turn it into a date. Sanele's voice test showed spoken prices are unreliable,
so the app's typed quote form stays the main way to quote; this fills it in from chat.
"""

import re

from lang.models import Quote

PRICE_PATTERNS = [
    re.compile(r"(?<!\d)(?-i:R)\s?(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)(?!\d)"),
    re.compile(r"(?<!\d)(\d+(?:[\s,]\d{3})*)\s?(?:rand|randi)\b", re.IGNORECASE),
]
CENTS_PATTERN = re.compile(r"[.,]\d{2}$")

# Each day in English, isiZulu and isiXhosa. The isiZulu and isiXhosa forms carry the "on" prefix
# ("ngoLwesibili" is "on Tuesday"), so they match anywhere inside a word.
DAY_FORMS: dict[str, list[str]] = {
    "Monday": ["monday", "msombuluko", "mvulo"],
    "Tuesday": ["tuesday", "lwesibili", "lwesibini"],
    "Wednesday": ["wednesday", "lwesithathu"],
    "Thursday": ["thursday", "lwesine"],
    "Friday": ["friday", "lwesihlanu"],
    "Saturday": ["saturday", "mgqibelo"],
    "Sunday": ["sunday", "sonto", "cawa"],
    "today": ["today", "namuhla", "namhlanje"],
    "tomorrow": ["tomorrow", "kusasa", "ngomso"],
}
TIME_PATTERN = re.compile(
    r"(?<!\d)(\d{1,2}(?::\d{2})?\s?(?:am|pm)|\d{1,2}[:h]\d{2})(?!\d)", re.IGNORECASE
)


def parse_rands(amount_text: str) -> int:
    """Turn "1 200", "1,250.50" or "450" into whole rands, with 50 cents rounding up."""
    has_cents = CENTS_PATTERN.search(amount_text) is not None
    digits = re.sub(r"\D", "", amount_text)
    return (int(digits) + 50) // 100 if has_cents else int(digits)


def find_first_price(text: str) -> int | None:
    """The first rand amount in the text, whichever way it's written."""
    matches = [match for pattern in PRICE_PATTERNS for match in pattern.finditer(text)]
    if not matches:
        return None
    first = min(matches, key=lambda match: match.start())
    return parse_rands(first.group(1))


def find_day(text: str) -> str | None:
    """The first day mentioned, as an English word, or None."""
    lowered_text = text.lower()
    positions = [
        (lowered_text.find(form), day)
        for day, forms in DAY_FORMS.items()
        for form in forms
        if form in lowered_text
    ]
    return min(positions)[1] if positions else None


def extract_quote(text: str) -> Quote | None:
    """Pull a rand amount and a time out of a chat message, or None if there is no price.

    "Ngingafika ngoLwesibili ngo-10:00, R450" gives Quote(amount_rands=450, when="Tuesday 10:00").
    When a message has several prices ("R350 call-out, then R200 an hour"), the first one wins.
    """
    amount_rands = find_first_price(text)
    if amount_rands is None:
        return None
    time_match = TIME_PATTERN.search(text)
    when_parts = [part for part in (find_day(text), time_match and time_match.group(1)) if part]
    return Quote(amount_rands=amount_rands, when=" ".join(when_parts) or None)
