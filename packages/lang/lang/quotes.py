"""extract_quote(): pull a rand amount and a day or time out of a chat message.

Run it on the original message, never a translation, so the price on a quote card is exactly what
the tradesperson wrote. The day comes back in English ("Tuesday"), whichever language it was
written in, so P2 can turn it into a date. Sanele's voice test showed spoken prices are unreliable,
so the app's typed quote form stays the main way to quote; this fills it in from chat.
"""

import re

from lang.models import Quote
from lang.protection import RAND_AMOUNT, RAND_DIGITS, THOUSANDS_SPACE

# The same amounts protect() keeps whole, so "R450" on one line and "200 for the valve" on the
# next is R450, not R450 200.
PRICE_PATTERNS = [
    re.compile(rf"(?<!\d)(?-i:R){THOUSANDS_SPACE}?({RAND_AMOUNT})(?!\d)"),
    re.compile(rf"(?<!\d)({RAND_DIGITS}){THOUSANDS_SPACE}?(?:rand|randi)\b", re.IGNORECASE),
]
CENTS_PATTERN = re.compile(r"[.,]\d{2}$")

# Each day in English, isiZulu and isiXhosa. The isiZulu and isiXhosa forms carry the "on" prefix
# ("ngoLwesibili" is "on Tuesday"), so they match anywhere inside a word. isiZulu "ngeSonto" isn't
# here: iSonto also means "week", so it has its own check below.
DAY_FORMS: dict[str, list[str]] = {
    "Monday": ["monday", "msombuluko", "mvulo"],
    "Tuesday": ["tuesday", "lwesibili", "lwesibini"],
    "Wednesday": ["wednesday", "lwesithathu"],
    "Thursday": ["thursday", "lwesine"],
    "Friday": ["friday", "lwesihlanu"],
    "Saturday": ["saturday", "mgqibelo"],
    "Sunday": ["sunday", "cawa"],
    "today": ["today", "namuhla", "namhlanje"],
    "tomorrow": ["tomorrow", "kusasa", "ngomso"],
}
TIME_PATTERN = re.compile(
    r"(?<!\d)(\d{1,2}(?::\d{2})?\s?(?:am|pm)|\d{1,2}[:h]\d{2})(?!\d)", re.IGNORECASE
)

# "ngeSonto" is "on Sunday", but iSonto also means "week": "ngeSonto elizayo" can mean next Sunday
# or next week, and "kabili ngesonto" is twice a week. So it only counts as Sunday when nothing
# comes after it but a time, a price, or a time of day ("ngeSonto ngo-10:00, R450", "ngeSonto
# ekuseni"), and not after a "times" word. No day beats the wrong day.
NGESONTO_PATTERN = re.compile(r"\bngesonto\b", re.IGNORECASE)
TIMES_WORDS = {"kanye", "kabili", "kathathu", "kane", "kahlanu"}  # once, twice, three times…
LAST_WORD_PATTERN = re.compile(r"(\w+)\W*$")
# What may follow "ngeSonto" once times and prices are taken out: spaces, punctuation, the small
# words that go with a time or price ("ngo-10:00", "u-R450", "at 10am"), and times of day.
AFTER_SUNDAY_PATTERN = re.compile(
    r"(?:[\s,.!?;:-]|\b(?:ngo|u|ngu|yi|at|for|ekuseni|emini|ntambama|kusihlwa|ebusuku)\b)*",
    re.IGNORECASE,
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


def remove_times_and_prices(text: str) -> str:
    """The text with every time and rand amount taken out."""
    text = TIME_PATTERN.sub("", text)
    for pattern in PRICE_PATTERNS:
        text = pattern.sub("", text)
    return text


def find_sunday_position(text: str) -> int | None:
    """Where "ngeSonto" can only mean Sunday, or None (see NGESONTO_PATTERN for the rule)."""
    match = NGESONTO_PATTERN.search(text)
    if match is None:
        return None
    word_before = LAST_WORD_PATTERN.search(text[: match.start()])
    if word_before and word_before.group(1).lower() in TIMES_WORDS:
        return None
    rest = remove_times_and_prices(text[match.end() :])
    return match.start() if AFTER_SUNDAY_PATTERN.fullmatch(rest) else None


def find_day(text: str) -> str | None:
    """The first day mentioned, as an English word, or None."""
    lowered_text = text.lower()
    positions = [
        (lowered_text.find(form), day)
        for day, forms in DAY_FORMS.items()
        for form in forms
        if form in lowered_text
    ]
    sunday_position = find_sunday_position(text)
    if sunday_position is not None:
        positions.append((sunday_position, "Sunday"))
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
