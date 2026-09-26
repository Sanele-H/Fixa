"""Data shapes for the ranking package.

P2's API builds the inputs (JobRequest, Candidate, ProviderStats, AcceptedQuote) from its
database and gets the outputs back (RankedProvider, TrustSummary, PriceRange). The output
shapes match contracts/fixtures/, so P2 can return them as they are.

Fairness by construction: ProviderStats holds job evidence only, and it is all that the
trust summary and the ranking score read. A provider's name, ID badge and photo count
travel in Candidate so they can be shown on the card, but no scoring code reads them.
Language, nationality and photos of the person are never passed in at all.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

JobSize = Literal["small", "medium", "large"]
IdBadge = Literal["none", "id_number", "home_affairs"]


class JobOutcome(BaseModel):
    """One finished job that says something about the provider's work.

    Leave out jobs the customer cancelled before the provider confirmed: they say nothing
    about the provider. Off-app jobs appear here only once the customer has confirmed them.
    """

    model_config = ConfigDict(extra="forbid")

    finished_on: date
    completed: bool  # False: the provider didn't turn up, or cancelled after confirming
    still_working: bool | None = None  # the two-week "still working?" answer; None if not given
    off_app: bool = False  # logged by the provider, confirmed by the customer over SMS or USSD


class ProviderStats(BaseModel):
    """A provider's job evidence: the only input to the trust summary and the ranking score.

    extra="forbid" makes it an error to pass anything else, such as an ID badge or language.
    """

    model_config = ConfigDict(extra="forbid")

    outcomes: list[JobOutcome] = Field(default_factory=list)
    repeat_customers: int = 0  # customers who hired this provider more than once


class Candidate(BaseModel):
    """One provider who could be shown for a job, as P2 passes it to rank_providers.

    distance_km is worked out by P2, so exact locations never leave the server.
    display_name, id_badge and photos are copied to the result and never scored.
    """

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    display_name: str
    trades: list[str]
    distance_km: float
    id_badge: IdBadge = "none"
    photos: int = 0  # before/after photos, for the evidence strip
    licensed: bool = False
    open_quotes: int = 0
    active_jobs: int = 0
    stats: ProviderStats


class JobRequest(BaseModel):
    """The job the customer wants providers for."""

    model_config = ConfigDict(extra="forbid")

    trade: str
    size: JobSize
    needs_licence: bool = False  # electrical work needing a CoC, geyser installs
    posted_on: date  # "today" for weighting recent outcomes; the simulation sets its own clock


class Evidence(BaseModel):
    """The evidence strip on a provider card, in the shape of ranked_providers.json."""

    jobs: int  # completed in-app jobs
    repeat_customers: int
    photos: int
    off_app_confirmed: int


class TrustBadge(BaseModel):
    """The part of a TrustSummary shown on a provider card. score is None for newcomers."""

    score: float | None
    low: float | None
    high: float | None
    label: str


class RankedProvider(BaseModel):
    """One row of the ranked list, in the shape of contracts/fixtures/ranked_providers.json."""

    provider_id: str
    display_name: str
    trades: list[str]
    distance_km: float
    is_newcomer: bool
    id_badge: IdBadge
    evidence: Evidence
    trust: TrustBadge


class TrustBreakdown(BaseModel):
    """What a trust score is built from, for the trust breakdown screen."""

    jobs: int  # completed in-app jobs
    repeat_customers: int
    off_app_confirmed: int
    still_working_rate: float | None  # share of "still working?" answers that were yes


class TrustSummary(BaseModel):
    """How likely a provider's next job is to go well, with a range showing how sure we are.

    score, low and high are None while the evidence is too thin to say.
    """

    score: float | None
    low: float | None
    high: float | None
    n_evidence: int  # job outcomes the score is built on
    breakdown: TrustBreakdown
    label: str

    def to_badge(self) -> TrustBadge:
        """Returns the fields a provider card shows."""
        return TrustBadge(score=self.score, low=self.low, high=self.high, label=self.label)


class AcceptedQuote(BaseModel):
    """An accepted quote, joined with its job's trade, size and suburb by P2."""

    model_config = ConfigDict(extra="forbid")

    trade: str
    size: JobSize
    suburb: str
    amount_rands: int


class PriceRange(BaseModel):
    """The typical price range, in the shape of contracts/fixtures/price_range.json."""

    trade: str
    size: JobSize
    suburb: str
    low_rands: int
    high_rands: int
    n_quotes: int
