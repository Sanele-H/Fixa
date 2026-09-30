"""The job state machine: which state can follow which.

posted -> quoting -> quote_accepted -> confirmed -> in_progress -> done -> followed_up
A provider who declines sends the job back to quoting. Any state can move to cancelled.
Contact details unlock at `confirmed` (see job_views.py).
"""

POSTED = "posted"
QUOTING = "quoting"
QUOTE_ACCEPTED = "quote_accepted"
CONFIRMED = "confirmed"
IN_PROGRESS = "in_progress"
DONE = "done"
FOLLOWED_UP = "followed_up"
CANCELLED = "cancelled"

TRANSITIONS: dict[str, set[str]] = {
    POSTED: {QUOTING, CANCELLED},
    QUOTING: {QUOTE_ACCEPTED, CANCELLED},
    QUOTE_ACCEPTED: {CONFIRMED, QUOTING, CANCELLED},
    CONFIRMED: {IN_PROGRESS, CANCELLED},
    IN_PROGRESS: {DONE, CANCELLED},
    DONE: {FOLLOWED_UP, CANCELLED},
    FOLLOWED_UP: {CANCELLED},
    CANCELLED: set(),
}

# Providers can send quotes and see the job in their feed only while it is looking for quotes.
OPEN_FOR_QUOTES = {POSTED, QUOTING}

# From here on the customer and the confirmed provider may see phone numbers and the address.
UNLOCKED_STATES = {CONFIRMED, IN_PROGRESS, DONE, FOLLOWED_UP}


class InvalidTransitionError(Exception):
    """Raised when a job is asked to move to a state that cannot follow its current one."""


def check_transition(current: str, new: str) -> None:
    if new not in TRANSITIONS.get(current, set()):
        raise InvalidTransitionError(f"A job that is {current} cannot become {new}")
