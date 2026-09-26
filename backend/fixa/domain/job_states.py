"""The job lifecycle, and the rule that contact details only unlock at the end of it.

    posted -> quoted -> accepted -> confirmed -> unlocked

- posted:    customer posted the job; shortlisted providers can see it.
- quoted:    at least one provider sent a quote (price + time).
- accepted:  customer accepted one quote.
- confirmed: that provider confirmed. Both sides have now approved.
- unlocked:  phone numbers and address are shared with both sides.

Owner: Role 3. The server, not the frontend, enforces every transition.
"""

from enum import StrEnum


class JobState(StrEnum):
    """Where a job is in its lifecycle. Values are what the API sends to the frontend."""

    POSTED = "posted"
    QUOTED = "quoted"
    ACCEPTED = "accepted"
    CONFIRMED = "confirmed"
    UNLOCKED = "unlocked"


class InvalidJobTransitionError(Exception):
    """Raised when a job is asked to move to a state it may not reach from its current one."""


def is_transition_allowed(current_state: JobState, target_state: JobState) -> bool:
    """Return True if a job in `current_state` may move to `target_state`.

    TODO (Role 3, Day 2): define the allowed transitions (see the module docstring) and
    decide what happens to extra quotes once one is accepted.
    """
    raise NotImplementedError("TODO Role 3: define allowed job transitions")


def ensure_transition_allowed(current_state: JobState, target_state: JobState) -> None:
    """Raise InvalidJobTransitionError unless the move is allowed.

    Call this in every service function that changes a job's state, so no route can skip it.
    """
    if not is_transition_allowed(current_state, target_state):
        raise InvalidJobTransitionError(f"Cannot move a job from {current_state} to {target_state}")


def is_contact_sharing_allowed(job_state: JobState) -> bool:
    """Return True only when contact details may be sent for a job in this state.

    TODO (Role 3, Day 3): this is the core safety rule. Keep it this small and test it.
    """
    raise NotImplementedError("TODO Role 3: decide when contact details unlock")
