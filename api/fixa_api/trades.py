"""The trades Fixa knows, read from data/glossary.json."""

import json
from functools import cache
from pathlib import Path

GLOSSARY_PATH = Path(__file__).resolve().parents[2] / "data" / "glossary.json"


@cache
def known_trades() -> set[str]:
    """The trade ids in data/glossary.json."""
    glossary = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
    return {trade["id"] for trade in glossary["trades"]}
