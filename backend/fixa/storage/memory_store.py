"""An in-memory store with one Create/Read/Update/Delete method per operation.

Owner: Role 3. Services call these methods; routes never touch the dictionaries directly,
so swapping in SQLite later means rewriting this file only.

Users are implemented so the frontend can connect on day 1. The rest are TODO.
"""

from fixa.domain.models import ContactDetails, Job, Message, Quote, User
from fixa.seed.demo_data import create_demo_contact_details, create_demo_users


class MemoryStore:
    """Holds all demo data in dictionaries keyed by id."""

    def __init__(self) -> None:
        self.users_by_id: dict[str, User] = {}
        self.contact_details_by_user_id: dict[str, ContactDetails] = {}
        self.jobs_by_id: dict[str, Job] = {}
        self.quotes_by_id: dict[str, Quote] = {}
        self.messages_by_id: dict[str, Message] = {}
        self.reset_to_demo_data()

    def reset_to_demo_data(self) -> None:
        """Clear everything and reload the seeded demo profiles. Used between rehearsals."""
        self.users_by_id = {user.id: user for user in create_demo_users()}
        self.contact_details_by_user_id = {
            details.user_id: details for details in create_demo_contact_details()
        }
        self.jobs_by_id = {}
        self.quotes_by_id = {}
        self.messages_by_id = {}

    # Users ---------------------------------------------------------------

    def list_users(self) -> list[User]:
        """Return every user, customers first, then providers, each in seed order."""
        return sorted(self.users_by_id.values(), key=lambda user: user.role.value)

    def get_user(self, user_id: str) -> User | None:
        """Return the user with this id, or None if there isn't one."""
        return self.users_by_id.get(user_id)

    def update_user(self, user: User) -> User:
        """Replace the stored user that has the same id, and return it."""
        self.users_by_id[user.id] = user
        return user

    # Contact details (read only through the unlock flow) -----------------

    def get_contact_details(self, user_id: str) -> ContactDetails | None:
        """Return a user's private contact details. Only services/jobs.py should call this."""
        return self.contact_details_by_user_id.get(user_id)

    # Jobs ------------------------------------------------------------------

    def create_job(self, job: Job) -> Job:
        """Store a new job and return it. TODO (Role 3, Day 2)."""
        raise NotImplementedError("TODO Role 3: create_job")

    def get_job(self, job_id: str) -> Job | None:
        """Return the job with this id, or None. TODO (Role 3, Day 2)."""
        raise NotImplementedError("TODO Role 3: get_job")

    def list_jobs(self) -> list[Job]:
        """Return all jobs, newest first. TODO (Role 3, Day 2)."""
        raise NotImplementedError("TODO Role 3: list_jobs")

    def update_job(self, job: Job) -> Job:
        """Replace the stored job that has the same id. TODO (Role 3, Day 2)."""
        raise NotImplementedError("TODO Role 3: update_job")

    # Quotes ----------------------------------------------------------------

    def create_quote(self, quote: Quote) -> Quote:
        """Store a new quote and return it. TODO (Role 3, Day 2)."""
        raise NotImplementedError("TODO Role 3: create_quote")

    def list_quotes_for_job(self, job_id: str) -> list[Quote]:
        """Return the quotes for one job, oldest first. TODO (Role 3, Day 2)."""
        raise NotImplementedError("TODO Role 3: list_quotes_for_job")

    # Messages --------------------------------------------------------------

    def create_message(self, message: Message) -> Message:
        """Store a message that has already been masked and translated. TODO (Role 3, Day 2)."""
        raise NotImplementedError("TODO Role 3: create_message")

    def list_messages_for_job(self, job_id: str) -> list[Message]:
        """Return a job's messages, oldest first. TODO (Role 3, Day 2)."""
        raise NotImplementedError("TODO Role 3: list_messages_for_job")
