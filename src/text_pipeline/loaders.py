"""Load raw fashion-related text corpora from CSV, JSON, or API dumps."""
from pathlib import Path

import pandas as pd


def load_text_corpus(path: Path) -> pd.DataFrame:
    """
    Placeholder loader returning an empty corpus schema.

    Future implementations should inspect file suffixes and read CSV/JSON data,
    preserving columns: id, text, source, timestamp.
    """
    _ = path
    return pd.DataFrame(columns=["id", "text", "source", "timestamp"])
