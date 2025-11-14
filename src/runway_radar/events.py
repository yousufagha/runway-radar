from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from runway_radar.config import DATA_DIR


@dataclass
class EventMeta:
    """
    Metadata for a single fashion event.

    This captures season, year, city and other information so that
    downstream analyses can aggregate by season, city or brand.
    """

    event_id: str
    brand: str
    season_code: str
    season_name: str
    year: int
    city: str
    week: str
    segment: str
    runway_date: str
    notes: str = ""


def get_events_meta_path() -> Path:
    """
    Return the full path to the events metadata CSV file
    under the data/meta directory.
    """
    return DATA_DIR / "meta" / "events.csv"


def load_events_meta(path: Optional[Path] = None) -> pd.DataFrame:
    """
    Load the events metadata as a DataFrame.

    If the file does not exist, return an empty DataFrame with the
    columns defined by EventMeta.
    """
    if path is None:
        path = get_events_meta_path()

    columns = [
        "event_id",
        "brand",
        "season_code",
        "season_name",
        "year",
        "city",
        "week",
        "segment",
        "runway_date",
        "notes",
    ]

    if not path.exists():
        return pd.DataFrame(columns=columns)

    df = pd.read_csv(path)
    # Ensure columns exist in the expected order, but keep any extras
    for col in columns:
        if col not in df.columns:
            df[col] = "" if col != "year" else 0
    return df[columns]


def get_event_meta(event_id: str) -> Optional[EventMeta]:
    """
    Return EventMeta for a given event_id, or None if not found.
    """
    df = load_events_meta()
    if df.empty:
        return None

    rows = df.loc[df["event_id"] == event_id]
    if rows.empty:
        return None

    row = rows.iloc[0]

    return EventMeta(
        event_id=str(row["event_id"]),
        brand=str(row["brand"]),
        season_code=str(row["season_code"]),
        season_name=str(row["season_name"]),
        year=int(row["year"]),
        city=str(row["city"]),
        week=str(row["week"]),
        segment=str(row["segment"]),
        runway_date=str(row["runway_date"]),
        notes=str(row.get("notes", "")),
    )
