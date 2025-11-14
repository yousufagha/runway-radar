from functools import lru_cache
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except Exception:
    SentimentIntensityAnalyzer = None


@lru_cache(maxsize=1)
def _analyzer() -> SentimentIntensityAnalyzer:
    if SentimentIntensityAnalyzer is None:
        return None  # type: ignore
    return SentimentIntensityAnalyzer()


def sentiment_score(text: str) -> float:
    if not text:
        return 0.0
    analyzer = _analyzer()
    if analyzer is None:
        # Fallback neutral sentiment if VADER not installed
        return 0.0
    scores = analyzer.polarity_scores(text)
    return float(scores.get("compound", 0.0))
