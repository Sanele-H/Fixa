"""Command line for the fairness simulation. From the repo root:

    node scripts/run-python.mjs -m ranking.simulation [--seed N] [--out FOLDER]

It writes the pitch charts and summary.md to packages/ranking/results/ (about 40 s).
"""

import argparse
from pathlib import Path

from ranking.simulation import DEFAULT_SEED, compare_rankers
from ranking.simulation.report import write_report
from ranking.simulation.world import SimConfig

RESULTS_DIR_PATH = Path(__file__).resolve().parents[2] / "results"


def main() -> None:
    """Runs every ranker on the simulated city and writes the charts and summary table."""
    arguments = parse_arguments()
    config = SimConfig()
    results = compare_rankers(config, arguments.seed)
    summaries = write_report(results, config, arguments.seed, arguments.out)
    for ranker_name, summary in summaries.items():
        print(ranker_name, round_measures(summary))
    print(f"Charts and summary.md written to {arguments.out}")


def round_measures(summary: dict) -> dict:
    """Rounds a ranker's measures to 3 decimals for printing."""
    return {
        name: round(value, 3) if isinstance(value, float) else value
        for name, value in summary.items()
    }


def parse_arguments() -> argparse.Namespace:
    """Reads the command-line options; every one has a default."""
    parser = argparse.ArgumentParser(
        prog="python -m ranking.simulation", description="Runs the Fixa fairness simulation."
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="random seed")
    parser.add_argument("--out", type=Path, default=RESULTS_DIR_PATH, help="output folder")
    return parser.parse_args()


if __name__ == "__main__":
    main()
