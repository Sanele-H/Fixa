"""Language and safety for Fixa (P3).

Owner: P3. Only P3 edits files in packages/lang/. P2's API imports this package.

Public functions (the contract; signatures change only with the team's agreement):
    translate(text, target_lang, source_lang=None)
        -> Translation(text, original, source_lang, flagged, flag_reason)
    understand_job(text, lang) -> JobIntent(trade, urgency, size, confidence)
    scan_message(text, lang, contacts_unlocked) -> SafetyResult(safe_text, findings, scam_warnings)
    extract_quote(text) -> Quote(amount_rands, when) | None
    get_scam_warning_texts(scam_warnings, lang) -> list[str], in the reader's language

Proposed (not agreed yet):
    transcribe(audio, mime_type, lang=None) -> Transcript(text, lang, confidence)

Data P3 owns: data/glossary.json, data/test_messages.json, data/number_words.json.

Step 0 (Day 1): stubs with the correct return types, so the API can import them (lang/stubs.py).
Real so far: translate (lang/translation.py), with backends picked by TRANSLATION_BACKEND, and
scan_message (lang/safety.py) understand_job (lang/understanding.py) and
extract_quote (lang/quotes.py). Only transcribe is still a stub.
"""

from lang.models import (
    Finding,
    JobIntent,
    Quote,
    SafetyResult,
    Transcript,
    Translation,
)
from lang.quotes import extract_quote
from lang.safety import get_scam_warning_texts, scan_message
from lang.stubs import transcribe
from lang.translation import translate
from lang.understanding import understand_job

__all__ = [
    "Finding",
    "JobIntent",
    "Quote",
    "SafetyResult",
    "Transcript",
    "Translation",
    "extract_quote",
    "get_scam_warning_texts",
    "scan_message",
    "transcribe",
    "translate",
    "understand_job",
]
