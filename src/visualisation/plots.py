"""Matplotlib plot helpers for trend lines and rankings."""
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd


def plot_trend_lines(df: pd.DataFrame, x_col: str, y_col: str, group_col: Optional[str] = None) -> None:
    """
    Plot sentiment or mention trajectories over time.

    Placeholder implementation uses simple matplotlib line plots.
    """
    plt.figure(figsize=(10, 5))
    if group_col:
        for key, group in df.groupby(group_col):
            plt.plot(group[x_col], group[y_col], label=str(key))
        plt.legend()
    else:
        plt.plot(df[x_col], df[y_col])
    plt.xlabel(x_col)
    plt.ylabel(y_col)
    plt.tight_layout()


def plot_bar_ranking(df: pd.DataFrame, category_col: str, value_col: str, top_n: int = 10) -> None:
    """Plot top-ranked categories as a horizontal bar chart."""
    top_df = df.nlargest(top_n, value_col)
    plt.figure(figsize=(8, 6))
    plt.barh(top_df[category_col], top_df[value_col])
    plt.xlabel(value_col)
    plt.ylabel(category_col)
    plt.tight_layout()
