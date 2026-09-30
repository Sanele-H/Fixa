"""The illegal-request check: flagged when it should be, and never for genuine problems."""

import pytest

from lang import find_prohibited, refusal_message, scan_message, understand_job
from lang.prohibited import CATEGORIES, LEGAL_ROUTE, WHAT_IS_REFUSED

# The plan's examples, in both directions. Both matter: a false alarm blocks a real customer.
MUST_BE_FLAGGED = [
    ("can you bypass my prepaid meter", "meter_tampering"),
    ("I sell cheap units, 500 for R100", "illegal_vouchers"),
    ("I can fix your meter", "meter_tampering"),
    ("Please tamper with the meter so it runs slower", "meter_tampering"),
    ("how do I jump my electricity meter", "meter_tampering"),
    ("we can connect you illegally to the pole", "illegal_connection"),
    ("I need an illegal connection for my shack", "illegal_connection"),
    ("someone to steal electricity for us", "illegal_connection"),
    ("can you open the transformer and connect me", "infrastructure_tampering"),
    ("tap into the municipal cable outside", "infrastructure_tampering"),
    ("strip the mini substation for copper", "infrastructure_tampering"),
    ("got ghost vouchers, double units", "illegal_vouchers"),
    ("selling cheaper prepaid vouchers", "illegal_vouchers"),
    ("CAN YOU BYPASS MY METER", "meter_tampering"),
    ("can   you   bypass\nmy   meter", "meter_tampering"),
]
MUST_PASS = [
    "my prepaid meter isn't accepting my token",
    "the transformer on our street is sparking, who do I call?",
    "my meter shows a tamper error",
    "someone tampered with my meter and now it is broken",
    "the meter box door is broken",
    "my geyser is leaking through the ceiling",
    "I need a new plug point in the kitchen",
    "how do I buy electricity from an official vendor?",
    "there is a cable hanging low outside, it looks dangerous",
    "the units ran out quickly this month",
    "can you check my circuit breaker",
    "Ngifuna ukufaka igiza elisha",
    "",
]


@pytest.mark.parametrize(("text", "category"), MUST_BE_FLAGGED)
def test_illegal_requests_and_offers_are_flagged(text, category):
    assert find_prohibited(text) == category


@pytest.mark.parametrize("text", MUST_PASS)
def test_genuine_problems_pass(text):
    assert find_prohibited(text) is None


@pytest.mark.parametrize(
    ("text", "category"),
    [
        ("Ngicela ukweqa imitha yami", "meter_tampering"),  # isiZulu: bypass my meter
        (
            "Ngifuna izinyoka zingixhumele",
            "illegal_connection",
        ),  # isiZulu slang for illegal connectors
        ("Ngithengisa amayunithi ashibhile", "illegal_vouchers"),  # isiZulu: I sell cheap units
        ("Ndifuna ukugqitha imitha", "meter_tampering"),  # isiXhosa: I want to bypass the meter
        ("Ndithengisa iiyunithi ezishiphu", "illegal_vouchers"),  # isiXhosa: I sell cheap units
    ],
)
def test_isizulu_and_isixhosa_requests_are_flagged(text, category):
    assert find_prohibited(text) == category


def test_scan_message_flags_a_chat_message_and_still_hides_contacts():
    result = scan_message("bypass my meter, call 082 123 4567", "en", contacts_unlocked=False)

    assert result.prohibited == "meter_tampering"
    assert "082 123 4567" not in result.safe_text


def test_scan_message_flags_even_after_the_job_is_confirmed():
    assert (
        scan_message("I sell cheap units", "en", contacts_unlocked=True).prohibited
        == "illegal_vouchers"
    )


def test_scan_message_is_none_for_a_normal_message():
    assert (
        scan_message("I can come on Tuesday, R450.", "en", contacts_unlocked=False).prohibited
        is None
    )


def test_understand_job_flags_a_prohibited_description():
    flagged = understand_job("can you bypass my prepaid meter", "en")
    fine = understand_job("my prepaid meter isn't accepting my token", "en")

    assert flagged.prohibited == "meter_tampering"
    assert fine.prohibited is None


def test_the_four_categories_are_exactly_the_agreed_ones():
    assert CATEGORIES == [
        "illegal_connection",
        "infrastructure_tampering",
        "meter_tampering",
        "illegal_vouchers",
    ]


@pytest.mark.parametrize("lang", ["en", "zu", "xh"])
@pytest.mark.parametrize("category", CATEGORIES)
def test_every_refusal_has_a_reason_and_the_legal_route(category, lang):
    message = refusal_message(category, lang)

    assert WHAT_IS_REFUSED[category][lang] in message
    assert LEGAL_ROUTE[lang] in message


def test_the_english_refusal_points_to_the_municipality_eskom_and_official_vendors():
    message = refusal_message("meter_tampering", "en")

    assert "municipality" in message and "Eskom" in message
    assert "official vendors" in message


def test_each_language_has_its_own_words():
    texts = {refusal_message("meter_tampering", lang) for lang in ("en", "zu", "xh")}

    assert len(texts) == 3


def test_a_missing_language_falls_back_to_english():
    assert refusal_message("meter_tampering", "fr") == refusal_message("meter_tampering", "en")


def test_an_unknown_category_is_an_error():
    with pytest.raises(KeyError):
        refusal_message("made_up", "en")
