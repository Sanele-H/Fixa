"""scan_message() hides contact details however they're disguised, and never over-hides."""

import pytest

from lang.safety import (
    HIDDEN_CONTACT_TEXT,
    SCAM_WARNING_ONE_TIME_PIN,
    SCAM_WARNING_SUSPICIOUS_LINK,
    SCAM_WARNING_UPFRONT_PAYMENT,
    scan_message,
)


@pytest.mark.parametrize(
    "text",
    [
        "Call me 0821234567",
        "Call me 082 123 4567",
        "Call me 082-123-4567",
        "Call me (082) 123 4567",
        "Call me +27 82 123 4567",
        "Call me o82 one two three four five six seven",
        "Call me zero eight two one two three four five six seven",
        "Call me zero eight two double one three triple four",
        "WhatsApp o82.123.4567",
        "Ngishayele ku 082 123 4567",
    ],
)
def test_disguised_phone_numbers_are_hidden(text):
    result = scan_message(text, "en", contacts_unlocked=False)
    assert result.safe_text.endswith(HIDDEN_CONTACT_TEXT)
    assert not any(char.isdigit() for char in result.safe_text)
    assert [finding.kind for finding in result.findings] == ["phone"]


@pytest.mark.parametrize(
    "text",
    [
        "I can come on Tuesday, R450.",
        "Ngizoba khona ngo-10:30 kusasa ekuseni.",
        "I need a 15mm pipe replaced under the sink.",
        "My final price is R2 500 and I finish on 29/09.",
        "It costs R350 for the call-out and R200 per hour.",
        "I've done this work for 8 years, the one with the green gate.",
        "Oh, I can come at 10:00, 11:00 or 12:00.",
    ],
)
def test_prices_times_and_sizes_are_never_hidden(text):
    result = scan_message(text, "en", contacts_unlocked=False)
    assert result.safe_text == text
    assert result.findings == []


def test_a_time_next_to_a_number_hides_only_the_number():
    result = scan_message("Come at 10:00, 082 123 4567", "en", contacts_unlocked=False)
    assert result.safe_text == f"Come at 10:00, {HIDDEN_CONTACT_TEXT}"


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("Email me nomsa@example.co.za", "email"),
        ("Email me nomsa at gmail dot com", "email"),
        ("See my work on www.nomsaplumbing.co.za", "link"),
        ("Chat to me on wa.me/27821234567", "link"),
        ("I live at 12 Protea Street, Soweto", "address"),
    ],
)
def test_emails_links_and_addresses_are_hidden(text, kind):
    result = scan_message(text, "en", contacts_unlocked=False)
    assert HIDDEN_CONTACT_TEXT in result.safe_text
    assert [finding.kind for finding in result.findings] == [kind]


def test_contacts_show_once_the_job_is_confirmed():
    text = "Call me on 082 123 4567, I'm at 12 Protea Street"
    result = scan_message(text, "en", contacts_unlocked=True)
    assert result.safe_text == text
    assert [finding.kind for finding in result.findings] == ["phone", "address"]


@pytest.mark.parametrize(
    ("text", "warning"),
    [
        ("Please send me a deposit of R500 first", SCAM_WARNING_UPFRONT_PAYMENT),
        ("Ngicela ungithumele idiphozithi engu-R500 kuqala", SCAM_WARNING_UPFRONT_PAYMENT),
        ("Pay me via eWallet before I come", SCAM_WARNING_UPFRONT_PAYMENT),
        ("Send me the OTP you just got", SCAM_WARNING_ONE_TIME_PIN),
        ("What's the one-time pin on your phone?", SCAM_WARNING_ONE_TIME_PIN),
        ("Pay here bit.ly/fixa-pay", SCAM_WARNING_SUSPICIOUS_LINK),
    ],
)
def test_scam_patterns_are_warned_about(text, warning):
    assert warning in scan_message(text, "en", contacts_unlocked=False).scam_warnings


def test_scam_warnings_apply_even_after_contacts_unlock():
    result = scan_message("Send me a deposit first", "en", contacts_unlocked=True)
    assert result.scam_warnings == [SCAM_WARNING_UPFRONT_PAYMENT]


def test_an_ordinary_message_has_no_warnings():
    result = scan_message("I-geyser yami iyavuza. Ungakwazi ukuza namuhla?", "zu", False)
    assert result.scam_warnings == []


def test_warning_texts_come_in_the_readers_language():
    from lang import get_scam_warning_texts

    codes = [SCAM_WARNING_UPFRONT_PAYMENT, SCAM_WARNING_ONE_TIME_PIN]
    assert get_scam_warning_texts(codes, "zu")[0].startswith("Qaphela: ungalokothi ukhokhe")
    assert get_scam_warning_texts(codes, "xh")[1].startswith("Ungaze wabelane")
    assert get_scam_warning_texts([SCAM_WARNING_SUSPICIOUS_LINK], "en") == [
        "Be careful with links from people you don't know. Don't enter your personal details."
    ]


def test_idiphozi_is_caught_too():
    result = scan_message("Ngicela ungithumele idiphozi kuqala", "zu", contacts_unlocked=False)
    assert result.scam_warnings == [SCAM_WARNING_UPFRONT_PAYMENT]
