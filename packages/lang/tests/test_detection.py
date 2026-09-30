"""detect_language(): the language a message is really in, whatever the sender's setting says."""

import json
from pathlib import Path

import pytest

from lang import detect_language
from lang.backends import AzureBackend, BackendDetection, FakeBackend
from lang.detection import detect_by_markers
from lang.safety import HIDDEN_CONTACT_TEXT

TEST_MESSAGES_PATH = Path(__file__).resolve().parents[3] / "data" / "test_messages.json"
# No marker words, so only a detector can tell what language this is.
UNMARKED_ZULU = "Impompi yasekhishini ayiyeki ukuvuza."


class ScriptedDetector:
    """Answers every detect() with the same guess, and remembers what it was asked."""

    def __init__(self, detection: BackendDetection | None = None, error: Exception | None = None):
        self.detection = detection
        self.error = error
        self.sent_texts: list[str] = []

    def detect(self, text: str) -> BackendDetection | None:
        self.sent_texts.append(text)
        if self.error:
            raise self.error
        return self.detection


@pytest.fixture
def use_detector(monkeypatch):
    """use_detector(ScriptedDetector(...)) makes detect_language() ask that detector."""

    def install(detector: ScriptedDetector) -> ScriptedDetector:
        monkeypatch.setattr("lang.detection.get_backend", lambda: detector)
        return detector

    return install


def test_markers_find_isizulu_even_when_the_sender_is_set_to_english(use_detector):
    detector = use_detector(ScriptedDetector(BackendDetection(code="en", score=1.0)))

    assert detect_language("Ngizofika kusasa", "en") == "zu"
    assert detector.sent_texts == []  # the markers were enough


def test_markers_find_isixhosa():
    assert detect_language("Ndiza kufika ngomso", "en") == "xh"
    assert detect_language("Enkosi", "zu") == "xh"


def test_markers_never_pick_the_wrong_language_in_the_team_test_messages():
    messages = json.loads(TEST_MESSAGES_PATH.read_text(encoding="utf-8"))["messages"]
    nguni_messages = [message for message in messages if message["lang"] in ("zu", "xh")]

    wrong = [
        message["id"]
        for message in nguni_messages
        if detect_by_markers(message["text"]) not in (None, message["lang"])
    ]

    assert nguni_messages
    assert wrong == []


def test_short_text_keeps_the_sender_setting(use_detector):
    detector = use_detector(ScriptedDetector(BackendDetection(code="en", score=1.0)))

    assert detect_language("ok", "zu") == "zu"
    assert detect_language("R450", "xh") == "xh"
    assert detector.sent_texts == []


def test_confident_english_from_the_detector_wins(use_detector):
    use_detector(ScriptedDetector(BackendDetection(code="en", score=0.99)))

    assert detect_language("See you on Tuesday morning", "zu") == "en"


def test_unsure_english_keeps_the_sender_setting(use_detector):
    use_detector(ScriptedDetector(BackendDetection(code="en", score=0.6)))

    assert detect_language(UNMARKED_ZULU, "zu") == "zu"


def test_an_isizulu_setting_beats_the_detector_calling_it_isixhosa(use_detector):
    use_detector(ScriptedDetector(BackendDetection(code="xh", score=0.99)))

    assert detect_language(UNMARKED_ZULU, "zu") == "zu"


def test_the_detector_guess_is_used_when_the_sender_is_set_to_english(use_detector):
    use_detector(ScriptedDetector(BackendDetection(code="zu", score=0.9)))

    assert detect_language(UNMARKED_ZULU, "en") == "zu"


def test_a_language_we_do_not_support_keeps_the_sender_setting(use_detector):
    use_detector(ScriptedDetector(BackendDetection(code="rw", score=0.4)))

    assert detect_language(UNMARKED_ZULU, "en") == "en"


def test_a_detector_failure_keeps_the_sender_setting(use_detector):
    use_detector(ScriptedDetector(error=RuntimeError("network down")))

    assert detect_language(UNMARKED_ZULU, "xh") == "xh"


def test_values_and_hidden_contacts_never_reach_the_detector(use_detector):
    detector = use_detector(ScriptedDetector(BackendDetection(code="zu", score=0.9)))

    detect_language(f"Impompi iyavuza, kubiza R450 {HIDDEN_CONTACT_TEXT}", "en")

    assert "R450" not in detector.sent_texts[0]
    assert HIDDEN_CONTACT_TEXT not in detector.sent_texts[0]


def test_the_fake_backend_cannot_detect():
    assert FakeBackend().detect(UNMARKED_ZULU) is None


class FakeAzureResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


def test_azure_backend_reads_the_detected_language(monkeypatch):
    monkeypatch.setenv("AZURE_TRANSLATOR_KEY", "test-key")
    monkeypatch.setenv("AZURE_TRANSLATOR_REGION", "southafricanorth")
    sent = {}

    def fake_post(url, params, headers, json, timeout):
        sent.update(url=url, body=json)
        return FakeAzureResponse([{"language": "zu", "score": 0.9, "isTranslationSupported": True}])

    monkeypatch.setattr("lang.backends.httpx.post", fake_post)

    detection = AzureBackend().detect(UNMARKED_ZULU)

    assert detection == BackendDetection(code="zu", score=0.9)
    assert sent["url"].endswith("/detect")
    assert sent["body"] == [{"Text": UNMARKED_ZULU}]
