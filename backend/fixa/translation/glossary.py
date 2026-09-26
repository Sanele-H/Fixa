"""The trade glossary: how each trade term should be said in each pilot language.

Owner: Role 1. Data lives in data/glossary.csv (one row per term, one column per language).

Two uses:
1. Hints: tell the backend which target term to use (LLM backends can follow these).
2. Checks: after translating, confirm the expected term appears; if not, flag as unsure.

isiZulu and the other Nguni and Sotho-Tswana languages add prefixes that change with grammar
(igiza -> legiza), so the CSV notes suggest storing a stem such as "-giza" for checks.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

GLOSSARY_CSV_PATH = Path(__file__).parent / "data" / "glossary.csv"
NON_LANGUAGE_COLUMNS = frozenset({"term_id", "trade", "checked_by", "notes"})


@dataclass(frozen=True)
class GlossaryEntry:
    """One trade term in every language we have it for.

    Attributes:
        term_id: Stable id, e.g. "geyser".
        trade: Which trade it belongs to, e.g. "plumbing".
        terms_by_language: Language code -> term. Missing languages are left out.
    """

    term_id: str
    trade: str
    terms_by_language: dict[str, str]


def read_glossary_entries(csv_path: Path = GLOSSARY_CSV_PATH) -> list[GlossaryEntry]:
    """Read every row of the glossary CSV into a GlossaryEntry, skipping empty language cells."""
    with csv_path.open(encoding="utf-8", newline="") as csv_file:
        return [
            GlossaryEntry(
                term_id=row["term_id"],
                trade=row["trade"],
                terms_by_language={
                    language_code: term.strip()
                    for language_code, term in row.items()
                    if language_code not in NON_LANGUAGE_COLUMNS and term and term.strip()
                },
            )
            for row in csv.DictReader(csv_file)
        ]


def find_entries_in_text(
    entries: list[GlossaryEntry], text: str, language_code: str
) -> list[GlossaryEntry]:
    """Return the entries whose term in `language_code` appears in `text`.

    TODO (Role 1, Day 3): decide how to match (whole word? stem?) per language.
    """
    raise NotImplementedError("TODO Role 1: find_entries_in_text")


def find_missing_target_terms(
    entries: list[GlossaryEntry], translated_text: str, target_language_code: str
) -> list[GlossaryEntry]:
    """Return the entries whose expected target-language term is NOT in `translated_text`.

    TODO (Role 1, Day 3).
    """
    raise NotImplementedError("TODO Role 1: find_missing_target_terms")
