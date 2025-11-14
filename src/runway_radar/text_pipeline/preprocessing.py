"""Simple text cleaning utilities."""
import re


def basic_clean(text: str) -> str:
    """
    Lowercase, strip URLs, collapse whitespace, and remove leading/trailing space.
    """
    no_urls = re.sub(r"http\S+", "", text)
    cleaned = re.sub(r"\s+", " ", no_urls.lower()).strip()
    return cleaned
