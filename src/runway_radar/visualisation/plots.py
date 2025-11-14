"""Chart helpers for Runway Radar."""
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd


def plot_bar_ranking(
    df: pd.DataFrame,
    category_col: str,
    value_col: str,
    top_n: int = 10,
    title: Optional[str] = None,
) -> None:
    """
    Plot a horizontal bar chart for ranked categories.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing categories and values.
    category_col : str
        Column name of the category labels.
    value_col : str
        Column name of the scores or counts.
    top_n : int
        Number of top entries to display.
    title : Optional[str]
        Optional plot title.
    """
    ranked = df.sort_values(value_col, ascending=False).head(top_n)
    plt.figure(figsize=(8, 6))
    plt.barh(ranked[category_col], ranked[value_col])
    plt.gca().invert_yaxis()
    plt.xlabel(value_col)
    if title:
        plt.title(title)
    plt.tight_layout()
    plt.show()
