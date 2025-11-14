from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from runway_radar.config import DATA_DIR, ensure_directories
from runway_radar.events import EventMeta, get_event_meta


def get_event_paths(event_id: str) -> Dict[str, Path]:
    """
    Compute and return key filesystem paths for a given event_id.

    Paths include raw and processed locations for images and CSVs.
    """
    raw_event_dir = DATA_DIR / "raw" / "events" / event_id
    processed_event_dir = DATA_DIR / "processed" / "events" / event_id

    paths: Dict[str, Path] = {
        "raw_event_dir": raw_event_dir,
        "raw_images_dir": raw_event_dir / "images",
        "raw_press_path": raw_event_dir / "press.csv",
        "raw_social_path": raw_event_dir / "social.csv",
        "processed_event_dir": processed_event_dir,
        "image_elements_path": processed_event_dir / "image_elements.csv",
        "text_mentions_path": processed_event_dir / "text_mentions.csv",
        "trend_scores_path": processed_event_dir / "trend_scores.csv",
    }

    return paths


def build_image_elements(event: EventMeta, paths: Dict[str, Path]) -> pd.DataFrame:
    """
    Build the image_elements table for a given event.

    For now, this creates an empty DataFrame with the expected columns
    and writes it to disk. Later this will call the image pipeline
    (detectors, palettes, features).
    """
    columns = [
        "image_id",
        "event_id",
        "look_number",
        "garment_categories",
        "skirt_length",
        "dominant_colours",
        "materials",
        "extra_tags",
    ]
    df = pd.DataFrame(columns=columns)
    df["event_id"] = event.event_id

    processed_dir = paths["processed_event_dir"]
    processed_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(paths["image_elements_path"], index=False)
    return df


def build_text_mentions(event: EventMeta, paths: Dict[str, Path]) -> pd.DataFrame:
    """
    Build the text_mentions table for a given event.

    For now, this creates an empty DataFrame with the expected columns
    and writes it to disk. Later this will call the text pipeline
    (loaders, preprocessing, sentiment, element extraction).
    """
    columns = [
        "mention_id",
        "event_id",
        "element",
        "element_type",
        "sentiment",
        "source",
        "timestamp",
        "extra_tags",
    ]
    df = pd.DataFrame(columns=columns)
    df["event_id"] = event.event_id

    processed_dir = paths["processed_event_dir"]
    processed_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(paths["text_mentions_path"], index=False)
    return df


def build_trend_scores(event: EventMeta, paths: Dict[str, Path]) -> pd.DataFrame:
    """
    Build the trend_scores table for a given event.

    For now, this creates an empty DataFrame with the expected columns
    and writes it to disk. Later this will combine image_elements and
    text_mentions and compute popularity indices.
    """
    columns = [
        "event_id",
        "element",
        "element_type",
        "image_share",
        "text_mentions",
        "avg_sentiment",
        "popularity_index",
    ]
    df = pd.DataFrame(columns=columns)
    df["event_id"] = event.event_id

    processed_dir = paths["processed_event_dir"]
    processed_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(paths["trend_scores_path"], index=False)
    return df


def run_event_pipeline(event_id: str) -> Optional[Dict[str, pd.DataFrame]]:
    """
    Orchestrate processing for a single event.

    Current behaviour:
    - Load event metadata from events.csv
    - Resolve raw and processed paths
    - Ensure high level data directories exist
    - Call stub builders for image_elements, text_mentions, trend_scores

    Returns
    -------
    dict or None
        A dictionary of DataFrames keyed by:
        - 'image_elements'
        - 'text_mentions'
        - 'trend_scores'

        Returns None if the event_id is not defined in events.csv.
    """
    ensure_directories()
    event = get_event_meta(event_id)
    if event is None:
        return None

    paths = get_event_paths(event_id)
    paths["processed_event_dir"].mkdir(parents=True, exist_ok=True)

    image_elements = build_image_elements(event, paths)
    text_mentions = build_text_mentions(event, paths)
    trend_scores = build_trend_scores(event, paths)

    return {
        "image_elements": image_elements,
        "text_mentions": text_mentions,
        "trend_scores": trend_scores,
    }
