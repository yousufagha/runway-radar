import sqlite3
from typing import Optional, List, Any
from contextlib import closing

import pandas as pd

from .utils import now_iso


def _connect(db_path: str):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    with closing(_connect(db_path)) as conn:
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                uploaded_at TEXT DEFAULT (datetime('now')),
                source TEXT,
                source_url TEXT,
                image_url TEXT,
                event TEXT
            );

            CREATE TABLE IF NOT EXISTS image_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id INTEGER NOT NULL,
                tag_type TEXT NOT NULL,
                tag_value TEXT NOT NULL,
                confidence REAL,
                source TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(image_id) REFERENCES images(id)
            );

            CREATE TABLE IF NOT EXISTS texts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                source TEXT,
                created_at TEXT,
                sentiment REAL,
                event TEXT
            );

            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text_id INTEGER NOT NULL,
                entity_type TEXT NOT NULL,
                entity_value TEXT NOT NULL,
                confidence REAL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(text_id) REFERENCES texts(id)
            );
            """
        )
        conn.commit()
        _migrate_images_table(conn)
        _migrate_texts_table(conn)
        _backfill_dates(conn)


def _migrate_images_table(conn: sqlite3.Connection) -> None:
    # Ensure columns exist for source metadata
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(images)")
    cols = {row[1] for row in cur.fetchall()}  # row: cid, name, type, notnull, dflt_value, pk
    to_add = []
    if "source" not in cols:
        to_add.append(("source", "TEXT"))
    if "source_url" not in cols:
        to_add.append(("source_url", "TEXT"))
    if "image_url" not in cols:
        to_add.append(("image_url", "TEXT"))
    if "event" not in cols:
        to_add.append(("event", "TEXT"))
    for name, typ in to_add:
        cur.execute(f"ALTER TABLE images ADD COLUMN {name} {typ}")
    # Create index to help dedup on image_url
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_images_image_url ON images(image_url)")
    conn.commit()


def _migrate_texts_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(texts)")
    cols = {row[1] for row in cur.fetchall()}
    if "event" not in cols:
        cur.execute("ALTER TABLE texts ADD COLUMN event TEXT")
        conn.commit()


def _backfill_dates(conn: sqlite3.Connection) -> None:
    try:
        cur = conn.cursor()
        # Backfill missing created_at in image_tags from parent image uploaded_at
        cur.execute(
            """
            UPDATE image_tags
            SET created_at = (
                SELECT uploaded_at FROM images WHERE images.id = image_tags.image_id
            )
            WHERE (created_at IS NULL OR created_at = '')
        """
        )
        conn.commit()
    except Exception:
        pass


def insert_image(db_path: str, filename: str) -> int:
    with closing(_connect(db_path)) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO images (filename, uploaded_at) VALUES (?, ?)", (filename, now_iso()))
        conn.commit()
        return int(cur.lastrowid)


def insert_image_ex(
    db_path: str,
    filename: str,
    source: Optional[str] = None,
    source_url: Optional[str] = None,
    image_url: Optional[str] = None,
    event: Optional[str] = None,
) -> int:
    with closing(_connect(db_path)) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO images (filename, uploaded_at, source, source_url, image_url, event) VALUES (?, ?, ?, ?, ?, ?)",
            (filename, now_iso(), source, source_url, image_url, event),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_image_by_image_url(db_path: str, image_url: str) -> Optional[int]:
    if not image_url:
        return None
    with closing(_connect(db_path)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM images WHERE image_url = ?", (image_url,))
        row = cur.fetchone()
        return int(row[0]) if row else None


def insert_image_tag(
    db_path: str,
    image_id: int,
    tag_type: str,
    tag_value: str,
    confidence: Optional[float] = None,
    source: Optional[str] = None,
    created_at: Optional[str] = None,
) -> int:
    with closing(_connect(db_path)) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO image_tags (image_id, tag_type, tag_value, confidence, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (image_id, tag_type, tag_value, confidence, source, created_at or now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)


def insert_text(
    db_path: str,
    text: str,
    source: Optional[str] = None,
    created_at: Optional[str] = None,
    sentiment: Optional[float] = None,
    event: Optional[str] = None,
) -> int:
    if not created_at:
        created_at = now_iso()
    with closing(_connect(db_path)) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO texts (text, source, created_at, sentiment, event) VALUES (?, ?, ?, ?, ?)",
            (text, source, created_at, sentiment, event),
        )
        conn.commit()
        return int(cur.lastrowid)


def insert_entity(
    db_path: str,
    text_id: int,
    entity_type: str,
    entity_value: str,
    confidence: Optional[float] = None,
) -> int:
    with closing(_connect(db_path)) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO entities (text_id, entity_type, entity_value, confidence, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (text_id, entity_type, entity_value, confidence, now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)


def df_from_query(db_path: str, query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
    params = params or []
    with closing(_connect(db_path)) as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df
