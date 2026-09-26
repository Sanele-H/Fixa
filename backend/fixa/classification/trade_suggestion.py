"""Suggest a trade and job size from a photo and a short description.

Owner: Role 3. The plan says one AI call is enough. Demo step 1: Mrs. van Wyk photographs
the leak and the app suggests "Plumbing, small job".

Suggested shape: a keyword suggester that always works offline, plus a vision-model
suggester (chosen with TRADE_SUGGESTER in .env) that falls back to keywords on any error.
"""

from abc import ABC, abstractmethod

from fixa.domain.models import ApiModel, JobSize


class TradeSuggestion(ApiModel):
    """What the app suggests to the customer. They can always change it.

    Attributes:
        trade: One of fixa.domain.trades.PILOT_TRADE_IDS.
        size: Rough job size.
        confidence: 0.0 to 1.0.
        source: Which suggester produced it, e.g. "keywords" or "claude".
    """

    trade: str
    size: JobSize
    confidence: float
    source: str


class TradeSuggester(ABC):
    """Anything that can turn a photo and/or description into a TradeSuggestion."""

    @abstractmethod
    def suggest_trade(
        self, photo_bytes: bytes | None, photo_media_type: str | None, description: str
    ) -> TradeSuggestion:
        """Return the best-guess trade and size. Must not raise; fall back instead."""


def create_trade_suggester(suggester_name: str) -> TradeSuggester:
    """Return the suggester named in settings.

    TODO (Role 3, Day 3): implement KeywordTradeSuggester first, then a vision one.
    """
    raise NotImplementedError(f"TODO Role 3: trade suggester {suggester_name!r}")
