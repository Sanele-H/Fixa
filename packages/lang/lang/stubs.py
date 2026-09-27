"""Step 0 stubs: fake answers in the right shape, so P1 and P2 can build before real code exists.

Each function is replaced by real code behind the same signature. The fake values match the
fixtures in contracts/fixtures/, so the API and the app see the same data either way.
"""

from lang.models import JobIntent, Lang, Quote, SafetyResult, Transcript

FAKE_TRANSCRIPT_TEXT = "Ngingafika ngoLwesibili, R450."
FAKE_TRANSCRIPT_CONFIDENCE = 0.9


def understand_job(text: str, lang: Lang) -> JobIntent:
    """Turn a customer's description into trade, urgency and size, with the glossary as fallback.

    Stub: always a small urgent plumbing job, as in job_intent.json.
    """
    return JobIntent(trade="plumbing", urgency="urgent", size="small", confidence=0.82)


def scan_message(text: str, lang: Lang, contacts_unlocked: bool) -> SafetyResult:
    """Hide phones, emails and links (including "o82 one two three…") and warn about scams.

    Contact details stay hidden until contacts_unlocked is True (the job is confirmed).
    Stub: returns the text unchanged with nothing found.
    """
    return SafetyResult(safe_text=text, findings=[], scam_warnings=[])


def extract_quote(text: str) -> Quote | None:
    """Pull a rand amount and a time out of a chat message, or None if there is no price.

    Stub: always R450 on Tuesday 10:00, as in quote.json.
    """
    return Quote(amount_rands=450, when="Tuesday 10:00")


def transcribe(audio: bytes, mime_type: str, lang: Lang | None = None) -> Transcript:
    """Turn a voice note into text. PROPOSAL: not in contracts/api.md until the team agrees.

    mime_type is what the browser recorded, for example "audio/webm" or "audio/mp4".
    The audio is never stored or forwarded: only the text goes on, through scan_message.
    Stub: always returns the demo's isiZulu sentence.
    """
    return Transcript(text=FAKE_TRANSCRIPT_TEXT, lang="zu", confidence=FAKE_TRANSCRIPT_CONFIDENCE)
