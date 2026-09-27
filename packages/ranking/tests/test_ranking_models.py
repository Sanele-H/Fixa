"""The output models have exactly the shapes of the agreed fixtures in contracts/fixtures/."""

import json
from pathlib import Path

import pytest

from ranking import Evidence, PriceRange, RankedProvider, TrustBadge

FIXTURES_PATH = Path(__file__).resolve().parents[3] / "contracts" / "fixtures"


def read_fixture(file_name: str):
    """Reads one JSON fixture from contracts/fixtures/."""
    return json.loads((FIXTURES_PATH / file_name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("fixture_row", read_fixture("ranked_providers.json"))
def test_ranked_provider_round_trips_the_fixture(fixture_row):
    assert RankedProvider.model_validate(fixture_row).model_dump() == fixture_row


def test_price_range_round_trips_the_fixture():
    fixture = read_fixture("price_range.json")
    assert PriceRange.model_validate(fixture).model_dump() == fixture


def test_profile_evidence_and_trust_round_trip_the_fixture():
    profile = read_fixture("provider_profile.json")
    assert Evidence.model_validate(profile["evidence"]).model_dump() == profile["evidence"]
    assert TrustBadge.model_validate(profile["trust"]).model_dump() == profile["trust"]
