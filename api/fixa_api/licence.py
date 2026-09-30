"""Work that the law says only a licensed provider may do.

Electrical work that needs a Certificate of Compliance, and geyser installations (which need a
PIRB-registered plumber). A job like that is shown only to licensed providers, never ranked to
unlicensed ones, and can't be quoted on by them.

The check reads the customer's own words, so it is a keyword check, not a judgement: it leans
towards "needs a licence", because a licensed provider can always do unlicensed work, but not the
other way round. Customers can also tick "licensed provider only" themselves.
"""

import re

GEYSER_WORDS = {"geyser", "igeyser", "igiza"}
INSTALL_WORDS = {"install", "installation", "installed", "installing", "faka", "ukufaka", "ufakelo"}
# A replaced part of a geyser isn't a geyser installation.
GEYSER_PART_WORDS = {"valve", "element", "thermostat", "pressure"}
ELECTRICAL_PHRASES = [
    "certificate of compliance",
    "electrical certificate",
    "coc",
    "rewire",
    "rewiring",
    "rewired",
    "wiring",
    "db board",
    "distribution board",
    "consumer unit",
    "new circuit",
]


def words_in(text: str) -> set[str]:
    return set(re.findall(r"[a-z']+", text.lower()))


def needs_licence_for(trade: str, description: str) -> bool:
    """True if this trade and description describe work only a licensed provider may do."""
    words = words_in(description)
    if trade == "plumbing":
        return (
            bool(words & GEYSER_WORDS)
            and bool(words & INSTALL_WORDS)
            and not words & GEYSER_PART_WORDS
        )
    if trade == "electrical":
        lowered = description.lower()
        return any(re.search(rf"\b{re.escape(phrase)}\b", lowered) for phrase in ELECTRICAL_PHRASES)
    return False
