"""Prices, times, dates, phone numbers and addresses survive translation unchanged."""

import pytest

from lang.protection import ProtectedValue, protect, restore


@pytest.mark.parametrize(
    ("text", "expected_values"),
    [
        ("Ngingafika ngoLwesibili, R450.", ["R450"]),
        ("I can come Tuesday 10:00", ["10:00"]),
        ("Ngizofika ngo 10h30", ["10h30"]),
        ("Around 2pm tomorrow", ["2pm"]),
        ("The job is R1 200 all in", ["R1 200"]),
        ("Kuzobiza R1,250.50", ["R1,250.50"]),
        ("It costs 450 rand", ["450 rand"]),
        ("See you on 29/09", ["29/09"]),
        ("Booked for 2026-09-29", ["2026-09-29"]),
        ("Can we do 3 Oct?", ["3 Oct"]),
        ("I need a 15mm pipe", ["15mm"]),
        ("Call 082 123 4567 after 5pm", ["082 123 4567", "5pm"]),
        ("Or +27 82 123 4567", ["+27 82 123 4567"]),
        ("I live at 12 Protea Street, Soweto", ["12 Protea Street"]),
        ("Email nomsa@example.co.za", ["nomsa@example.co.za"]),
    ],
)
def test_protect_takes_out_each_value(text, expected_values):
    protected = protect(text)
    assert [value.text for value in protected.values] == expected_values
    for value in expected_values:
        assert value not in protected.text


def test_protect_leaves_plain_words_alone():
    protected = protect("Igiza lami liyavuza, ngicela usizo")
    assert protected.values == []
    assert protected.text == "Igiza lami liyavuza, ngicela usizo"


def test_price_and_time_in_one_message_are_separate_values():
    protected = protect("R450, Tuesday 10:00")
    assert [(value.kind, value.text) for value in protected.values] == [
        ("price", "R450"),
        ("time", "10:00"),
    ]
    assert protected.text == "[[0]], Tuesday [[1]]"


def test_restore_puts_values_back_even_when_reordered():
    protected = protect("Ngingafika ngo 10:00 ngoLwesibili, R450.")
    translated = "It will cost [[1]]. I can come on Tuesday at [[0]]."
    restored = restore(translated, protected.values)
    assert restored.text == "It will cost R450. I can come on Tuesday at 10:00."
    assert restored.missing == []


@pytest.mark.parametrize("mangled", ["[[ 0 ]]", "[0]", "[[0]"])
def test_restore_accepts_placeholders_a_backend_mangled(mangled):
    values = [ProtectedValue(kind="price", text="R450")]
    assert restore(f"It costs {mangled}.", values).text == "It costs R450."


def test_restore_reports_a_dropped_placeholder():
    protected = protect("R450, Tuesday 10:00")
    restored = restore("Tuesday [[1]]", protected.values)
    assert [value.text for value in restored.missing] == ["R450"]


def test_protect_then_restore_without_translation_gives_the_original_back():
    text = "Call 082 123 4567, R450 at 12 Protea Street on 29/09 at 10:00"
    protected = protect(text)
    assert restore(protected.text, protected.values).text == text
