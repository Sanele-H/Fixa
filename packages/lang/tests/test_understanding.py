"""understand_job() reads the trade, urgency and size from real descriptions in 3 languages."""

import pytest

from lang import understand_job


@pytest.mark.parametrize(
    ("text", "lang", "trade", "urgency"),
    [
        (
            "My geyser is leaking, water is everywhere. Can you come today?",
            "en",
            "plumbing",
            "urgent",
        ),
        (
            "I-geyser yami iyavuza, amanzi agcwele yonke indawo. Ungakwazi ukuza namuhla?",
            "zu",
            "plumbing",
            "urgent",
        ),
        ("Igiza lami liyavuza", "zu", "plumbing", "normal"),
        ("Impompi yasekhishini ayiyeki ukuvuza.", "zu", "plumbing", "normal"),
        ("Indlu yangasese ivalilekile futhi amanzi aphumela phansi.", "zu", "plumbing", "normal"),
        (
            "Ngidinga ukushintshwa kwepayipi elingu-15mm ngaphansi kosinki.",
            "zu",
            "plumbing",
            "normal",
        ),
        ("I-geyser yam iqhushumbe ngale ntsasa, nceda undincede.", "xh", "plumbing", "urgent"),
        (
            "Umbhobho wangaphandle waphukile kwaye amanzi abaleka esiya esitratweni.",
            "xh",
            "plumbing",
            "normal",
        ),
        (
            "The electricity keeps tripping when I switch on the kettle",
            "en",
            "electrical",
            "normal",
        ),
        ("Ugesi uhlale ucisha uma ngivula iketela", "zu", "electrical", "normal"),
        (
            "Imitha yami ekhokhelwa kusengaphambili ikhombisa ukuthi khukhona inkinga, "
            "izibani azikhanyi.",
            "zu",
            "electrical",
            "normal",
        ),
        ("Akukho mbane kwisiqingatha sendlu.", "xh", "electrical", "urgent"),
        ("There are sparks coming from the plug", "en", "electrical", "urgent"),
        ("I need a welder to fix my burglar bars", "en", "welding", "normal"),
        ("The front gate is broken and needs welding", "en", "welding", "normal"),
        ("The boundary wall has collapsed", "en", "bricklaying", "normal"),
        ("I need my car serviced, the brakes are squeaking", "en", "mechanic", "normal"),
        ("The roof leaks into the passage when it rains", "en", "roofing", "normal"),
        ("Three floor tiles in the kitchen are cracked", "en", "tiling", "normal"),
        ("I need a built-in wardrobe for the bedroom", "en", "cabinetmaking", "normal"),
        ("The lounge needs repainting, walls and ceiling", "en", "painting", "normal"),
        (
            "The washing machine won't spin and makes a loud noise",
            "en",
            "appliance_repair",
            "normal",
        ),
        ("The lawn needs mowing and the hedges are overgrown", "en", "groundskeeping", "normal"),
    ],
)
def test_trade_and_urgency_from_real_descriptions(text, lang, trade, urgency):
    intent = understand_job(text, lang)
    assert (intent.trade, intent.urgency) == (trade, urgency)
    assert intent.confidence >= 0.6


@pytest.mark.parametrize(
    ("text", "size"),
    [
        ("The tap in the kitchen won't stop dripping", "small"),
        ("I need a new geyser installed", "large"),
        ("I need the whole house rewired", "large"),
        ("My geyser is leaking", "medium"),
    ],
)
def test_job_size(text, size):
    assert understand_job(text, "en").size == size


def test_no_rush_is_low_urgency():
    assert understand_job("Leaking tap, no rush, next week is fine", "en").urgency == "low"


def test_an_unknown_job_gets_a_low_confidence_guess():
    intent = understand_job("Can someone help me with my house?", "en")
    assert intent.confidence <= 0.2
    assert intent.trade == "other"


def test_more_matching_words_means_more_confidence():
    one_word = understand_job("My geyser is broken", "en").confidence
    three_words = understand_job("My geyser pipe is leaking under the sink", "en").confidence
    assert three_words > one_word
