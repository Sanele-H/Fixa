"""Provider profiles, browsing nearby providers and price guidance."""

from typing import Annotated

from fastapi import APIRouter, Query

from fixa_api.fixtures import load_fixture

router = APIRouter(prefix="/api", tags=["providers"])


@router.get("/providers")
def read_nearby_providers(
    trade: str,
    lang: str | None = None,
    radius_km: Annotated[float, Query(gt=0, le=30)] = 10,
):
    return load_fixture("nearby_providers.json")


@router.get("/providers/{provider_id}")
def read_provider(provider_id: str):
    return load_fixture("provider_profile.json")


@router.get("/price-range")
def read_price_range(trade: str, size: str, suburb: str):
    return load_fixture("price_range.json")
