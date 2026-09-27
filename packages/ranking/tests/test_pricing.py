"""price_range and is_underpriced: the middle of real accepted quotes, never an invented price."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ranking import AcceptedQuote, PriceRange, is_underpriced, price_range

SEED_PATH = Path(__file__).resolve().parents[3] / "data" / "seed"
LOCAL = "Braamfontein"


def make_quotes(amounts: list[int], suburb: str = LOCAL, trade: str = "plumbing", size="small"):
    """Makes accepted quotes for the given amounts, all in one suburb, trade and size."""
    return [
        AcceptedQuote(trade=trade, size=size, suburb=suburb, amount_rands=amount)
        for amount in amounts
    ]


def read_seed_accepted_quotes() -> list[AcceptedQuote]:
    """Joins the seed's accepted quotes with their jobs' trade, size and suburb, as P2 will."""
    jobs = json.loads((SEED_PATH / "jobs.json").read_text(encoding="utf-8"))
    quotes = json.loads((SEED_PATH / "quotes.json").read_text(encoding="utf-8"))
    jobs_by_id = {job["id"]: job for job in jobs}
    return [
        AcceptedQuote(
            trade=jobs_by_id[quote["job_id"]]["trade"],
            size=jobs_by_id[quote["job_id"]]["size"],
            suburb=jobs_by_id[quote["job_id"]]["suburb"],
            amount_rands=quote["amount_rands"],
        )
        for quote in quotes
        if quote["state"] == "accepted"
    ]


def test_no_range_below_eight_accepted_quotes():
    assert price_range("plumbing", "small", LOCAL, make_quotes([450] * 7)) is None


def test_enough_local_quotes_give_their_middle_half():
    quotes = make_quotes(list(range(100, 1300, 100)))  # R100 to R1,200, 12 quotes
    typical = price_range("plumbing", "small", LOCAL, quotes)
    assert (typical.low_rands, typical.high_rands, typical.n_quotes) == (350, 950, 12)
    assert (typical.trade, typical.size, typical.suburb) == ("plumbing", "small", LOCAL)


def test_other_trades_and_sizes_are_ignored():
    quotes = make_quotes([400] * 12)
    quotes += make_quotes([5000] * 20, trade="electrical")
    quotes += make_quotes([9000] * 20, size="large")
    typical = price_range("plumbing", "small", LOCAL, quotes)
    assert (typical.low_rands, typical.high_rands, typical.n_quotes) == (400, 400, 12)


def test_thin_local_data_leans_on_other_suburbs():
    quotes = make_quotes([1000] * 3) + make_quotes([400] * 30, suburb="Soweto")
    typical = price_range("plumbing", "small", LOCAL, quotes)
    wider_only = price_range("plumbing", "small", LOCAL, make_quotes([400] * 30, "Soweto"))
    assert typical.n_quotes == 33
    assert (wider_only.low_rands, wider_only.high_rands) == (400, 400)
    assert typical.low_rands == 400 < typical.high_rands < 1000  # local quotes pull it up


def test_a_suburb_with_no_quotes_gets_the_wider_range():
    typical = price_range("plumbing", "small", "Tembisa", make_quotes([300, 400, 500] * 4))
    assert (typical.low_rands, typical.high_rands, typical.suburb) == (300, 500, "Tembisa")


def test_too_few_quotes_even_with_other_suburbs_gives_no_range():
    quotes = make_quotes([450] * 3) + make_quotes([400] * 4, suburb="Soweto")
    assert price_range("plumbing", "small", LOCAL, quotes) is None


def test_suburb_matching_ignores_case_and_spaces():
    typical = price_range("plumbing", "small", " braamfontein ", make_quotes([500] * 12))
    assert (typical.low_rands, typical.n_quotes) == (500, 12)


def test_the_range_stays_within_real_quotes_and_is_rounded_to_ten_rands():
    amounts = [333, 347, 351, 368, 402, 419, 455, 463, 488, 512, 547, 590, 611]
    typical = price_range("plumbing", "small", LOCAL, make_quotes(amounts))
    assert min(amounts) <= typical.low_rands <= typical.high_rands <= max(amounts)
    assert typical.low_rands % 10 == 0 and typical.high_rands % 10 == 0


def test_quotes_must_be_positive():
    with pytest.raises(ValidationError):
        AcceptedQuote(trade="plumbing", size="small", suburb=LOCAL, amount_rands=0)


def test_the_demo_job_gets_a_sensible_range_from_the_seed_data():
    typical = price_range("plumbing", "small", LOCAL, read_seed_accepted_quotes())
    assert typical.n_quotes >= 12
    assert 250 <= typical.low_rands < typical.high_rands <= 700


@pytest.mark.parametrize(
    ("amount_rands", "expected"),
    [(270, True), (279, True), (280, False), (350, False), (900, False)],
)
def test_underpricing_means_under_80_percent_of_the_low_end(amount_rands, expected):
    typical = PriceRange(
        trade="plumbing", size="small", suburb=LOCAL, low_rands=350, high_rands=600, n_quotes=12
    )
    assert is_underpriced(amount_rands, typical) is expected


def test_no_underpricing_warning_without_a_range():
    assert is_underpriced(50, None) is False
