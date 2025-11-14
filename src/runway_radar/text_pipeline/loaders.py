"""Load raw text data for the text pipeline."""
from pathlib import Path

import pandas as pd


def load_text_corpus(path: Path) -> pd.DataFrame:
    """Load a CSV or return an empty corpus schema if missing."""
    if not path.exists():
        return pd.DataFrame(columns=["id", "text", "source", "timestamp"])
    return pd.read_csv(path)
