"""translate() keeps values exact, flags doubts, and never breaks chat when a backend fails."""

from collections import OrderedDict
from types import SimpleNamespace

import pytest

from lang.backends import (
    CLAUDE_MAX_RETRIES,
    AzureBackend,
    BackendTranslation,
    ClaudeBackend,
    FakeBackend,
    TranslationFailedError,
    get_backend,
    to_plain_text,
    to_protected_html,
)
from lang.quality import (
    FLAG_REASON_AMOUNT_CHANGED,
    FLAG_REASON_NOT_TRANSLATED,
    FLAG_REASON_UNAVAILABLE,
)
from lang.safety import HIDDEN_CONTACT_TEXT
from lang.translation import translate


@pytest.fixture(autouse=True)
def empty_caches(monkeypatch):
    """Each test starts with no cached translations or backends."""
    monkeypatch.setattr("lang.translation._translation_cache", OrderedDict())
    monkeypatch.setattr("lang.backends._backend_cache", {})


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
    assert translation.flag_reason == FLAG_REASON_AMOUNT_CHANGED


def test_a_failed_backend_shows_the_original_flagged():
    translation = translate("Ngingafika ngoLwesibili", "en", "zu", backend=BrokenBackend())
    assert translation.text == "Ngingafika ngoLwesibili"
    assert translation.flagged is True
    assert translation.flag_reason == FLAG_REASON_UNAVAILABLE


@pytest.mark.parametrize(
    "error",
    [
        TypeError("an empty ANTHROPIC_API_KEY"),
        IndexError("an Azure reply with no translations"),
        ModuleNotFoundError("a library that isn't installed"),
    ],
)
def test_any_backend_error_shows_the_original_flagged(error):
    class RaisingBackend:
        def translate(self, text, target_lang, source_lang):
            raise error

    translation = translate("Ngingafika ngoLwesibili", "en", "zu", backend=RaisingBackend())
    assert translation.text == "Ngingafika ngoLwesibili"
    assert translation.flag_reason == FLAG_REASON_UNAVAILABLE


def test_a_backend_that_cannot_be_created_shows_the_original_flagged(monkeypatch):
    def fail_to_create_backend():
        raise RuntimeError("no credentials")

    monkeypatch.setattr("lang.translation.get_backend", fail_to_create_backend)
    translation = translate("Ngingafika ngoLwesibili", "en", "zu")
    assert translation.flag_reason == FLAG_REASON_UNAVAILABLE


@pytest.mark.parametrize(
    "reply",
    [
        "It costs [[0]] and [[3]].",  # [[3]] was made up: there is only one value
        "It costs [[0]], yes [[0]].",  # the same value twice
    ],
)
def test_a_made_up_or_repeated_value_flags_the_message(reply):
    translation = translate("Kubiza R450.", "en", "zu", backend=ScriptedBackend(reply))
    assert translation.flag_reason == FLAG_REASON_AMOUNT_CHANGED


def test_a_blank_message_keeps_the_senders_language():
    assert translate("   ", "en", "zu").source_lang == "zu"


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


class FakeAzureResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


def test_azure_backend_reads_translation_and_detected_language(monkeypatch):
    monkeypatch.setenv("AZURE_TRANSLATOR_KEY", "test-key")
    monkeypatch.setenv("AZURE_TRANSLATOR_REGION", "southafricanorth")
    sent = {}

    def fake_post(url, params, headers, json, timeout):
        sent.update(url=url, params=params, headers=headers, body=json)
        return FakeAzureResponse(
            [
                {
                    "detectedLanguage": {"language": "zu", "score": 1.0},
                    "translations": [
                        {
                            "text": "I can come on Tuesday, "
                            '<span class="notranslate">[[0]]</span>.',
                            "to": "en",
                        }
                    ],
                }
            ]
        )

    monkeypatch.setattr("lang.backends.httpx.post", fake_post)
    translation = translate("Ngingafika ngoLwesibili, R450.", "en", backend=AzureBackend())
    assert translation.text == "I can come on Tuesday, R450."
    assert translation.source_lang == "zu"
    assert sent["params"] == {"api-version": "3.0", "to": "en", "textType": "html"}
    assert sent["headers"]["Ocp-Apim-Subscription-Region"] == "southafricanorth"
    assert sent["body"] == [
        {"Text": 'Ngingafika ngoLwesibili, <span class="notranslate">[[0]]</span>.'}
    ]


def test_azure_html_escapes_the_message_so_a_less_than_sign_is_safe():
    assert to_protected_html("a < b [[0]]") == 'a &lt; b <span class="notranslate">[[0]]</span>'
    assert to_plain_text('a &lt; b <span class="notranslate">R450</span>') == "a < b R450"


