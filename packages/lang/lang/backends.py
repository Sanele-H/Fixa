"""Translation backends. Each one takes already-protected text (values swapped for [[0]], [[1]]…)
and returns the translation. Pick one with TRANSLATION_BACKEND in .env: fake, azure or claude.

The fake backend needs no keys, so everyone can build and test without them.
"""

import html
import os
import re
from typing import Protocol

import anthropic
import httpx
from pydantic import BaseModel

from lang.models import Lang

LANGUAGE_NAMES: dict[str, str] = {"en": "English", "zu": "isiZulu", "xh": "isiXhosa"}
DEFAULT_BACKEND_NAME = "fake"

CLAUDE_DEFAULT_MODEL = "claude-opus-5"
CLAUDE_MAX_TOKENS = 2000
CLAUDE_TIMEOUT_SECONDS = 15.0
# The SDK retries twice by default, which could hold a chat message for 45 s or more.
CLAUDE_MAX_RETRIES = 1
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

AZURE_DEFAULT_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
AZURE_API_VERSION = "3.0"
AZURE_TIMEOUT_SECONDS = 10.0
# Azure leaves anything inside this span untranslated (textType=html), so placeholders get double
# protection: Azure won't touch them, and restore() still checks every value came back.
AZURE_NOTRANSLATE_SPAN = '<span class="notranslate">{}</span>'
AZURE_SPAN_TAG_PATTERN = re.compile(r"</?span[^>]*>")
PLACEHOLDER_IN_TEXT_PATTERN = re.compile(r"\[\[\d+\]\]")


class BackendTranslation(BaseModel):
    """What a backend returns: the translated text and the language it detected or was given."""

    text: str
    source_lang: Lang


class TranslationBackend(Protocol):
    """Every backend has this one method."""

    def translate(
        self, text: str, target_lang: Lang, source_lang: Lang | None
    ) -> BackendTranslation: ...


def get_short_code(code: str | None) -> str:
    """The bare code in "zu", "zu-ZA" or "xh.": lowercase, with no region or punctuation."""
    return (code or "").strip().rstrip(".:").split("-")[0].lower()


def to_supported_lang(code: str | None) -> Lang:
    """Turn a backend's language code ("zu", "zu-ZA", "xh") into one of ours, defaulting to en."""
    short_code = get_short_code(code)
    return short_code if short_code in LANGUAGE_NAMES else "en"  # type: ignore[return-value]


def is_language_code(text: str) -> bool:
    """True when text is just one of our language codes, as Claude is asked to write on the first
    line of its reply when the sender's language is unknown."""
    return get_short_code(text) in LANGUAGE_NAMES


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
    recommended fallback model. A reply that was cut off, or that doesn't start with the language
    code it was asked for, counts as a failure, so the reader gets the original instead.
    """

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(
            timeout=CLAUDE_TIMEOUT_SECONDS, max_retries=CLAUDE_MAX_RETRIES
        )
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
        if response.stop_reason == "max_tokens":
            raise TranslationFailedError("Claude's translation was cut off")
        reply = "".join(block.text for block in response.content if block.type == "text").strip()
        if source_lang:
            return BackendTranslation(text=reply, source_lang=source_lang)
        detected_code, _, translated_text = reply.partition("\n")
        if not is_language_code(detected_code) or not translated_text.strip():
            raise TranslationFailedError(f"Claude's reply had no language code line: {reply!r}")
        return BackendTranslation(
            text=translated_text.strip(), source_lang=to_supported_lang(detected_code)
        )


class AzureBackend:
    """Azure AI Translator (REST v3). Needs AZURE_TRANSLATOR_KEY and AZURE_TRANSLATOR_REGION.

    AZURE_TRANSLATOR_ENDPOINT overrides the global endpoint. Sanele's test (27 Sep) found Azure
    usable for isiZulu and isiXhosa, but it produced nonsense for Sesotho, Sepedi and Setswana.
    """

    def __init__(self) -> None:
        self.endpoint = os.getenv("AZURE_TRANSLATOR_ENDPOINT", AZURE_DEFAULT_ENDPOINT).rstrip("/")
        self.headers = {
            "Ocp-Apim-Subscription-Key": os.environ["AZURE_TRANSLATOR_KEY"],
            "Ocp-Apim-Subscription-Region": os.environ["AZURE_TRANSLATOR_REGION"],
            "Content-Type": "application/json",
        }

    def translate(
        self, text: str, target_lang: Lang, source_lang: Lang | None
    ) -> BackendTranslation:
        parameters = {"api-version": AZURE_API_VERSION, "to": target_lang, "textType": "html"}
        if source_lang:
            parameters["from"] = source_lang
        try:
            response = httpx.post(
                f"{self.endpoint}/translate",
                params=parameters,
                headers=self.headers,
                json=[{"Text": to_protected_html(text)}],
                timeout=AZURE_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise TranslationFailedError(f"Azure Translator failed: {error}") from error
        result = response.json()[0]
        detected_code = (result.get("detectedLanguage") or {}).get("language")
        return BackendTranslation(
            text=to_plain_text(result["translations"][0]["text"]),
            source_lang=source_lang or to_supported_lang(detected_code),
        )


def to_protected_html(text: str) -> str:
    """Escape the text as HTML and wrap every [[n]] placeholder in Azure's notranslate span."""
    pieces: list[str] = []
    position = 0
    for match in PLACEHOLDER_IN_TEXT_PATTERN.finditer(text):
        pieces.append(html.escape(text[position : match.start()]))
        pieces.append(AZURE_NOTRANSLATE_SPAN.format(match.group()))
        position = match.end()
    pieces.append(html.escape(text[position:]))
    return "".join(pieces)


def to_plain_text(translated_html: str) -> str:
    """Remove Azure's spans and un-escape the HTML, giving plain text back."""
    return html.unescape(AZURE_SPAN_TAG_PATTERN.sub("", translated_html))


class TranslationFailedError(Exception):
    """A backend could not translate the message."""


BACKEND_CLASSES: dict[str, type] = {
    "fake": FakeBackend,
    "claude": ClaudeBackend,
    "azure": AzureBackend,
}
_backend_cache: dict[str, TranslationBackend] = {}


def get_backend(name: str | None = None) -> TranslationBackend:
    """Return the backend named here or in TRANSLATION_BACKEND, created once and reused."""
    backend_name = (name or os.getenv("TRANSLATION_BACKEND") or DEFAULT_BACKEND_NAME).lower()
    if backend_name not in BACKEND_CLASSES:
        raise ValueError(
            f"Unknown translation backend {backend_name!r}: use one of {sorted(BACKEND_CLASSES)}"
        )
    if backend_name not in _backend_cache:
        _backend_cache[backend_name] = BACKEND_CLASSES[backend_name]()
    return _backend_cache[backend_name]
