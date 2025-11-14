"""Sentiment helpers for Runway Radar."""
from typing import Optional

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyser: Optional[SentimentIntensityAnalyzer] = None


def load_vader() -> SentimentIntensityAnalyzer:
    """Lazily load and cache the VADER sentiment analyser."""
    global _analyser
    if _analyser is None:
        _analyser = SentimentIntensityAnalyzer()
    return _analyser


def score_sentiment_vader(text: str) -> float:
    """Return the compound VADER score for a single text."""
    analyser = load_vader()
    return analyser.polarity_scores(text)["compound"]
