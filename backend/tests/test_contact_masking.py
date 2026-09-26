"""Role 3's to-do list for contact masking, written as tests.

Every test is marked "expected to fail with NotImplementedError" until mask_contact_details
exists. After that, any real failure shows up red. Add the trickiest cases you find in
interviews ("masking rules catch the 10 trickiest test cases" is the Day 3 goal).
"""

import pytest

from fixa.domain.tokens import MASKED_CONTACT_TOKEN
from fixa.safety.contact_masking import mask_contact_details

pytestmark = pytest.mark.xfail(raises=NotImplementedError, reason="TODO Role 3: masking")

MESSAGES_THAT_MUST_BE_MASKED = [
    "Call me on 082 123 4567",
    "0821234567",
    "+27 82 123 4567",
    "o82 one two three four five six seven",  # letter o and number words (demo step 3)
    "0 8 2 1 2 3 4 5 6 7",
    "nul agt twee een twee drie vier vyf ses sewe",  # Afrikaans number words
    "email me at someone@example.com",
    "I'm at 12 Sample Street, Mondeor",
    # TODO: isiZulu number words, "double five", "WhatsApp me on...", your interview finds
]

MESSAGES_THAT_MUST_NOT_CHANGE = [
    "Ek kan dit regmaak vir R450, Dinsdag om 10:00.",
    "I need 2 taps and 15mm pipe, about R1 500 total",
    "Kan iemand Dinsdag kom?",
]


@pytest.mark.parametrize("message", MESSAGES_THAT_MUST_BE_MASKED)
def test_contact_details_are_hidden(message):
    result = mask_contact_details(message)

    assert MASKED_CONTACT_TOKEN in result.masked_text
    assert result.contains_masked_contact


@pytest.mark.parametrize("message", MESSAGES_THAT_MUST_NOT_CHANGE)
def test_prices_times_and_quantities_are_left_alone(message):
    result = mask_contact_details(message)

    assert result.masked_text == message
    assert not result.contains_masked_contact
