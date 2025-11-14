from typing import List

import pandas as pd


def generate_colour_insights(
    trend_df: pd.DataFrame,
    events_df: pd.DataFrame,
    min_share: float = 0.3,
) -> List[str]:
    """
    Generate simple English insights for colours within individual events.

    For each row where element_type == 'colour' and image_share >= min_share,
    produce a sentence of the form:

    "{colour} is in, appearing in {share_pct}% of looks at {brand} {season_name} {year}."

    Expected columns in trend_df:
    - event_id
    - element
    - element_type
    - image_share

    Expected columns in events_df:
    - event_id
    - brand
    - season_name
    - year
    """
    if trend_df.empty or events_df.empty:
        return []

    merged = trend_df.merge(events_df, on="event_id", how="inner")

    mask = (merged["element_type"] == "colour") & (
        merged["image_share"].astype(float) >= float(min_share)
    )
    candidates = merged.loc[mask].copy()

    insights: List[str] = []
    for _, row in candidates.iterrows():
        colour = str(row["element"])
        share_pct = int(round(float(row["image_share"]) * 100))
        brand = str(row["brand"])
        season_name = str(row["season_name"])
        year = int(row["year"])

        sentence = (
            f"{colour.capitalize()} is in, appearing in {share_pct}% of looks at "
            f"{brand} {season_name} {year}."
        )
        insights.append(sentence)

    return insights


def generate_garment_insights(
    trend_df: pd.DataFrame,
    events_df: pd.DataFrame,
    min_share: float = 0.3,
) -> List[str]:
    """
    Generate simple English insights for garments and silhouettes.

    For each row where element_type == 'garment' and image_share >= min_share,
    produce a sentence of the form:

    "{element} leads the runway at {brand} {season_name} {year}, making up {share_pct}% of looks."

    This is a simple starting template which can be refined later.
    """
    if trend_df.empty or events_df.empty:
        return []

    merged = trend_df.merge(events_df, on="event_id", how="inner")

    mask = (merged["element_type"] == "garment") & (
        merged["image_share"].astype(float) >= float(min_share)
    )
    candidates = merged.loc[mask].copy()

    insights: List[str] = []
    for _, row in candidates.iterrows():
        element = str(row["element"])
        share_pct = int(round(float(row["image_share"]) * 100))
        brand = str(row["brand"])
        season_name = str(row["season_name"])
        year = int(row["year"])

        sentence = (
            f"{element.capitalize()} leads the runway at {brand} {season_name} {year}, "
            f"making up {share_pct}% of looks."
        )
        insights.append(sentence)

    return insights
