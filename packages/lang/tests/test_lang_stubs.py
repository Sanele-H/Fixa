"""The stubs return the agreed types, so the API can import and call them. Replace with real
tests as each function gets real code."""

from lang import (
    JobIntent,
    Quote,
    SafetyResult,
    Transcript,
    Translation,
    extract_quote,
    scan_message,
    transcribe,
    translate,
    understand_job,
)
from lang.backends import FakeBackend


def test_translate_keeps_the_original():
    # The fake backend, whatever TRANSLATION_BACKEND says, so this test never makes a paid call
    translation = translate(
        "Ngingafika ngoLwesibili, R450.", target_lang="en", source_lang="zu", backend=FakeBackend()
    )
    assert isinstance(translation, Translation)
    assert translation.original == "Ngingafika ngoLwesibili, R450."
    assert translation.source_lang == "zu"


def test_understand_job_returns_an_intent():
    assert isinstance(understand_job("igiza lami liyavuza", lang="zu"), JobIntent)


def test_scan_message_returns_a_safety_result():
    assert isinstance(scan_message("Hello", lang="en", contacts_unlocked=False), SafetyResult)


def test_extract_quote_returns_a_quote_or_none():
    quote = extract_quote("I can do it for R450 on Tuesday")
    assert quote is None or isinstance(quote, Quote)


def test_transcribe_returns_a_transcript():
    assert isinstance(transcribe(b"fake audio", mime_type="audio/webm"), Transcript)
