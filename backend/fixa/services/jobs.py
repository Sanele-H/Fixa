"""Job use cases: post, quote, accept, confirm, unlock. Owner: Role 3.

Every function that changes a job's state must call job_states.ensure_transition_allowed.
TODO (Role 3, Day 2-3): implement each function. docs/api-contract.md says which route uses which.
"""

from fixa.domain.models import ContactDetails, Job, NewJob, NewQuote, Quote, User
from fixa.ranking.provider_ranking import RankingStrategy
from fixa.storage.memory_store import MemoryStore


def post_job(
    store: MemoryStore,
    ranking_strategy: RankingStrategy,
    customer: User,
    new_job: NewJob,
) -> Job:
    """Create a job and shortlist providers for it (trade + area match, then rank).

    Demo step 2: Nomsa gets the job through the newcomer slot.
    """
    raise NotImplementedError("TODO Role 3: post_job")


def list_jobs_for_user(store: MemoryStore, viewer: User) -> list[Job]:
    """Customers see jobs they posted; providers see jobs they were shortlisted for."""
    raise NotImplementedError("TODO Role 3: list_jobs_for_user")


def create_quote(store: MemoryStore, provider: User, job_id: str, new_quote: NewQuote) -> Quote:
    """A shortlisted provider quotes a price and time. Moves posted -> quoted."""
    raise NotImplementedError("TODO Role 3: create_quote")


def list_quotes_for_job(store: MemoryStore, viewer: User, job_id: str) -> list[Quote]:
    """The job's customer sees every quote; a provider sees only their own."""
    raise NotImplementedError("TODO Role 3: list_quotes_for_job")


def accept_quote(store: MemoryStore, customer: User, job_id: str, quote_id: str) -> Job:
    """The job's customer accepts one quote. Moves quoted -> accepted."""
    raise NotImplementedError("TODO Role 3: accept_quote")


def confirm_job(store: MemoryStore, provider: User, job_id: str) -> Job:
    """The accepted provider confirms. Moves accepted -> confirmed."""
    raise NotImplementedError("TODO Role 3: confirm_job")


def unlock_contact_details(store: MemoryStore, customer: User, job_id: str) -> Job:
    """Both sides approved, so share details. Moves confirmed -> unlocked.

    This is where a booking fee would be charged (business model), even if faked for the demo.
    """
    raise NotImplementedError("TODO Role 3: unlock_contact_details")


def get_contact_details_for_job(store: MemoryStore, viewer: User, job_id: str) -> ContactDetails:
    """Return the OTHER party's contact details.

    Raises ContactDetailsLockedError unless the job is unlocked and the viewer is its customer
    or its assigned provider. This is the only place the app reads ContactDetails.
    """
    raise NotImplementedError("TODO Role 3: get_contact_details_for_job")
