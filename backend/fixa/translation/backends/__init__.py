"""Pick a translation backend by name (TRANSLATION_BACKEND in .env).

TODO (Role 1, Day 2-4): add at least two real backends to compare, one file each, e.g.
    google.py  - Google Translate REST API (GOOGLE_TRANSLATE_API_KEY)
    claude.py  - an LLM, which can follow glossary hints (ANTHROPIC_API_KEY)
    nllb.py    - Meta NLLB (uses codes like "zul_Latn")
    lelapa.py  - Lelapa AI, built for South African languages
then register each one in BACKEND_CLASSES_BY_NAME. Nothing else has to change.
"""

from fixa.translation.backends.base import TranslationBackend
from fixa.translation.backends.echo import EchoBackend

BACKEND_CLASSES_BY_NAME: dict[str, type[TranslationBackend]] = {
    EchoBackend.name: EchoBackend,
}


def create_translation_backend(backend_name: str) -> TranslationBackend:
    """Return a new backend for `backend_name`.

    Raises:
        ValueError: If no backend with that name is registered.
    """
    backend_class = BACKEND_CLASSES_BY_NAME.get(backend_name)
    if backend_class is None:
        known_names = ", ".join(sorted(BACKEND_CLASSES_BY_NAME))
        raise ValueError(f"Unknown TRANSLATION_BACKEND {backend_name!r}. Known: {known_names}")
    return backend_class()
