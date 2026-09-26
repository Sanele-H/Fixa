"""Each provider's chance that their next job goes well, as a Beta posterior.

A job went well if it was completed and the customer didn't answer "no" to "still
working?" two weeks later. A no-show or a "no" counts against the provider.

Each outcome counts with a weight:
- recent outcomes count more: the weight halves every RECENCY_HALF_LIFE_DAYS
- off-app jobs confirmed by SMS or USSD count half as much as in-app jobs

The ranking draws once from this posterior per search (Thompson sampling). The trust
summary (step 3) shows its mean and a range.
"""

from dataclasses import dataclass
from datetime import date

import numpy as np

from ranking.models import JobOutcome, ProviderStats

# The prior: what we assume with no evidence. Its mean is 0.8 (most jobs go well) and it's
# worth 2 jobs, so a few real outcomes soon outweigh it. Tuned in the simulation.
PRIOR_SUCCESSES = 1.6
PRIOR_FAILURES = 0.4
RECENCY_HALF_LIFE_DAYS = 365
OFF_APP_WEIGHT = 0.5  # P2's rule: off-app jobs count for less than in-app jobs


@dataclass(frozen=True)
class SuccessPosterior:
    """A Beta(successes, failures) belief about how likely a provider's next job goes well.

    successes and failures are weighted counts (Beta's alpha and beta), prior included.
    """

    successes: float
    failures: float

    @property
    def mean(self) -> float:
        """The expected chance that the next job goes well."""
        return self.successes / (self.successes + self.failures)


def calculate_posterior(stats: ProviderStats, today: date) -> SuccessPosterior:
    """Updates the prior with a provider's weighted outcomes, as of today."""
    weighted_successes = sum(
        weigh_outcome(outcome, today) for outcome in stats.outcomes if went_well(outcome)
    )
    weighted_failures = sum(
        weigh_outcome(outcome, today) for outcome in stats.outcomes if not went_well(outcome)
    )
    return SuccessPosterior(
        successes=PRIOR_SUCCESSES + weighted_successes,
        failures=PRIOR_FAILURES + weighted_failures,
    )


def went_well(outcome: JobOutcome) -> bool:
    """True if the job was completed and the customer didn't say it stopped working."""
    return outcome.completed and outcome.still_working is not False


def weigh_outcome(outcome: JobOutcome, today: date) -> float:
    """Returns how much an outcome counts: 1 for an in-app job finished today, less if older.

    The weight halves every RECENCY_HALF_LIFE_DAYS, and off-app jobs count OFF_APP_WEIGHT
    as much. Dates after today count as today.
    """
    age_days = max(0, (today - outcome.finished_on).days)
    recency_weight = 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)
    return recency_weight * (OFF_APP_WEIGHT if outcome.off_app else 1.0)


def draw_success_chance(posterior: SuccessPosterior, rng: np.random.Generator) -> float:
    """Draws one plausible success chance from the posterior (one Thompson sample).

    With little evidence the posterior is wide, so draws vary a lot from search to
    search: that's how newcomers get shown while we're still unsure about them.
    """
    return float(rng.beta(posterior.successes, posterior.failures))
