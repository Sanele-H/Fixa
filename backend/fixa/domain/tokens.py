"""Special tokens that more than one module must agree on.

MASKED_CONTACT_TOKEN replaces a phone number, email or address that someone typed into chat.
- Role 3's contact masking writes it.
- Role 1's token protection must keep it unchanged through translation.
- Role 2's chat bubble renders it as a localised "number hidden" chip.
It is language-neutral on purpose, so it never needs translating.
"""

MASKED_CONTACT_TOKEN = "[***]"
