"""translate() keeps values exact, flags doubts, and never breaks chat when a backend fails."""

from lang.backends import BackendTranslation, FakeBackend, TranslationFailedError, get_backend
from lang.translation import FLAG_REASON_UNAVAILABLE, FLAG_REASON_VALUES_LOST, translate


class ScriptedBackend:
    """Returns a fixed translation, and remembers the text it was sent."""

    def __init__(self, reply: str, detected_lang: str = "zu"):
        self.reply = reply
        self.detected_lang = detected_lang
        self.sent_text = ""

    def translate(self, text, target_lang, source_lang):
        self.sent_text = text
        return BackendTranslation(text=self.reply, source_lang=source_lang or self.detected_lang)


class BrokenBackend:
    def translate(self, text, target_lang, source_lang):
        raise TranslationFailedError("backend down")


def test_backend_never_sees_the_price_or_time():
    backend = ScriptedBackend("I can come on Tuesday at [[1]], [[0]].")
    translate("Ngingafika ngoLwesibili, R450, ngo 10:00", "en", "zu", backend=backend)
    assert "R450" not in backend.sent_text
    assert "10:00" not in backend.sent_text


def test_values_come_back_exactly():
    backend = ScriptedBackend("I can come on Tuesday, [[0]].")
    translation = translate("Ngingafika ngoLwesibili, R450.", "en", "zu", backend=backend)
    assert translation.text == "I can come on Tuesday, R450."
    assert translation.original == "Ngingafika ngoLwesibili, R450."
    assert translation.source_lang == "zu"
    assert translation.flagged is False


def test_a_dropped_value_flags_the_message():
    backend = ScriptedBackend("I can come on Tuesday.")
    translation = translate("Ngingafika ngoLwesibili, R450.", "en", "zu", backend=backend)
    assert translation.flagged is True
    assert translation.flag_reason == FLAG_REASON_VALUES_LOST


def test_a_failed_backend_shows_the_original_flagged():
    translation = translate("Ngingafika ngoLwesibili", "en", "zu", backend=BrokenBackend())
    assert translation.text == "Ngingafika ngoLwesibili"
    assert translation.flagged is True
    assert translation.flag_reason == FLAG_REASON_UNAVAILABLE


def test_same_language_is_not_sent_to_a_backend():
    backend = ScriptedBackend("should not be used")
    translation = translate("Hello", "en", "en", backend=backend)
    assert translation.text == "Hello"
    assert backend.sent_text == ""


def test_detected_language_is_reported_when_source_is_unknown():
    backend = ScriptedBackend("My geyser is leaking", detected_lang="zu")
    assert translate("Igiza lami liyavuza", "en", backend=backend).source_lang == "zu"


def test_fake_backend_is_the_default(monkeypatch):
    monkeypatch.delenv("TRANSLATION_BACKEND", raising=False)
    assert isinstance(get_backend(), FakeBackend)
    assert translate("Sawubona, R450", "en", "zu").text == "[en] Sawubona, R450"
