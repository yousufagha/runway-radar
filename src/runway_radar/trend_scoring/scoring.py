"""Compute popularity scores for trend elements."""
import math


def compute_popularity_index(sentiment: float, mentions: int) -> float:
    """
    PopularityIndex = sentiment × log(1 + mentions).
    """
    safe_mentions = max(0, int(mentions))
    return float(sentiment) * math.log1p(safe_mentions)
