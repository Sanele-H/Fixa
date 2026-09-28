"""extract_quote() pulls the price and day or time out of real messages in 3 languages."""

import pytest

from lang import extract_quote


@pytest.mark.parametrize(
    ("text", "amount_rands", "when"),
    [
        ("Ngingafika ngoLwesibili, R450.", 450, "Tuesday"),
        ("Ngingafika ngoLwesibili ngo-10:00, R450", 450, "Tuesday 10:00"),
        ("Ngingayilungisa ngoR1200 , kukhona namaparts", 1200, None),
        ("Intengo yami yokugcina ingu-R2 500 futhi ngizoqeda ngoLwesihlanu.", 2500, "Friday"),
        ("Ndingeza ngoLwesithathu ngo-9:00, kuza kubiza ama-R600.", 600, "Wednesday 9:00"),
        ("Ndidinga umntu oza kupeyinta amagumbi amabini, malunga ne-R1,800?", 1800, None),
        ("I can do it for R1,250.50 tomorrow at 2pm", 1251, "tomorrow 2pm"),
        ("It costs 450 rand, I can come today", 450, "today"),
        ("Kubiza u-R350 ukuze beze lapho ukhona, besekuba u-R200 ngehora.", 350, None),
    ],
)
def test_price_and_time_from_real_messages(text, amount_rands, when):
    quote = extract_quote(text)
    assert quote is not None
    assert (quote.amount_rands, quote.when) == (amount_rands, when)


@pytest.mark.parametrize(
    "text",
    [
        "I-geyser yami iyavuza. Ungakwazi ukuza namuhla?",
        "I need a 15mm pipe replaced",
        "Can you come at 10:00?",
    ],
)
def test_a_message_without_a_price_has_no_quote(text):
    assert extract_quote(text) is None
