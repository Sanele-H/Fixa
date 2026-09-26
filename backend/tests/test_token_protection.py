"""Role 1's to-do list for number protection. Expected to fail until protect/restore exist."""

import pytest

from fixa.domain.tokens import MASKED_CONTACT_TOKEN
from fixa.translation.token_protection import protect_tokens, restore_tokens

pytestmark = pytest.mark.xfail(raises=NotImplementedError, reason="TODO Role 1: token protection")


@pytest.mark.parametrize(
    ("text", "values_that_must_be_protected"),
    [
        ("Ek kan dit regmaak vir R450, Dinsdag om 10:00.", ["R450", "10:00"]),
        ("R1 500 for 2 taps, 10h00", ["R1 500", "2", "10h00"]),
        ("15mm pipe, 3pm", ["15mm", "3pm"]),
        (f"My number is {MASKED_CONTACT_TOKEN}", [MASKED_CONTACT_TOKEN]),
        # TODO: "450 rand", dates, mixed English/isiZulu from the 30 test messages
    ],
)
def test_values_are_swapped_out_before_translation(text, values_that_must_be_protected):
    protected = protect_tokens(text)

    for value in values_that_must_be_protected:
        assert value in protected.protected_values
        assert value not in protected.text


def test_round_trip_restores_the_exact_text():
    text = "Ek kan dit regmaak vir R450, Dinsdag om 10:00."
    protected = protect_tokens(text)

    restored = restore_tokens(protected.text, protected)

    assert restored.text == text
    assert restored.missing_values == ()


def test_lost_placeholders_are_reported():
    protected = protect_tokens("R450 at 10:00")

    restored = restore_tokens("a translation that dropped everything", protected)

    assert set(restored.missing_values) == {"R450", "10:00"}
