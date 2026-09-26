"""price_range: the typical price for a job, worked out from accepted quotes only.

STUB (step 0): always None ("not enough data yet"). Step 5 returns the middle range
(25th to 75th percentile) of accepted quotes, leaning on wider trade-and-size data when
the suburb has few quotes, and still None below 8 quotes. It never invents a price.
"""

from ranking.models import AcceptedQuote, JobSize, PriceRange


def price_range(
    trade: str, size: JobSize, area: str, accepted_quotes: list[AcceptedQuote]
) -> PriceRange | None:
    """Returns the typical price range for a job, or None when there isn't enough data.

    Args:
        trade: the trade id, from data/glossary.json.
        size: "small", "medium" or "large".
        area: the suburb the job is in.
        accepted_quotes: accepted quotes, each with its job's trade, size and suburb.

    Returns:
        A PriceRange, or None when there are too few accepted quotes to say.
        STUB: always None.
    """
    return None
