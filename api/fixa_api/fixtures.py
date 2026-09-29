"""Loads the sample responses in contracts/fixtures/. Routes serve them until real code exists."""

import json
from functools import cache
from pathlib import Path
from typing import Any

FIXTURES_PATH = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"


@cache
def _read(file_name: str) -> str:
    return (FIXTURES_PATH / file_name).read_text(encoding="utf-8")


def load_fixture(file_name: str) -> Any:
    """Return the parsed JSON of one fixture, for example load_fixture("job_public.json")."""
    return json.loads(_read(file_name))
