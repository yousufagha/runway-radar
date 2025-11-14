"""Sentiment analysis utilities leveraging VADER and transformer models."""
from typing import Any

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def load_vader() -> SentimentIntensityAnalyzer:
    """Initialise and return the VADER sentiment analyser."""
    return SentimentIntensityAnalyzer()


def score_sentiment_vader(text: str) -> float:
    """Return the VADER compound sentiment score for the provided text."""
    analyzer = load_vader()
    return analyzer.polarity_scores(text)["compound"]


def score_sentiment_transformer(text: str, model: Any = None, tokenizer: Any = None) -> float:
    """
    Placeholder for transformer-based sentiment scoring.

    Future implementation should tokenize the input, run model inference,
    and return a normalised sentiment score.
    """
    _ = (text, model, tokenizer)
    return 0.0
