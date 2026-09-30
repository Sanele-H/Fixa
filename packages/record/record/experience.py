"""What a provider's confirmed jobs add up to: which trade, over what span, and by task.

Kept free of PDF code so the PDF, the HTML record page and the verify page all use the
same numbers.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from record.models import RecordEvidence, RecordJob

# Trades with an ARPL toolkit (merSETA form LPM-FM-009, category G), by glossary trade id,
# with the trade title the form asks for. The form's full toolkit list is below: add a
# trade here once P3 puts its id in data/glossary.json.
ARPL_TRADE_TITLES = {
    "plumbing": "Plumber",
    "electrical": "Electrician",
    "carpentry": "Carpenter",
    "welding": "Welder",
    "bricklaying": "Bricklayer",
    "mechanic": "Automotive Motor Mechanic",
    "painting": "Painter",
}
MERSETA_TOOLKIT_TRADE_TITLES = [
    "Diesel Mechanic", "Automotive Motor Mechanic", "Boilermaker", "Welder", "Pipe-Fitter",
    "Fitter & Turner", "Electrician", "Heavy Equipment Mechanic", "Instrument Mechanic",
    "Lift Mechanic", "Shipbuilder", "Panel Beater", "Vehicle Painter", "Bricklayer",
    "Plumber", "Carpenter", "Sheetfed Lithographer", "Mechanical Fitter", "Millwright",
    "Rigger",
]  # fmt: skip
ARPL_TRADES = frozenset(ARPL_TRADE_TITLES)
MONTHS_PER_YEAR = 12
CONFIRMATION_NAMES = {"app": "in the app", "sms": "by customer SMS", "ussd": "by customer USSD"}


class ArplTradeError(ValueError):
    """Raised for an ARPL export when the provider has no trade with an ARPL toolkit."""


@dataclass(frozen=True)
class ExperienceSummary:
    """The span of confirmed work, for the form's experience requirements."""

    first_job_on: date | None
    last_job_on: date | None
    span_months: int  # whole months from the first confirmed job to the last
    months_with_work: int  # calendar months with at least one confirmed job
    calendar_months: int  # calendar months from the first job's month to the last's


@dataclass(frozen=True)
class TaskExperience:
    """One row of the form's "Details of Experience" table: a trade task and its dates."""

    trade_task: str
    first_done_on: date
    last_done_on: date
    job_count: int
    suburbs: list[str]
    confirmation_counts: dict[str, int]  # how many were confirmed in the app, by SMS, by USSD


def choose_arpl_trade(evidence: RecordEvidence) -> str:
    """Returns the trade an ARPL record is for.

    That is evidence.arpl_trade if set, or else the provider's ARPL trade with the most
    confirmed jobs.

    Raises:
        ArplTradeError: the chosen trade has no ARPL toolkit, isn't one of the provider's
            trades, or the provider has no ARPL trade at all.
    """
    arpl_trades = [trade for trade in evidence.trades if trade in ARPL_TRADES]
    if evidence.arpl_trade is not None:
        if evidence.arpl_trade not in arpl_trades:
            raise ArplTradeError(f"No ARPL toolkit record for trade {evidence.arpl_trade!r}")
        return evidence.arpl_trade
    if not arpl_trades:
        raise ArplTradeError(f"No ARPL toolkit for trades {evidence.trades}")
    return max(arpl_trades, key=lambda trade: len(list_trade_jobs(evidence, trade)))


def list_trade_jobs(evidence: RecordEvidence, trade: str) -> list[RecordJob]:
    """Lists the provider's jobs in one trade, oldest first."""
    return sorted((job for job in evidence.jobs if job.trade == trade), key=lambda job: job.done_on)


@dataclass(frozen=True)
class ArplExperience:
    """How much confirmed work counts towards ARPL: the trade it's for (None when the provider
    has no trade with an ARPL toolkit) and the experience in it."""

    arpl_trade: str | None
    summary: ExperienceSummary


