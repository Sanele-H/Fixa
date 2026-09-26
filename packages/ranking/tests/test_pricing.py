"""price_range. Step 0 stub: always None. The rule tested here holds for the real one too."""

from ranking import AcceptedQuote, price_range


def test_no_range_below_eight_accepted_quotes():
    quotes = [
        AcceptedQuote(trade="plumbing", size="small", suburb="Braamfontein", amount_rands=450)
        for _ in range(7)
    ]
    assert price_range("plumbing", "small", "Braamfontein", quotes) is None
