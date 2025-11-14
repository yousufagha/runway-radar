from typing import List, Optional

import pandas as pd

from . import storage
from .utils import get_time_bounds


def _text_entity_agg_query(entity_type: str, timeframe: str, only_entities: Optional[List[str]], event: Optional[str] = None):
    start, end = get_time_bounds(timeframe)
    params = []
    where = ["e.entity_type = ?"]
    params.append(entity_type)
    if start:
        where.append("t.created_at >= ?")
        params.append(start)
    if end:
        where.append("t.created_at <= ?")
        params.append(end)
    if event:
        where.append("t.event = ?"); params.append(event)
    if only_entities:
        placeholders = ",".join(["?"] * len(only_entities))
        where.append(f"e.entity_value IN ({placeholders})")
        params.extend(only_entities)
    sql = f"""
        SELECT e.entity_value, COUNT(*) as freq, AVG(COALESCE(t.sentiment, 0)) as avg_sentiment
        FROM entities e
        JOIN texts t ON e.text_id = t.id
        WHERE {' AND '.join(where)}
        GROUP BY e.entity_value
    """
    return sql, params


def _image_tag_agg_query(tag_type: str, timeframe: str, only_entities: Optional[List[str]], event: Optional[str] = None):
    start, end = get_time_bounds(timeframe)
    params = []
    where = ["tag_type = ?"]
    params.append(tag_type)
    if start:
        where.append("created_at >= ?")
        params.append(start)
    if end:
        where.append("created_at <= ?")
        params.append(end)
    if event:
        where.append("image_id IN (SELECT id FROM images WHERE event = ?)"); params.append(event)
    if only_entities:
        placeholders = ",".join(["?"] * len(only_entities))
        where.append(f"tag_value IN ({placeholders})")
        params.extend(only_entities)
    sql = f"""
        SELECT tag_value as entity_value, COUNT(*) as freq
        FROM image_tags
        WHERE {' AND '.join(where)}
        GROUP BY tag_value
    """
    return sql, params


def aggregate_popularity(db_path: str, entity_type: str, timeframe: str = "all", only_entities: Optional[List[str]] = None, event: Optional[str] = None) -> pd.DataFrame:
    # Text-based entities with sentiment
    sql_text, params_text = _text_entity_agg_query(entity_type, timeframe, only_entities, event)
    df_text = storage.df_from_query(db_path, sql_text, params_text)
    if df_text.empty:
        df_text = pd.DataFrame(columns=["entity_value", "freq", "avg_sentiment"]).astype({"freq": int, "avg_sentiment": float})

    # Image tags (no sentiment; assume neutral positive 1.0)
    sql_img, params_img = _image_tag_agg_query(entity_type, timeframe, only_entities, event)
    df_img = storage.df_from_query(db_path, sql_img, params_img)
    if df_img.empty:
        df_img = pd.DataFrame(columns=["entity_value", "freq"]).astype({"freq": int})
    df_img["avg_sentiment"] = 1.0

    # Merge on entity_value
    merged = pd.merge(df_text, df_img, on="entity_value", how="outer", suffixes=("_text", "_img")).fillna(0)
    # Compute totals
    merged["freq_total"] = merged.get("freq_text", 0) + merged.get("freq_img", 0)
    # Weighted sentiment by frequency parts; if total zero, set to 0
    def _weighted(row):
        ft = row.get("freq_text", 0)
        fi = row.get("freq_img", 0)
        total = ft + fi
        if total <= 0:
            return 0.0
        at = row.get("avg_sentiment_text", 0)
        ai = 1.0  # image sentiment assumed neutral-positive
        return (at * ft + ai * fi) / total

    merged["avg_sentiment_total"] = merged.apply(_weighted, axis=1)
    merged["popularity_score"] = merged["freq_total"] * merged["avg_sentiment_total"]

    # Provide standardized columns
    out = merged[["entity_value", "freq_total", "avg_sentiment_total", "popularity_score"]].rename(columns={
        "freq_total": "freq",
        "avg_sentiment_total": "avg_sentiment",
    })
    out = out.sort_values(by=["popularity_score", "freq"], ascending=[False, False])
    out.reset_index(drop=True, inplace=True)
    return out


