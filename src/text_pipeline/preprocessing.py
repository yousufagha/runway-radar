"""Basic text cleaning and normalisation helpers."""
import re


def basic_clean(text: str) -> str:
    """
    Lower-case text and remove extra whitespace.

    Future extensions can include emoji handling, stop-word removal, or lemmatisation.
    """
    cleaned = re.sub(r"\s+", " ", text.lower()).strip()
    return cleaned
