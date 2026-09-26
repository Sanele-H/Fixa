"""Runtime settings, read once from environment variables.

Copy `.env.example` to `.env` at the repo root and fill in what you need.
Never commit `.env` - it holds API keys.
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT_PATH = Path(__file__).resolve().parents[2]

DEFAULT_TRANSLATION_BACKEND_NAME = "echo"
DEFAULT_TRADE_SUGGESTER_NAME = "keywords"
DEFAULT_ALLOWED_ORIGINS = "http://localhost:5173"


@dataclass(frozen=True)
class Settings:
    """All configuration the backend reads from the environment.

    Attributes:
        translation_backend_name: Which translation backend to use ("echo", "google",
            "claude", "nllb", "lelapa"). "echo" needs no API key and is the default.
        trade_suggester_name: Which photo -> trade suggester to use ("keywords", "claude").
        google_translate_api_key: Key for the Google Translate backend, if used.
        anthropic_api_key: Key for Claude-based backends, if used.
        allowed_origins: Browser origins allowed to call the API directly (CORS).
    """

    translation_backend_name: str
    trade_suggester_name: str
    google_translate_api_key: str | None
    anthropic_api_key: str | None
    allowed_origins: list[str]


@lru_cache
def get_settings() -> Settings:
    """Load `.env` (if present) and return the settings. Cached after the first call."""
    load_dotenv(REPO_ROOT_PATH / ".env")
    allowed_origins_text = os.getenv("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS)
    return Settings(
        translation_backend_name=os.getenv("TRANSLATION_BACKEND", DEFAULT_TRANSLATION_BACKEND_NAME),
        trade_suggester_name=os.getenv("TRADE_SUGGESTER", DEFAULT_TRADE_SUGGESTER_NAME),
        google_translate_api_key=os.getenv("GOOGLE_TRANSLATE_API_KEY") or None,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        allowed_origins=[origin.strip() for origin in allowed_origins_text.split(",")],
    )
