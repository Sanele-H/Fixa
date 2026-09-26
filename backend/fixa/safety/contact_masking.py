"""Hide phone numbers, emails and addresses that people type into chat before the job unlocks.

Owner: Role 3. Runs FIRST in the message pipeline, before translation, so the raw number
is never stored and "See original" can't reveal it.

The hard part is disguised numbers: "o82 one two three...", "0 8 2", number words in
Afrikaans and isiZulu, "double five". backend/tests/test_contact_masking.py lists the
tricky cases to beat; add your own as you find them.

Must NOT mask prices ("R450") or times ("10:00") - the demo depends on those coming through.
"""

from dataclasses import dataclass

from fixa.domain.tokens import MASKED_CONTACT_TOKEN


@dataclass(frozen=True)
class MaskingResult:
    """The outcome of masking one message.

    Attributes:
        masked_text: The message with each contact detail replaced by MASKED_CONTACT_TOKEN.
        masked_value_count: How many contact details were hidden (0 if none).
    """

    masked_text: str
    masked_value_count: int

    @property
    def contains_masked_contact(self) -> bool:
        """True if anything in the message was hidden."""
        return self.masked_value_count > 0


def mask_contact_details(text: str) -> MaskingResult:
    """Replace every phone number, email and street address in `text` with MASKED_CONTACT_TOKEN.

    Args:
        text: The message exactly as the sender typed it, in any language.

    Returns:
        A MaskingResult. Text with nothing to hide comes back unchanged.

    TODO (Role 3, Day 3): implement. A suggested approach is in docs/roles/role-3-backend-safety.md.
    """
    raise NotImplementedError(f"TODO Role 3: mask contact details using {MASKED_CONTACT_TOKEN!r}")
