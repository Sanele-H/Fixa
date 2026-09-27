"""price_range: the typical price for a job, worked out from accepted quotes only.

The range is the middle half of accepted quotes (25th to 75th percentile) for the same
trade and job size:
- A suburb with at least LOCAL_QUOTES_FOR_LOCAL_ONLY quotes gets a range from its own
  quotes only.
- A suburb with fewer leans on the same trade and size in other suburbs. Those quotes
  fill in for the missing local ones, together counting as the missing number of quotes
  and never more than one quote each.
- Below MIN_QUOTES_FOR_RANGE quotes in all, there is no range (None).

It never invents a price: the percentiles lie between real accepted quotes.

is_underpriced flags a proposed quote well below the typical range, so the app can say
"You may be underpricing".
"""

import numpy as np

from ranking.models import AcceptedQuote, JobSize, PriceRange

MIN_QUOTES_FOR_RANGE = 8
LOCAL_QUOTES_FOR_LOCAL_ONLY = 12
LOW_PERCENTILE = 25
HIGH_PERCENTILE = 75
PRICE_STEP_RANDS = 10  # ranges are rounded to R10, like real quotes
UNDERPRICING_SHARE_OF_LOW = 0.8  # a quote under 80% of the range's low end is "well below"


def price_range(
    trade: str, size: JobSize, area: str, accepted_quotes: list[AcceptedQuote]
) -> PriceRange | None:
    """Returns the typical price range for a job, or None when there isn't enough data.

    Args:
        trade: the trade id, from data/glossary.json.
        size: "small", "medium" or "large".
        area: the suburb the job is in. Matching ignores letter case and spaces around it.
        accepted_quotes: accepted quotes, each with its job's trade, size and suburb.

    Returns:
        A PriceRange rounded to R10, where n_quotes counts every quote the range draws on
        (local plus any borrowed from other suburbs). None below MIN_QUOTES_FOR_RANGE.
    """
    matching_quotes = [
        quote for quote in accepted_quotes if quote.trade == trade and quote.size == size
    ]
    local_amounts = [q.amount_rands for q in matching_quotes if is_same_suburb(q.suburb, area)]
    wider_amounts = [q.amount_rands for q in matching_quotes if not is_same_suburb(q.suburb, area)]
    amounts, weights = combine_local_and_wider(local_amounts, wider_amounts)
    if len(amounts) < MIN_QUOTES_FOR_RANGE:
        return None
    return PriceRange(
        trade=trade,
        size=size,
        suburb=area,
        low_rands=round_to_price_step(calculate_percentile(amounts, weights, LOW_PERCENTILE)),
        high_rands=round_to_price_step(calculate_percentile(amounts, weights, HIGH_PERCENTILE)),
        n_quotes=len(amounts),
    )


def is_underpriced(amount_rands: int, typical_range: PriceRange | None) -> bool:
    """True if a proposed quote is well below the typical range (under 80% of its low end).

    Never true without a range: with too little data there is nothing to compare with.
    """
    if typical_range is None:
        return False
    return amount_rands < UNDERPRICING_SHARE_OF_LOW * typical_range.low_rands


def is_same_suburb(suburb: str, area: str) -> bool:
    """True if two suburb names match, ignoring letter case and surrounding spaces."""
    return suburb.strip().casefold() == area.strip().casefold()


def combine_local_and_wider(
    local_amounts: list[int], wider_amounts: list[int]
) -> tuple[list[int], list[float]]:
    """Returns the amounts to use and how much each counts.

    Local quotes count 1 each. When there are fewer than LOCAL_QUOTES_FOR_LOCAL_ONLY, the
    wider quotes fill in: together they count as the missing number of quotes, and each
    counts at most as much as a local quote.
    """
    missing_quote_count = LOCAL_QUOTES_FOR_LOCAL_ONLY - len(local_amounts)
    local_weights = [1.0] * len(local_amounts)
    if missing_quote_count <= 0 or not wider_amounts:
        return local_amounts, local_weights
    wider_weight = min(1.0, missing_quote_count / len(wider_amounts))
    return local_amounts + wider_amounts, local_weights + [wider_weight] * len(wider_amounts)


def calculate_percentile(amounts: list[int], weights: list[float], percentile: float) -> float:
    """Returns a weighted percentile of the amounts, interpolated between real amounts.

    Each amount sits at the middle of its own share of the total weight. With equal
    weights this is the usual percentile, and it never goes below the lowest amount or
    above the highest.
    """
    order = np.argsort(amounts, kind="stable")
    sorted_amounts = np.asarray(amounts, dtype=float)[order]
    sorted_weights = np.asarray(weights, dtype=float)[order]
    positions = (np.cumsum(sorted_weights) - sorted_weights / 2) / sorted_weights.sum()
    return float(np.interp(percentile / 100, positions, sorted_amounts))


def round_to_price_step(amount_rands: float) -> int:
    """Rounds an amount to the nearest R10."""
    return int(round(amount_rands / PRICE_STEP_RANDS) * PRICE_STEP_RANDS)
