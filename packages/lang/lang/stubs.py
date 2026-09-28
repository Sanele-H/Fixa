"""Step 0 stubs: fake answers in the right shape, so P1 and P2 can build before real code exists.

Each function is replaced by real code behind the same signature. The fake values match the
fixtures in contracts/fixtures/, so the API and the app see the same data either way.
"""

from lang.models import Lang, Quote, Transcript

FAKE_TRANSCRIPT_TEXT = "Ngingafika ngoLwesibili, R450."
FAKE_TRANSCRIPT_CONFIDENCE = 0.9


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
