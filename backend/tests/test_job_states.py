"""Role 3's to-do list for the job lifecycle. Expected to fail until transitions are defined."""

import pytest

from fixa.domain.job_states import (
    InvalidJobTransitionError,
    JobState,
    ensure_transition_allowed,
    is_contact_sharing_allowed,
)

pytestmark = pytest.mark.xfail(raises=NotImplementedError, reason="TODO Role 3: job states")

HAPPY_PATH = [
    (JobState.POSTED, JobState.QUOTED),
    (JobState.QUOTED, JobState.ACCEPTED),
    (JobState.ACCEPTED, JobState.CONFIRMED),
    (JobState.CONFIRMED, JobState.UNLOCKED),
]


@pytest.mark.parametrize(("current_state", "target_state"), HAPPY_PATH)
def test_demo_path_is_allowed(current_state, target_state):
    ensure_transition_allowed(current_state, target_state)


def test_cannot_skip_straight_to_unlocked():
    with pytest.raises(InvalidJobTransitionError):
        ensure_transition_allowed(JobState.POSTED, JobState.UNLOCKED)


@pytest.mark.parametrize("job_state", [state for state in JobState if state != JobState.UNLOCKED])
def test_contact_details_stay_hidden_before_unlock(job_state):
    assert not is_contact_sharing_allowed(job_state)


def test_contact_details_are_shared_once_unlocked():
    assert is_contact_sharing_allowed(JobState.UNLOCKED)
