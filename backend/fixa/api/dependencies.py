"""Shared objects that routes receive through FastAPI's Depends.

Tests can replace any of these with app.dependency_overrides.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from fixa.config import get_settings
from fixa.domain.models import User
from fixa.ranking.provider_ranking import NewcomerFriendlyStrategy, RankingStrategy
from fixa.storage.memory_store import MemoryStore
from fixa.translation.backends import create_translation_backend
from fixa.translation.glossary import read_glossary_entries
from fixa.translation.pipeline import TranslationPipeline

DEMO_USER_HEADER = "X-User-Id"


@lru_cache
def get_store() -> MemoryStore:
    """Return the single in-memory store shared by every request."""
    return MemoryStore()


@lru_cache
def get_translation_pipeline() -> TranslationPipeline:
    """Build the translation pipeline once, using TRANSLATION_BACKEND from .env."""
    backend = create_translation_backend(get_settings().translation_backend_name)
    return TranslationPipeline(backend=backend, glossary_entries=read_glossary_entries())


def get_ranking_strategy() -> RankingStrategy:
    """Return the ranking used when a job is posted."""
    return NewcomerFriendlyStrategy()


def get_current_user(
    store: Annotated[MemoryStore, Depends(get_store)],
    user_id: Annotated[str | None, Header(alias=DEMO_USER_HEADER)] = None,
) -> User:
    """Return the user making the request.

    Demo-only "login": the frontend sends the chosen user's id in the X-User-Id header.
    There are no passwords. Say so if judges ask; real auth is a roadmap item.
    """
    user = store.get_user(user_id) if user_id else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Send a valid {DEMO_USER_HEADER} header (pick a demo user first)",
        )
    return user


StoreDependency = Annotated[MemoryStore, Depends(get_store)]
TranslationPipelineDependency = Annotated[TranslationPipeline, Depends(get_translation_pipeline)]
RankingStrategyDependency = Annotated[RankingStrategy, Depends(get_ranking_strategy)]
CurrentUserDependency = Annotated[User, Depends(get_current_user)]
