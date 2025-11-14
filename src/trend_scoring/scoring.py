"""Compute popularity scores and adoption metrics."""
import math


def compute_popularity_index(sentiment: float, mentions: int) -> float:
    """
    Sentiment-weighted popularity: sentiment × log(1 + mentions).

    Handles zero mentions gracefully via log1p.
    """
    return sentiment * math.log1p(max(mentions, 0))