def summarise_arpl_experience(evidence: RecordEvidence) -> ArplExperience:
    """The experience an ARPL record would show: in the ARPL trade chosen as for the export, or
    across all confirmed jobs, with no trade, when the provider has no ARPL trade."""
    try:
        arpl_trade = choose_arpl_trade(evidence)
    except ArplTradeError:
        return ArplExperience(arpl_trade=None, summary=summarise_experience(evidence.jobs))
    trade_jobs = list_trade_jobs(evidence, arpl_trade)
    return ArplExperience(arpl_trade=arpl_trade, summary=summarise_experience(trade_jobs))


def summarise_experience(jobs: list[RecordJob]) -> ExperienceSummary:
    """Works out the span of confirmed work and how many months had work in them."""
    if not jobs:
        return ExperienceSummary(None, None, 0, 0, 0)
    first_job_on = min(job.done_on for job in jobs)
    last_job_on = max(job.done_on for job in jobs)
    worked_months = {(job.done_on.year, job.done_on.month) for job in jobs}
    return ExperienceSummary(
        first_job_on=first_job_on,
        last_job_on=last_job_on,
        span_months=count_whole_months(first_job_on, last_job_on),
        months_with_work=len(worked_months),
        calendar_months=count_calendar_months(first_job_on, last_job_on),
    )


def count_whole_months(start: date, end: date) -> int:
    """Counts the whole months from start to end (30 Sep to 29 Oct is 0 months)."""
    months = (end.year - start.year) * MONTHS_PER_YEAR + end.month - start.month
    return months - 1 if end.day < start.day else months


def count_calendar_months(start: date, end: date) -> int:
    """Counts the calendar months from start's month to end's month, both included."""
    return (end.year - start.year) * MONTHS_PER_YEAR + end.month - start.month + 1


def format_duration(months: int) -> str:
    """Formats a number of months as "3 years 11 months"."""
    years, remaining_months = divmod(months, MONTHS_PER_YEAR)
    parts = []
    if years:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if remaining_months or not years:
        parts.append(f"{remaining_months} month{'s' if remaining_months != 1 else ''}")
    return " ".join(parts)


def group_jobs_by_task(jobs: list[RecordJob]) -> list[TaskExperience]:
    """Groups jobs by trade task, most jobs first, for the "Details of Experience" rows."""
    jobs_by_task: dict[str, list[RecordJob]] = defaultdict(list)
    for job in jobs:
        jobs_by_task[job.trade_task].append(job)
    task_rows = [summarise_task(task, task_jobs) for task, task_jobs in jobs_by_task.items()]
    return sorted(task_rows, key=lambda row: (-row.job_count, row.trade_task))


def summarise_task(trade_task: str, jobs: list[RecordJob]) -> TaskExperience:
    """Summarises the jobs of one trade task: dates, count, suburbs and how they were confirmed."""
    confirmation_counts: dict[str, int] = defaultdict(int)
    for job in jobs:
        confirmation_counts[job.confirmed_via] += 1
    return TaskExperience(
        trade_task=trade_task,
        first_done_on=min(job.done_on for job in jobs),
        last_done_on=max(job.done_on for job in jobs),
        job_count=len(jobs),
        suburbs=sorted({job.suburb for job in jobs}),
        confirmation_counts=dict(confirmation_counts),
    )


def count_jobs_by_year(jobs: list[RecordJob]) -> dict[int, int]:
    """Counts confirmed jobs per calendar year, for the experience timeline."""
    job_counts: dict[int, int] = defaultdict(int)
    for job in jobs:
        job_counts[job.done_on.year] += 1
    return dict(sorted(job_counts.items()))


def describe_confirmations(confirmation_counts: dict[str, int]) -> str:
    """Describes how jobs were confirmed, such as "9 by customer SMS, 2 in the app"."""
    return ", ".join(
        f"{count} {CONFIRMATION_NAMES[method]}"
        for method, count in sorted(confirmation_counts.items(), key=lambda item: -item[1])
    )
