"""The trades the pilot supports.

TODO (whole team, Day 1): pick the 2 or 3 pilot trades and trim this list to match.
The frontend shows `icon` next to the label so people who read less can still find their trade.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Trade:
    """One trade a provider can offer.

    Attributes:
        trade_id: Stable id used in the API and database, e.g. "plumbing".
        english_label: Label for docs and logs. UI labels live in the frontend i18n files.
        icon: Emoji placeholder until Role 2 picks real icons.
    """

    trade_id: str
    english_label: str
    icon: str


PILOT_TRADES: tuple[Trade, ...] = (
    Trade(trade_id="plumbing", english_label="Plumbing", icon="🔧"),
    Trade(trade_id="electrical", english_label="Electrical", icon="⚡"),
    Trade(trade_id="painting", english_label="Painting", icon="🎨"),
)

PILOT_TRADE_IDS: frozenset[str] = frozenset(trade.trade_id for trade in PILOT_TRADES)
