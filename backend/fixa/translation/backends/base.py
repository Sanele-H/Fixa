"""The interface every translation backend implements, so the pipeline can swap them freely."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class GlossaryHint:
    """Tells a backend which target-language word to use for a source-language term."""

    source_term: str
    target_term: str


@dataclass(frozen=True)
class BackendTranslation:
    """What a backend returns.

    Attributes:
        text: The translated text, placeholders included.
        is_uncertain: True if the backend itself reports low confidence (e.g. an LLM says so).
    """

    text: str
    is_uncertain: bool = False


class TranslationBackendError(Exception):
    """Raised when a backend can't translate (network down, no API key, refusal...).

    The pipeline catches this and shows the original text with a flag instead of crashing chat.
    """


class TranslationBackend(ABC):
    """One way of translating text, e.g. Google Translate, NLLB, an LLM or Lelapa AI."""

    name: str

    @abstractmethod
    def translate(
        self,
        text: str,
        source_language_code: str,
        target_language_code: str,
        glossary_hints: Sequence[GlossaryHint],
    ) -> BackendTranslation:
        """Translate `text`, leaving placeholders untouched.

        Args:
            text: Text after token protection, so it contains placeholders.
            source_language_code: ISO code from fixa.translation.languages.
            target_language_code: ISO code from fixa.translation.languages.
            glossary_hints: Preferred target terms. Backends that can't use hints ignore them.

        Raises:
            TranslationBackendError: If translation fails for any reason.
        """
