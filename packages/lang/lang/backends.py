"""Translation backends. Each one takes already-protected text (values swapped for [[0]], [[1]]…)
and returns the translation. Pick one with TRANSLATION_BACKEND in .env: fake, claude or google.

The fake backend needs no keys, so everyone can build and test without them.
"""

import os
from typing import Protocol

import anthropic
from pydantic import BaseModel

from lang.models import Lang

LANGUAGE_NAMES: dict[str, str] = {"en": "English", "zu": "isiZulu", "xh": "isiXhosa"}
DEFAULT_BACKEND_NAME = "fake"

CLAUDE_DEFAULT_MODEL = "claude-opus-5"
CLAUDE_MAX_TOKENS = 2000
CLAUDE_TIMEOUT_SECONDS = 15.0
CLAUDE_FALLBACK_BETA = "server-side-fallback-2026-07-01"
CLAUDE_SYSTEM_PROMPT = """You translate short marketplace chat messages between English, \
isiZulu and isiXhosa for a South African app where customers hire tradespeople (plumbers, \
electricians and so on).

Rules:
- Keep every placeholder such as [[0]] or [[1]] exactly as written. They stand for prices, times, \
dates, phone numbers and addresses. Never translate, remove or renumber them.
- People often mix English into isiZulu or isiXhosa. Translate the meaning naturally, the way a \
local person would say it.
- Keep trade words accurate (geyser, pipe, wiring, tap). If a trade word has no common local \
word, keep the English word.
- Output only what is asked for. No notes, quotes or explanations."""

GOOGLE_LOCATION = "global"


class BackendTranslation(BaseModel):
    """What a backend returns: the translated text and the language it detected or was given."""

    text: str
    source_lang: Lang


class TranslationBackend(Protocol):
    """Every backend has this one method."""

    def translate(
        self, text: str, target_lang: Lang, source_lang: Lang | None
    ) -> BackendTranslation: ...


def to_supported_lang(code: str | None) -> Lang:
    """Turn a backend's language code ("zu", "zu-ZA", "xh") into one of ours, defaulting to en."""
    short_code = (code or "").split("-")[0].strip().lower()
    return short_code if short_code in LANGUAGE_NAMES else "en"  # type: ignore[return-value]


class FakeBackend:
    """No network, no keys: tags the text with the target language, like "[en] …"."""

    def translate(
        self, text: str, target_lang: Lang, source_lang: Lang | None
    ) -> BackendTranslation:
        return BackendTranslation(text=f"[{target_lang}] {text}", source_lang=source_lang or "en")


class ClaudeBackend:
    """Claude through the Anthropic API. Needs ANTHROPIC_API_KEY.

    CLAUDE_TRANSLATION_MODEL overrides the model. Effort is low because chat needs replies in
    about 2 seconds. If the request is declined, fallbacks="default" retries it on Anthropic's
    recommended fallback model.
    """

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(timeout=CLAUDE_TIMEOUT_SECONDS)
        self.model = os.getenv("CLAUDE_TRANSLATION_MODEL", CLAUDE_DEFAULT_MODEL)

    def translate(
        self, text: str, target_lang: Lang, source_lang: Lang | None
    ) -> BackendTranslation:
        target_name = LANGUAGE_NAMES[target_lang]
        if source_lang:
            instruction = (
                f"Translate this {LANGUAGE_NAMES[source_lang]} message into {target_name}:"
            )
        else:
            instruction = (
                "On the first line, write only the language code of this message: en, zu or xh. "
                f"On the next line, write its translation into {target_name}:"
            )
        response = self.client.beta.messages.create(
            model=self.model,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=CLAUDE_SYSTEM_PROMPT,
            output_config={"effort": "low"},
            betas=[CLAUDE_FALLBACK_BETA],
            fallbacks="default",
            messages=[{"role": "user", "content": f"{instruction}\n\n{text}"}],
        )
        if response.stop_reason == "refusal":
            raise TranslationFailedError("Claude declined to translate this message")
        reply = "".join(block.text for block in response.content if block.type == "text").strip()
        if source_lang:
            return BackendTranslation(text=reply, source_lang=source_lang)
        detected_code, _, translated_text = reply.partition("\n")
        return BackendTranslation(
            text=translated_text.strip(), source_lang=to_supported_lang(detected_code)
        )


class GoogleBackend:
    """Google Cloud Translation v3. Needs GOOGLE_CLOUD_PROJECT, and
    GOOGLE_APPLICATION_CREDENTIALS pointing at a service-account JSON file outside the repo.

    Install its library first: pip install -e "packages/lang[google]"
    """

    def __init__(self) -> None:
        from google.cloud import translate_v3  # Imported here so the package works without it

        self.client = translate_v3.TranslationServiceClient()
        project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
        self.parent = f"projects/{project_id}/locations/{GOOGLE_LOCATION}"

    def translate(
        self, text: str, target_lang: Lang, source_lang: Lang | None
    ) -> BackendTranslation:
        response = self.client.translate_text(
            parent=self.parent,
            contents=[text],
            mime_type="text/plain",
            source_language_code=source_lang or None,
            target_language_code=target_lang,
        )
        translation = response.translations[0]
        detected_lang = source_lang or to_supported_lang(translation.detected_language_code)
        return BackendTranslation(text=translation.translated_text, source_lang=detected_lang)


class TranslationFailedError(Exception):
    """A backend could not translate the message."""


BACKEND_CLASSES: dict[str, type] = {
    "fake": FakeBackend,
    "claude": ClaudeBackend,
    "google": GoogleBackend,
}
_backend_cache: dict[str, TranslationBackend] = {}


def get_backend(name: str | None = None) -> TranslationBackend:
    """Return the backend named here or in TRANSLATION_BACKEND, created once and reused."""
    backend_name = (name or os.getenv("TRANSLATION_BACKEND") or DEFAULT_BACKEND_NAME).lower()
    if backend_name not in BACKEND_CLASSES:
        raise ValueError(
            f"Unknown translation backend {backend_name!r}: use fake, claude or google"
        )
    if backend_name not in _backend_cache:
        _backend_cache[backend_name] = BACKEND_CLASSES[backend_name]()
    return _backend_cache[backend_name]
