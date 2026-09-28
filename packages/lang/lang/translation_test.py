"""The 30-message translation test: which backend keeps prices, times and trade words right?

Run from the repo root:
    .venv/Scripts/python -m lang.translation_test --backends azure claude
    .venv/Scripts/python -m lang.translation_test --backends azure claude --compare-protection

It reads data/test_messages.json, translates every message with each backend, and scores:
- numbers kept: every value in must_keep_numbers appears exactly in the translation
- terms kept: every word in must_keep_terms appears in the translation
- speed: seconds per message (chat needs about 2 s)

Meaning can't be scored by a script, so the report lists each translation next to the
must_keep_meaning notes for a native speaker to check. The report is written to
packages/lang/results/.
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from lang.backends import BACKEND_CLASSES, get_backend
from lang.translation import translate

REPO_ROOT_PATH = Path(__file__).resolve().parents[3]
TEST_MESSAGES_PATH = REPO_ROOT_PATH / "data" / "test_messages.json"
RESULTS_DIRECTORY_PATH = REPO_ROOT_PATH / "packages" / "lang" / "results"
CHAT_SPEED_TARGET_SECONDS = 2.0


class TestMessage(BaseModel):
    __test__ = False  # A test message, not a pytest test class
    id: str
    lang: str
    target_lang: str
    text: str
    draft_en: str = ""  # The English meaning, for whoever writes the message
    must_keep_numbers: list[str] = []
    must_keep_terms: list[str] = []
    must_keep_meaning: list[str] = []
    notes: str = ""


class MessageResult(BaseModel):
    message: TestMessage
    run_name: str
    translated_text: str
    flagged: bool
    numbers_kept: bool
    terms_kept: bool
    seconds: float


def load_test_messages() -> list[TestMessage]:
    """Read the test messages from data/test_messages.json, skipping ones not written yet."""
    data = json.loads(TEST_MESSAGES_PATH.read_text(encoding="utf-8"))
    messages = [TestMessage(**message) for message in data["messages"]]
    written_messages = [message for message in messages if message.text.strip()]
    unwritten_ids = [message.id for message in messages if not message.text.strip()]
    if unwritten_ids:
        print(f"Skipping {len(unwritten_ids)} messages not written yet: {', '.join(unwritten_ids)}")
    return written_messages


def load_env_file() -> None:
    """Load the repo-root .env so API keys are available, if python-dotenv is installed."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(REPO_ROOT_PATH / ".env")


def run_message(message: TestMessage, backend_name: str, use_protection: bool) -> MessageResult:
    """Translate one message and score it."""
    backend = get_backend(backend_name)
    started_at = time.perf_counter()
    if use_protection:
        translation = translate(message.text, message.target_lang, message.lang, backend=backend)
        translated_text, flagged = translation.text, translation.flagged
    else:
        raw = backend.translate(message.text, message.target_lang, message.lang)
        translated_text, flagged = raw.text, False
    seconds = time.perf_counter() - started_at
    lowered_text = translated_text.lower()
    return MessageResult(
        message=message,
        run_name=backend_name if use_protection else f"{backend_name} (no protection)",
        translated_text=translated_text,
        flagged=flagged,
        numbers_kept=all(number in translated_text for number in message.must_keep_numbers),
        terms_kept=all(term.lower() in lowered_text for term in message.must_keep_terms),
        seconds=seconds,
    )


def summarise_run(results: list[MessageResult]) -> str:
    """One table row: how a backend did across every message."""
    count = len(results)
    numbers_kept_count = sum(result.numbers_kept for result in results)
    terms_kept_count = sum(result.terms_kept for result in results)
    flagged_count = sum(result.flagged for result in results)
    average_seconds = sum(result.seconds for result in results) / count
    slowest_seconds = max(result.seconds for result in results)
    return (
        f"| {results[0].run_name} | {numbers_kept_count}/{count} | {terms_kept_count}/{count} "
        f"| {flagged_count} | {average_seconds:.2f} s | {slowest_seconds:.2f} s |"
    )


def build_report(results_by_run: dict[str, list[MessageResult]]) -> str:
    """The markdown report: a summary table, then every translation for a native speaker."""
    lines = [
        f"# Translation test, {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"Chat target: about {CHAT_SPEED_TARGET_SECONDS:.0f} s per message.",
        "",
        "| Run | Numbers kept | Terms kept | Flagged | Average | Slowest |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines += [summarise_run(results) for results in results_by_run.values()]
    lines += ["", "## Every translation (check the meaning)", ""]
    for run_name, results in results_by_run.items():
        lines += [f"### {run_name}", "", "| Id | Original | Translation | Check meaning | OK? |"]
        lines += ["| --- | --- | --- | --- | --- |"]
        for result in results:
            problems = []
            if not result.numbers_kept:
                problems.append("numbers")
            if not result.terms_kept:
                problems.append("terms")
            if result.flagged:
                problems.append("flagged")
            status = "lost " + ", ".join(problems) if problems else "yes"
            lines.append(
                f"| {result.message.id} | {result.message.text} | {result.translated_text} "
                f"| {', '.join(result.message.must_keep_meaning)} | {status} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the 30-message translation test.")
    parser.add_argument("--backends", nargs="+", default=["fake"], choices=list(BACKEND_CLASSES))
    parser.add_argument(
        "--compare-protection",
        action="store_true",
        help="Also run each backend without number protection, to show what protection fixes.",
    )
    arguments = parser.parse_args()

    load_env_file()
    messages = load_test_messages()
    results_by_run: dict[str, list[MessageResult]] = {}
    protection_settings = [True, False] if arguments.compare_protection else [True]
    for backend_name in arguments.backends:
        for use_protection in protection_settings:
            results = [run_message(message, backend_name, use_protection) for message in messages]
            results_by_run[results[0].run_name] = results
            print(summarise_run(results))

    RESULTS_DIRECTORY_PATH.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIRECTORY_PATH / f"translation_test_{datetime.now():%Y%m%d_%H%M}.md"
    report_path.write_text(build_report(results_by_run), encoding="utf-8")
    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    main()