def test_text_handed_back_unchanged_is_flagged_not_translated():
    backend = ScriptedBackend("Ke tla tla ka Labobedi")
    translation = translate("Ke tla tla ka Labobedi", "en", "zu", backend=backend)
    assert translation.flag_reason == FLAG_REASON_NOT_TRANSLATED


def test_stray_space_after_an_isizulu_hyphen_is_closed():
    backend = ScriptedBackend("Ngizofika ngo- [[0]], kuzobiza u- [[1]].")
    translation = translate("I'll come at 9am, it costs R650.", "zu", "en", backend=backend)
    assert translation.text == "Ngizofika ngo-9 ekuseni, kuzobiza u-R650."


def test_good_translations_are_cached_and_reused(monkeypatch):
    calls = []

    class CountingBackend(ScriptedBackend):
        def translate(self, text, target_lang, source_lang):
            calls.append(text)
            return super().translate(text, target_lang, source_lang)

    counting_backend = CountingBackend("I can come on Tuesday, [[0]].")
    monkeypatch.setattr("lang.translation.get_backend", lambda: counting_backend)
    first = translate("Ngizofika ngoLwesibili, R450.", "en", "zu")
    second = translate("Ngizofika ngoLwesibili, R450.", "en", "zu")
    assert first == second
    assert len(calls) == 1


def test_spaces_azure_dropped_around_values_are_put_back_in_english():
    backend = ScriptedBackend(
        "It takes[[0]] to get there, and I'll be there in[[1]]minutes. On[[2]] ?"
    )
    translation = translate(
        "Kubiza u-R350, ngizobe ngilapho emizuzwini engu-20. Ngo 3 Oct?",
        "en",
        "zu",
        backend=backend,
    )
    assert (
        translation.text == "It takes R350 to get there, and I'll be there in 20 minutes. On 3 Oct?"
    )


def test_a_space_azure_dropped_after_a_comma_is_put_back_in_every_language():
    english = translate(
        "Ngingafika ngoLwesibili ngo-10:30, R450.",
        "en",
        "zu",
        backend=ScriptedBackend("I can come on Tuesday,[[0]],[[1]]."),
    )
    isizulu = translate(
        "I can come on Tuesday, 10:30.",
        "zu",
        "en",
        backend=ScriptedBackend("Ngingafika ngoLwesibili,[[0]]."),
    )
    assert english.text == "I can come on Tuesday, 10:30, R450."
    assert isizulu.text == "Ngingafika ngoLwesibili, 10:30."


def test_the_backend_never_sees_the_hidden_contact_marker():
    backend = ScriptedBackend("Ngishayele ucingo [[0]]")
    translate(f"Call me {HIDDEN_CONTACT_TEXT}", "zu", "en", backend=backend)
    assert backend.sent_text == "Call me [[0]]"


@pytest.mark.parametrize(
    ("target_lang", "expected_marker"),
    [
        ("zu", "[imininingwane yokuxhumana ifihliwe kuze kuqinisekiswe umsebenzi]"),
        ("en", HIDDEN_CONTACT_TEXT),
        # No isiXhosa wording from a first-language speaker yet, so it stays English
        ("xh", HIDDEN_CONTACT_TEXT),
    ],
)
def test_the_hidden_contact_marker_comes_back_in_the_readers_language(
    target_lang, expected_marker
):
    source_lang = "zu" if target_lang == "en" else "en"
    translation = translate(
        f"Call me {HIDDEN_CONTACT_TEXT} after 5",
        target_lang,
        source_lang,
        backend=ScriptedBackend("Translated [[0]] after [[1]]"),
    )
    assert translation.text == f"Translated {expected_marker} after 5"
    assert not translation.flagged


def test_isizulu_attached_values_keep_their_hyphen():
    backend = ScriptedBackend("Ungafika kusasa ngo-[[0]]?")
    translation = translate("Can you come tomorrow at 10:00?", "zu", "en", backend=backend)
    assert translation.text == "Ungafika kusasa ngo-10:00?"


@pytest.mark.parametrize(
    ("english_time", "target_lang", "expected_time"),
    [
        ("9am", "zu", "9 ekuseni"),
        ("2pm", "zu", "2 ntambama"),
        ("7pm", "zu", "7 kusihlwa"),
        ("11pm", "zu", "11 ebusuku"),
        ("12pm", "zu", "12 ntambama"),
        ("8am", "xh", "8 ntseni"),
        ("3:30pm", "xh", "3:30 njakalanga"),
        ("6 pm", "xh", "6 ngokuhlwa"),
        ("2am", "xh", "2 busuku"),
    ],
)
def test_am_pm_becomes_the_local_time_of_day_word(english_time, target_lang, expected_time):
    backend = ScriptedBackend("Ngizofika ngo- [[0]].")
    translation = translate(f"I'll come at {english_time}.", target_lang, "en", backend=backend)
    assert translation.text == f"Ngizofika ngo-{expected_time}."


