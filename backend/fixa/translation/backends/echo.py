"""A fake backend for offline development: tags the text with the target language, no API key.

If you ever see "[zu] ..." in the demo, TRANSLATION_BACKEND in .env is still set to "echo".
"""

from collections.abc import Sequence

from fixa.translation.backends.base import BackendTranslation, GlossaryHint, TranslationBackend


class EchoBackend(TranslationBackend):
    """Returns the input unchanged apart from a "[target]" prefix."""

    name = "echo"

    def translate(
        self,
        text: str,
        source_language_code: str,
        target_language_code: str,
        glossary_hints: Sequence[GlossaryHint],
    ) -> BackendTranslation:
        """Return `text` prefixed with the target language code, e.g. "[zu] My geiser lek"."""
        return BackendTranslation(text=f"[{target_language_code}] {text}")
