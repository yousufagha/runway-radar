"""Ranking helpers for garments, colours, designers, and other trend entities."""
import pandas as pd


def rank_elements(df: pd.DataFrame, score_col: str, ascending: bool = False) -> pd.DataFrame:
    """
    Sort elements by a score column.

    Returns the sorted DataFrame and adds a rank column (1-based).
    """
    ranked = df.sort_values(score_col, ascending=ascending).reset_index(drop=True).copy()
    ranked["rank"] = ranked.index + 1
    return ranked
