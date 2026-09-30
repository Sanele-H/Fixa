"""known_trades() reads every trade id from data/glossary.json."""

from fixa_api.trades import known_trades

EXPECTED_TRADES = frozenset(
    {
        "electrical",
        "plumbing",
        "carpentry",
        "welding",
        "bricklaying",
        "mechanic",
        "roofing",
        "tiling",
        "cabinetmaking",
        "painting",
        "appliance_repair",
        "groundskeeping",
        "other",
    }
)


def test_known_trades_has_all_thirteen():
    """The glossary has 13 trades and known_trades() returns every one of them."""
    assert known_trades() == EXPECTED_TRADES