@pytest.mark.parametrize(
    ("local_time", "source_lang", "target_lang", "expected_time"),
    [
        ("9 ekuseni", "zu", "en", "9am"),
        ("2 ntambama", "zu", "en", "2pm"),
        ("7 kusihlwa", "zu", "en", "7pm"),
        ("10:30 ekuseni", "zu", "en", "10:30am"),
        ("10h30 ekuseni", "zu", "en", "10:30am"),
        ("8 ebusuku", "zu", "en", "8pm"),
        ("2 ebusuku", "zu", "en", "2am"),
        ("12 ebusuku", "zu", "en", "12am"),
        ("12:00 ntambama", "zu", "en", "12:00pm"),
        ("14h00 ntambama", "zu", "en", "14:00"),
        ("20:00 ebusuku", "zu", "en", "20:00"),
        ("00:30 ebusuku", "zu", "en", "00:30"),
        ("14 ntambama", "zu", "en", "14:00"),
        ("9 ntseni", "xh", "en", "9am"),
        ("9 ekuseni", "zu", "xh", "9 ntseni"),
        ("7 ngokuhlwa", "xh", "zu", "7 kusihlwa"),
    ],
)
def test_a_local_time_of_day_is_said_the_readers_way(
    local_time, source_lang, target_lang, expected_time
):
    backend = ScriptedBackend("I'll come on Saturday at [[0]], it costs [[1]].")
    translation = translate(
        f"Ngizofika ngoMgqibelo ngo-{local_time}, kuzobiza R450.",
        target_lang,
        source_lang,
        backend=backend,
    )
    assert "ekuseni" not in backend.sent_text and "[[0]]" in backend.sent_text
    assert translation.text == f"I'll come on Saturday at {expected_time}, it costs R450."


def test_am_pm_stays_as_written_in_english():
    backend = ScriptedBackend("I'll come at [[0]].")
    assert translate("Ngizofika ngo 9am.", "en", "zu", backend=backend).text == "I'll come at 9am."


def test_a_missing_azure_key_shows_the_original_instead_of_crashing(monkeypatch):
    monkeypatch.setenv("TRANSLATION_BACKEND", "azure")
    monkeypatch.delenv("AZURE_TRANSLATOR_KEY", raising=False)
    monkeypatch.setattr("lang.backends._backend_cache", {})
    translation = translate("Ngingafika ngoLwesibili, R450.", "en", "zu")
    assert translation.text == "Ngingafika ngoLwesibili, R450."
    assert translation.flag_reason == FLAG_REASON_UNAVAILABLE


def make_claude_backend(monkeypatch, reply, stop_reason="end_turn"):
    """A ClaudeBackend whose Anthropic client returns reply, with no network. Also returns the
    options the client was created with."""
    client_options = {}
    response = SimpleNamespace(
        stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=reply)]
    )

    def create_fake_client(**options):
        client_options.update(options)
        messages = SimpleNamespace(create=lambda **_: response)
        return SimpleNamespace(beta=SimpleNamespace(messages=messages))

    monkeypatch.setattr("lang.backends.anthropic.Anthropic", create_fake_client)
    return ClaudeBackend(), client_options


def test_claude_reads_the_language_code_line_then_the_translation(monkeypatch):
    backend, client_options = make_claude_backend(monkeypatch, "zu\nMy geyser is leaking")
    result = backend.translate("Igiza lami liyavuza", "en", None)
    assert (result.text, result.source_lang) == ("My geyser is leaking", "zu")
    assert client_options["max_retries"] == CLAUDE_MAX_RETRIES


@pytest.mark.parametrize(
    ("reply", "stop_reason"),
    [
        ("My geyser is leaking", "end_turn"),  # no language code line
        ("zu", "end_turn"),  # a code but no translation
        ("zu\nMy geyser is", "max_tokens"),  # cut off
    ],
)
def test_a_claude_reply_that_is_cut_off_or_unlabelled_fails(monkeypatch, reply, stop_reason):
    backend, _ = make_claude_backend(monkeypatch, reply, stop_reason)
    with pytest.raises(TranslationFailedError):
        backend.translate("Igiza lami liyavuza", "en", None)
