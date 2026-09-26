"""The 30-message translation test: how many prices, times and trade terms each backend breaks,
with and without our number protection and glossary.

Owner: Role 1. Run from the repo root:  npm run translation-test -- --backends echo
Results go to experiments/translation_test/results/ (git-ignored; commit the final one on purpose).

The pitch line this produces: "Backend X broke N of 30 prices and times; with protection, 0."
"""

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

TEST_MESSAGES_CSV_PATH = Path(__file__).parent / "test_messages.csv"
RESULTS_DIRECTORY_PATH = Path(__file__).parent / "results"
LIST_SEPARATOR = "|"


@dataclass(frozen=True)
class TestMessage:
    """One row of test_messages.csv.

    Attributes:
        must_survive: Exact values (prices, times, numbers) that must appear in the translation.
        glossary_terms: Glossary term_ids the translation should use.
    """

    message_id: str
    source_language: str
    target_language: str
    text: str
    must_survive: tuple[str, ...]
    glossary_terms: tuple[str, ...]
    category: str


def split_list_cell(cell_text: str) -> tuple[str, ...]:
    """Turn "R450|10:00" into ("R450", "10:00"); an empty cell becomes ()."""
    return tuple(value.strip() for value in cell_text.split(LIST_SEPARATOR) if value.strip())


def read_test_messages(csv_path: Path = TEST_MESSAGES_CSV_PATH) -> list[TestMessage]:
    """Read every row of the test messages CSV."""
    with csv_path.open(encoding="utf-8", newline="") as csv_file:
        return [
            TestMessage(
                message_id=row["message_id"],
                source_language=row["source_language"],
                target_language=row["target_language"],
                text=row["text"],
                must_survive=split_list_cell(row["must_survive"]),
                glossary_terms=split_list_cell(row["glossary_terms"]),
                category=row["category"],
            )
            for row in csv.DictReader(csv_file)
        ]


def evaluate_backend(backend_name: str, test_messages: list[TestMessage]) -> list[dict]:
    """Translate every message twice (raw backend, then full pipeline) and score both.

    TODO (Role 1, Day 4): for each message record the translation, which must_survive values
    were lost, which glossary terms were missed, and the pipeline's flags. Use
    fixa.translation.backends.create_translation_backend and fixa.translation.pipeline.
    """
    raise NotImplementedError("TODO Role 1: evaluate_backend")


def write_results(result_rows: list[dict], backend_names: list[str]) -> Path:
    """Save one CSV of per-message results and return its path. TODO (Role 1, Day 4)."""
    raise NotImplementedError("TODO Role 1: write_results")


def parse_arguments() -> argparse.Namespace:
    """Read --backends from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backends", default="echo", help="Comma-separated backend names")
    return parser.parse_args()


def main() -> None:
    """Load the messages, evaluate each backend and print a summary table."""
    arguments = parse_arguments()
    test_messages = read_test_messages()
    backend_names = [name.strip() for name in arguments.backends.split(",")]
    print(f"Loaded {len(test_messages)} test messages (goal: 30). Backends: {backend_names}")
    result_rows = [row for name in backend_names for row in evaluate_backend(name, test_messages)]
    print(f"Results saved to {write_results(result_rows, backend_names)}")


if __name__ == "__main__":
    main()