def timeseries_popularity(
    db_path: str,
    entity_type: str,
    timeframe: str = "all",
    only_entities: Optional[List[str]] = None,
    top_n: int = 5,
    event: Optional[str] = None,
) -> pd.DataFrame:
    start, end = get_time_bounds(timeframe)

    # Text-based daily aggregations
    params_t: List = [entity_type]
    where_t = ["e.entity_type = ?"]
    if start:
        where_t.append("t.created_at >= ?"); params_t.append(start)
    if end:
        where_t.append("t.created_at <= ?"); params_t.append(end)
    if event:
        where_t.append("t.event = ?"); params_t.append(event)
    if only_entities:
        placeholders = ",".join(["?"] * len(only_entities))
        where_t.append(f"e.entity_value IN ({placeholders})"); params_t.extend(only_entities)
    sql_t = f"""
        SELECT substr(t.created_at,1,10) AS day, e.entity_value, COUNT(*) AS freq, AVG(COALESCE(t.sentiment,0)) AS avg_sentiment
        FROM entities e
        JOIN texts t ON e.text_id = t.id
        WHERE {' AND '.join(where_t)}
        GROUP BY day, e.entity_value
    """
    df_t = storage.df_from_query(db_path, sql_t, params_t)
    if df_t.empty:
        df_t = pd.DataFrame(columns=["day", "entity_value", "freq", "avg_sentiment"]).astype({"freq": int, "avg_sentiment": float})

    # Image tag daily aggregations
    params_i: List = [entity_type]
    where_i = ["tag_type = ?"]
    if start:
        where_i.append("created_at >= ?"); params_i.append(start)
    if end:
        where_i.append("created_at <= ?"); params_i.append(end)
    if event:
        where_i.append("t1.image_id IN (SELECT id FROM images WHERE event = ?)"); params_i.append(event)
    if only_entities:
        placeholders = ",".join(["?"] * len(only_entities))
        where_i.append(f"tag_value IN ({placeholders})"); params_i.extend(only_entities)
    sql_i = f"""
        SELECT substr(created_at,1,10) AS day, tag_value AS entity_value, COUNT(*) AS freq
        FROM image_tags
        WHERE {' AND '.join(where_i)}
        GROUP BY day, tag_value
    """
    df_i = storage.df_from_query(db_path, sql_i, params_i)
    if df_i.empty:
        df_i = pd.DataFrame(columns=["day", "entity_value", "freq"]).astype({"freq": int})
    df_i["avg_sentiment"] = 1.0

    merged = pd.merge(df_t, df_i, on=["day", "entity_value"], how="outer", suffixes=("_text", "_img")).fillna(0)
    merged["freq_total"] = merged.get("freq_text", 0) + merged.get("freq_img", 0)

    def _weighted(row):
        ft = row.get("freq_text", 0)
        fi = row.get("freq_img", 0)
        total = ft + fi
        if total <= 0:
            return 0.0
        at = row.get("avg_sentiment_text", 0)
        ai = 1.0
        return (at * ft + ai * fi) / total

    merged["avg_sentiment_total"] = merged.apply(_weighted, axis=1)
    merged["popularity_score"] = merged["freq_total"] * merged["avg_sentiment_total"]

    # keep top N entities across the whole range
    totals = merged.groupby("entity_value")["freq_total"].sum().sort_values(ascending=False)
    top_entities = set(totals.head(max(1, int(top_n))).index)
    out = merged[merged["entity_value"].isin(top_entities)].copy()
    out = out.rename(columns={"day": "date", "freq_total": "freq", "avg_sentiment_total": "avg_sentiment"})
    out = out[["date", "entity_value", "freq", "avg_sentiment", "popularity_score"]].sort_values(["date", "entity_value"]).reset_index(drop=True)
    return out


def cooccurrence(
    db_path: str,
    type_a: str,
    type_b: str,
    timeframe: str = "all",
    top_k: int = 20,
    event: Optional[str] = None,
) -> pd.DataFrame:
    start, end = get_time_bounds(timeframe)

    # Text co-occurrence
    params_t: List = [type_a, type_b]
    where_t = ["e1.entity_type = ?", "e2.entity_type = ?", "e1.text_id = e2.text_id"]
    if start:
        where_t.append("t.created_at >= ?"); params_t.append(start)
    if end:
        where_t.append("t.created_at <= ?"); params_t.append(end)
    if event:
        where_t.append("t.event = ?"); params_t.append(event)
    sql_t = f"""
        SELECT e1.entity_value AS a, e2.entity_value AS b, COUNT(DISTINCT e1.text_id) AS freq
        FROM entities e1
        JOIN entities e2 ON e1.text_id = e2.text_id
        JOIN texts t ON t.id = e1.text_id
        WHERE {' AND '.join(where_t)} AND e1.entity_value != e2.entity_value
        GROUP BY a, b
    """
    df_t = storage.df_from_query(db_path, sql_t, params_t)

    # Image tag co-occurrence
    params_i: List = [type_a, type_b]
    where_i = ["t1.tag_type = ?", "t2.tag_type = ?", "t1.image_id = t2.image_id"]
    if start:
        where_i.append("t1.created_at >= ?"); params_i.append(start)
    if end:
        where_i.append("t1.created_at <= ?"); params_i.append(end)
    if event:
        where_i.append("t1.image_id IN (SELECT id FROM images WHERE event = ?)"); params_i.append(event)
    sql_i = f"""
        SELECT t1.tag_value AS a, t2.tag_value AS b, COUNT(DISTINCT t1.image_id) AS freq
        FROM image_tags t1
        JOIN image_tags t2 ON t1.image_id = t2.image_id
        WHERE {' AND '.join(where_i)} AND t1.tag_value != t2.tag_value
        GROUP BY a, b
    """
    df_i = storage.df_from_query(db_path, sql_i, params_i)

    # Merge and sum
    frames = []
    if df_t is not None and not df_t.empty:
        frames.append(df_t)
    if df_i is not None and not df_i.empty:
        frames.append(df_i)
    if not frames:
        return pd.DataFrame(columns=["a", "b", "freq"]) 
    allpairs = pd.concat(frames, ignore_index=True)
    agg = allpairs.groupby(["a", "b"]).agg({"freq": "sum"}).reset_index()
    agg = agg.sort_values("freq", ascending=False).head(max(1, int(top_k)))
    return agg


def sources_breakdown(db_path: str) -> pd.DataFrame:
    # Images by source
    sql_img = "SELECT COALESCE(source,'unknown') AS source, COUNT(*) AS count FROM images GROUP BY source"
    df_img = storage.df_from_query(db_path, sql_img, [])
    df_img["type"] = "images"
    # Texts by source
    sql_txt = "SELECT COALESCE(source,'unknown') AS source, COUNT(*) AS count FROM texts GROUP BY source"
    df_txt = storage.df_from_query(db_path, sql_txt, [])
    df_txt["type"] = "texts"
    out = pd.concat([df_img, df_txt], ignore_index=True)
    return out
