"""Aggregate mentions and sentiment by trend element and over time."""
from typing import Optional

import pandas as pd


def aggregate_by_element(
    df: pd.DataFrame,
    element_col: str,
    time_col: str,
    sentiment_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Group mentions by trend element and time.

    Intended to compute mention counts, average sentiment, and other metrics
    for each element-time bucket.
    """
    _ = (df, element_col, time_col, sentiment_col)
    return pd.DataFrame()
