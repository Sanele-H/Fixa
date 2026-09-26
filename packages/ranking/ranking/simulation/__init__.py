"""The fairness simulation (step 2): Fixa's ranking against plain sort-by-rating.

Both rankers run on the same simulated city, with the same providers, jobs and customer
behaviour. Fixa's side calls rank_providers unchanged. Run from the repo root to write
the charts and a summary table to packages/ranking/results/:

    node scripts/run-python.mjs -m ranking.simulation
"""

import numpy as np

from ranking.ranker import rank_providers
from ranking.simulation.baseline import rank_by_rating, rank_without_exploring
from ranking.simulation.run import Ranker, SimulationResult, run_simulation
from ranking.simulation.world import SimConfig, create_jobs, create_providers

DEFAULT_SEED = 2026
FIXA_RANKER_NAME = "Fixa ranking"
RATING_RANKER_NAME = "Sort by rating"
NO_EXPLORING_RANKER_NAME = "Fixa without exploring"
RANKERS: dict[str, Ranker] = {
    FIXA_RANKER_NAME: rank_providers,
    RATING_RANKER_NAME: rank_by_rating,
    NO_EXPLORING_RANKER_NAME: rank_without_exploring,
}


def compare_rankers(
    config: SimConfig | None = None, seed: int = DEFAULT_SEED
) -> dict[str, SimulationResult]:
    """Runs every ranker on the same simulated city. Returns {ranker name: result}."""
    config = config or SimConfig()
    world_rng = np.random.default_rng(seed)
    providers = create_providers(world_rng, config)
    jobs = create_jobs(world_rng, config)
    return {
        ranker_name: run_simulation(ranker_name, ranker, providers, jobs, config, seed)
        for ranker_name, ranker in RANKERS.items()
    }
