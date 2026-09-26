"""Health check and the fixed lists the frontend needs (languages and trades)."""

from fastapi import APIRouter

from fixa.config import get_settings
from fixa.domain.models import ApiModel
from fixa.domain.trades import PILOT_TRADES
from fixa.translation.languages import LANGUAGE_NAMES_BY_CODE, PILOT_LANGUAGE_CODES

router = APIRouter(tags=["reference"])


class HealthStatus(ApiModel):
    """Proof the backend is up, and which translation backend it's using."""

    status: str
    translation_backend: str


class LanguageOption(ApiModel):
    """One entry in the language picker."""

    code: str
    name: str
    is_pilot: bool


class TradeOption(ApiModel):
    """One trade the customer can pick."""

    trade_id: str
    english_label: str
    icon: str


@router.get("/health")
def read_health() -> HealthStatus:
    """Return "ok" if the server is running."""
    return HealthStatus(status="ok", translation_backend=get_settings().translation_backend_name)


@router.get("/languages")
def list_languages() -> list[LanguageOption]:
    """Return every supported language, marking the pilot ones."""
    return [
        LanguageOption(code=code, name=name, is_pilot=code in PILOT_LANGUAGE_CODES)
        for code, name in LANGUAGE_NAMES_BY_CODE.items()
    ]


@router.get("/trades")
def list_trades() -> list[TradeOption]:
    """Return the pilot trades with their icons."""
    return [
        TradeOption(trade_id=trade.trade_id, english_label=trade.english_label, icon=trade.icon)
        for trade in PILOT_TRADES
    ]
