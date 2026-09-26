"""Jobs, quotes, the approval steps and the unlock. Each route is a thin call to services/jobs.py.

Until Role 3 fills in the services, these answer 501 with the TODO that owns them.
"""

from fastapi import APIRouter, UploadFile, status

from fixa.api.dependencies import CurrentUserDependency, RankingStrategyDependency, StoreDependency
from fixa.classification.trade_suggestion import TradeSuggestion
from fixa.domain.models import ApiModel, ContactDetails, Job, NewJob, NewQuote, Quote
from fixa.services import jobs as job_service

router = APIRouter(tags=["jobs"])


class QuoteAcceptance(ApiModel):
    """Request body for accepting a quote."""

    quote_id: str


@router.post("/trade-suggestions")
def create_trade_suggestion(photo: UploadFile, description: str = "") -> TradeSuggestion:
    """Suggest a trade and job size from a photo (demo step 1). TODO Role 3."""
    raise NotImplementedError("TODO Role 3: trade suggestion route")


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
def create_job(
    new_job: NewJob,
    current_user: CurrentUserDependency,
    store: StoreDependency,
    ranking_strategy: RankingStrategyDependency,
) -> Job:
    """Post a job as the current customer, and shortlist providers for it."""
    return job_service.post_job(store, ranking_strategy, current_user, new_job)


@router.get("/jobs")
def list_jobs(current_user: CurrentUserDependency, store: StoreDependency) -> list[Job]:
    """Jobs the current user posted (customer) or was shortlisted for (provider).

    TODO (Role 1 + 3): include the description translated into the viewer's language.
    """
    return job_service.list_jobs_for_user(store, current_user)


@router.post("/jobs/{job_id}/quotes", status_code=status.HTTP_201_CREATED)
def create_quote(
    job_id: str, new_quote: NewQuote, current_user: CurrentUserDependency, store: StoreDependency
) -> Quote:
    """Quote a price and time for a job, as a shortlisted provider."""
    return job_service.create_quote(store, current_user, job_id, new_quote)


@router.get("/jobs/{job_id}/quotes")
def list_quotes(
    job_id: str, current_user: CurrentUserDependency, store: StoreDependency
) -> list[Quote]:
    """Quotes on a job: all of them for its customer, only their own for a provider."""
    return job_service.list_quotes_for_job(store, current_user, job_id)


@router.post("/jobs/{job_id}/accept")
def accept_quote(
    job_id: str,
    acceptance: QuoteAcceptance,
    current_user: CurrentUserDependency,
    store: StoreDependency,
) -> Job:
    """Accept one quote, as the job's customer."""
    return job_service.accept_quote(store, current_user, job_id, acceptance.quote_id)


@router.post("/jobs/{job_id}/confirm")
def confirm_job(job_id: str, current_user: CurrentUserDependency, store: StoreDependency) -> Job:
    """Confirm the job, as the provider whose quote was accepted."""
    return job_service.confirm_job(store, current_user, job_id)


@router.post("/jobs/{job_id}/unlock")
def unlock_contact_details(
    job_id: str, current_user: CurrentUserDependency, store: StoreDependency
) -> Job:
    """Share contact details once both sides have approved."""
    return job_service.unlock_contact_details(store, current_user, job_id)


@router.get("/jobs/{job_id}/contact-details")
def read_contact_details(
    job_id: str, current_user: CurrentUserDependency, store: StoreDependency
) -> ContactDetails:
    """The other side's phone number (and address, for providers). 403 until unlocked."""
    return job_service.get_contact_details_for_job(store, current_user, job_id)
