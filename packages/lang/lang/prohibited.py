"""Illegal-request check: refuse requests for, or offers of, illegal electricity work.

Illegal connections, tampering with transformers, mini-substations or municipal cables,
bypassing or tampering with meters, and "ghost" prepaid vouchers that give more units than the
official rate. find_prohibited() names the category, or returns None for text that is fine.

It matches tampering-specific phrases from data/prohibited_terms.json (English, isiZulu and
isiXhosa, checked together because people mix languages), never bare words like "meter" or
"transformer". So "can you bypass my prepaid meter" is flagged, while "my prepaid meter isn't
accepting my token" and "the transformer on our street is sparking, who do I call?" pass.

refusal_message() is the explanation a person sees, in their own language, with the legal route.
Each is written once per category and language, not generated. THE ISIZULU AND ISIXHOSA TEXTS ARE
FIRST DRAFTS and need a native speaker before they go in front of people.
"""

import json
import re
from functools import cache
from pathlib import Path

from lang.models import Lang

PROHIBITED_TERMS_PATH = Path(__file__).resolve().parents[3] / "data" / "prohibited_terms.json"
CATEGORIES = [
    "illegal_connection",
    "infrastructure_tampering",
    "meter_tampering",
    "illegal_vouchers",
]
FALLBACK_LANG = "en"

# What is refused, per category, then the same legal route for all of them.
WHAT_IS_REFUSED: dict[str, dict[str, str]] = {
    "illegal_connection": {
        "en": "Illegal electricity connections put lives at risk.",
        "zu": "Ukuxhumela ugesi ngokungemthetho kubeka izimpilo engozini.",
        "xh": "Ukuxhuma umbane ngokungekho mthethweni kubeka ubomi emngciphekweni.",
    },
    "infrastructure_tampering": {
        "en": "Tampering with transformers, mini-substations or municipal cables can kill.",
        "zu": "Ukuphazamisa amatransfoma nezintambo zikamasipala kungabulala.",
        "xh": "Ukuphazamisa iitransfoma neekhebula zikamasipala kunokubulala.",
    },
    "meter_tampering": {
        "en": "Bypassing or tampering with a meter is against the law.",
        "zu": "Ukweqa noma ukuphazamisa imitha kuphambene nomthetho.",
        "xh": "Ukugqitha okanye ukuphazamisa imitha kuchasene nomthetho.",
    },
    "illegal_vouchers": {
        "en": (
            '"Ghost" or cheap prepaid vouchers are not real electricity: '
            "they are a scam or a crime."
        ),
        "zu": (
            'Ama-voucher e-"ghost" noma ashibhile akayona ugesi wangempela: '
            "ukukhohlisa noma ubugebengu."
        ),
        "xh": (
            'Iivawusha ze-"ghost" okanye ezishiphu ayingombane wenene: '
            "kukukhohlisa okanye ulwaphulo-mthetho."
        ),
    },
}
LEGAL_ROUTE: dict[str, str] = {
    "en": (
        "We can't help with this. It is illegal and dangerous. If your meter or connection is "
        "faulty, report it to your municipality or Eskom. "
        "Buy electricity only from official vendors."
    ),
    "zu": (
        "Asikwazi ukukusiza ngalokhu. Kungokungemthetho futhi kuyingozi. Uma imitha noma "
        "uxhumo lwakho lunenkinga, yazise umasipala noma i-Eskom. Thenga ugesi kubathengisi "
        "abasemthethweni kuphela."
    ),
    "xh": (
        "Asinakukunceda ngale nto. Ayikho mthethweni kwaye iyingozi. Ukuba imitha okanye "
        "uqhagamshelo lwakho lunengxaki, xela kumasipala okanye e-Eskom. Thenga umbane "
        "kubathengisi abasemthethweni kuphela."
    ),
}


@cache
def load_patterns() -> dict[str, list[re.Pattern]]:
    """Every language's patterns for each category, compiled once."""
    terms = json.loads(PROHIBITED_TERMS_PATH.read_text(encoding="utf-8"))["categories"]
    return {
        category: [
            re.compile(pattern) for patterns in terms[category].values() for pattern in patterns
        ]
        for category in CATEGORIES
    }


def find_prohibited(text: str) -> str | None:
    """The category of illegal electricity work the text asks for or offers, or None if fine."""
    lowered = " ".join(text.lower().split())
    patterns = load_patterns()
    for category in CATEGORIES:
        if any(pattern.search(lowered) for pattern in patterns[category]):
            return category
    return None


def refusal_message(category: str, lang: Lang) -> str:
    """Why the text was refused and where to go instead, in the reader's language (English if
    the language is missing). Raises KeyError for an unknown category."""
    what = WHAT_IS_REFUSED[category]
    reason = what.get(lang) or what[FALLBACK_LANG]
    route = LEGAL_ROUTE.get(lang) or LEGAL_ROUTE[FALLBACK_LANG]
    return f"{reason} {route}"
