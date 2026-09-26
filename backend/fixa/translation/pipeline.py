"""The one function the rest of the app calls to translate: TranslationPipeline.translate.

Owner: Role 1. Role 3's message service depends on the TranslationResult shape below, so
agree any change to it with Role 3 first.
"""

from dataclasses import dataclass
from enum import StrEnum

from fixa.translation.backends.base import TranslationBackend
from fixa.translation.glossary import GlossaryEntry


class TranslationFlag(StrEnum):
    """Why a translation might be wrong. The frontend shows an "unsure" marker for any flag."""

    PROTECTED_VALUE_LOST = "protected_value_lost"
    GLOSSARY_TERM_MISSING = "glossary_term_missing"
    BACKEND_UNCERTAIN = "backend_uncertain"
    BACKEND_FAILED = "backend_failed"


@dataclass(frozen=True)
class TranslationResult:
    """A finished translation, ready to store on a Message.

    Attributes:
        text: Translated text with prices, times and numbers exactly as the sender typed them.
        flags: Empty when we're confident. See TranslationFlag.
        backend_name: Which backend produced it, for the 30-message test results.
    """

    text: str
    flags: tuple[TranslationFlag, ...]
    backend_name: str


class TranslationPipeline:
    """Protects values, applies the glossary, calls a backend and flags anything doubtful."""

    def __init__(self, backend: TranslationBackend, glossary_entries: list[GlossaryEntry]) -> None:
        """Keep the backend and glossary. Both are injected so tests can pass fakes."""
        self.backend = backend
        self.glossary_entries = glossary_entries

    def translate(
        self, text: str, source_language_code: str, target_language_code: str
    ) -> TranslationResult:
        """Translate `text` for a reader of `target_language_code`.

        Must never raise: on backend failure, return the original text with BACKEND_FAILED,
        so chat keeps working even when the Wi-Fi doesn't.

        TODO (Role 1, Day 2-3): same-language shortcut, protect_tokens, glossary hints,
        backend call, restore_tokens, glossary check, flags. Cache repeated translations.
        """
        raise NotImplementedError("TODO Role 1: TranslationPipeline.translate")
