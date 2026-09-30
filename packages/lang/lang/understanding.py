"""understand_job(): turn a customer's description into a trade, urgency and job size.

Words from data/glossary.json point to a trade. isiZulu and isiXhosa attach prefixes ("ipayipi",
"kwepayipi"), so their forms match anywhere inside a word; English words match whole. Urgency and
size come from short word lists in all three languages. The customer always confirms or changes
the suggestion, so a low-confidence guess is fine; the confidence tells the app how sure it is.
"""

import json
import re
from pathlib import Path

from lang.models import JobIntent, JobSize, Lang, Urgency
from lang.prohibited import find_prohibited

GLOSSARY_PATH = Path(__file__).resolve().parents[3] / "data" / "glossary.json"
FALLBACK_TRADE = "other"  # unmatched descriptions fall back to the catch-all trade

NO_MATCH_CONFIDENCE = 0.2
ONE_MATCH_CONFIDENCE = 0.6
TWO_MATCHES_CONFIDENCE = 0.8
MANY_MATCHES_CONFIDENCE = 0.9
TIED_TRADES_CONFIDENCE = 0.4

# Matched anywhere in the lowercased text. isiZulu forms checked by P3; isiXhosa needs a check.
URGENT_FORMS = [
    # English
    "urgent",
    "emergency",
    "asap",
    "right now",
    "burst",
    "flood",
    "everywhere",
    "today",
    "tonight",
    "sparks",
    "smoke",
    "burning",
    "no electricity",
    "no power",
    "no water",
    "exploded",
    "help",
    # isiZulu
    "namuhla",
    "manje",
    "masinya",
    "ngokushesha",
    "igcwele",
    "agcwele",
    "yonke indawo",
    "akukho gesi",
    "awukho ugesi",
    "ngicela usizo",
    "siza",
    # isiXhosa
    "namhlanje",
    "ngokukhawuleza",
    "iqhushumbe",
    "qhushumb",
    "akukho mbane",
    "nceda",
    "ndincede",
]
LOW_URGENCY_FORMS = [
    "no rush",
    "not urgent",
    "when you can",
    "next week",
    "next month",
    "sometime",
    "akuphuthumi",
    "noma nini",
    "ngesonto elizayo",
    "akungxamisekanga",
    "nanini",
    "kwiveki ezayo",
]
LARGE_JOB_FORMS = [
    "install",
    "installation",
    "replace the geyser",
    "new geyser",
    "rewire",
    "whole house",
    "entire house",
    "renovat",
    "all the rooms",
    "build",
    "faka igiza",
    "igiza elisha",
    "yonke indlu",
    "igiza elitsha",
]
SMALL_JOB_FORMS = [
    "tap",
    "drip",
    "plug",
    "switch",
    "bulb",
    "socket",
    "blocked",
    "small",
    "mpompi",
    "plagi",
    "valilekile",
    "vinjiwe",
    "ncane",
    "mpompo",
    "valekile",
    "ncinci",
]


def load_trade_forms() -> dict[str, list[tuple[str, str, bool]]]:
    """Map each trade to its forms as (term, form, is_whole_word), read from the glossary."""
    try:
        glossary = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {FALLBACK_TRADE: [("geyser", "geyser", True), ("pipe", "pipe", True)]}
    trade_forms: dict[str, list[tuple[str, str, bool]]] = {
        trade["id"]: [] for trade in glossary.get("trades", [])
    }
    for term in glossary.get("terms", []):
        term_name = term["en"].lower()
        forms = trade_forms.setdefault(term["trade"], [])
        forms.append((term_name, term_name, True))
        for lang_code in ("zu", "xh"):
            forms.extend((term_name, form.lower(), False) for form in term.get(lang_code, []))
    return trade_forms


TRADE_FORMS = load_trade_forms()


def contains_form(text: str, form: str, is_whole_word: bool) -> bool:
    """True when the form appears in the text: as a whole word (plural allowed), or anywhere."""
    if is_whole_word:
        return re.search(rf"\b{re.escape(form)}(?:s|es|ing)?\b", text) is not None
    return form in text


def count_trade_matches(text: str) -> dict[str, int]:
    """How many different glossary terms for each trade appear in the text. "Igiza" matches both
    "igiza" and "giza", but they're one term (geyser), so it counts once."""
    return {
        trade: len({term for term, form, whole in forms if contains_form(text, form, whole)})
        for trade, forms in TRADE_FORMS.items()
    }


def contains_any(text: str, forms: list[str]) -> bool:
    return any(form in text for form in forms)


def guess_urgency(text: str) -> Urgency:
    if contains_any(text, LOW_URGENCY_FORMS):
        return "low"
    if contains_any(text, URGENT_FORMS):
        return "urgent"
    return "normal"


def guess_size(text: str) -> JobSize:
    if contains_any(text, LARGE_JOB_FORMS):
        return "large"
    if contains_any(text, SMALL_JOB_FORMS):
        return "small"
    return "medium"


def get_confidence(best_match_count: int, is_tied: bool) -> float:
    if best_match_count == 0:
        return NO_MATCH_CONFIDENCE
    if is_tied:
        return TIED_TRADES_CONFIDENCE
    if best_match_count == 1:
        return ONE_MATCH_CONFIDENCE
    if best_match_count == 2:
        return TWO_MATCHES_CONFIDENCE
    return MANY_MATCHES_CONFIDENCE


def understand_job(text: str, lang: Lang) -> JobIntent:
    """Turn a customer's description into trade, urgency and size, with a confidence from 0 to 1.

    lang is the customer's language; words from every language are checked, since people mix
    them ("I-geyser yami iyavuza").
    """
    lowered_text = text.lower()
    match_counts = count_trade_matches(lowered_text)
    best_count = max(match_counts.values(), default=0)
    best_trades = [trade for trade, count in match_counts.items() if count == best_count]
    trade = best_trades[0] if best_count > 0 else FALLBACK_TRADE
    return JobIntent(
        trade=trade,
        urgency=guess_urgency(lowered_text),
        size=guess_size(lowered_text),
        confidence=get_confidence(best_count, is_tied=best_count > 0 and len(best_trades) > 1),
        prohibited=find_prohibited(text),
    )
