import os
import io
import re
import hashlib
from typing import List, Optional, Dict, Any, Tuple

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import feedparser

from . import storage, vision, llm, nlp
from .utils import ensure_dir
import pandas as pd


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def fetch_html(url: str, timeout: int = 12) -> Tuple[Optional[str], Optional[str]]:
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
        if resp.status_code >= 400:
            return None, None
        return resp.text, resp.url
    except Exception:
        return None, None


def _is_image_url(u: str) -> bool:
    return bool(re.search(r"\.(jpg|jpeg|png|webp)(\?.*)?$", u, re.IGNORECASE))


def extract_image_candidates(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    cands: List[str] = []
    # meta tags
    for prop in ["og:image", "twitter:image", "twitter:image:src"]:
        tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            cands.append(urljoin(base_url, tag["content"]))
    # link rel image_src
    link = soup.find("link", attrs={"rel": ["image_src", "thumbnail"]})
    if link and link.get("href"):
        cands.append(urljoin(base_url, link["href"]))
    # all images
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-original")
        if not src:
            continue
        absu = urljoin(base_url, src)
        if _is_image_url(absu):
            cands.append(absu)
    # de-duplicate, preserve order
    seen = set()
    uniq = []
    for u in cands:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def extract_published_date(html: str) -> Optional[str]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        meta_keys = [
            ("meta", {"property": "article:published_time"}),
            ("meta", {"name": "article:published_time"}),
            ("meta", {"name": "pubdate"}),
            ("meta", {"itemprop": "datePublished"}),
            ("meta", {"property": "og:updated_time"}),
        ]
        for tag_name, attrs in meta_keys:
            tag = soup.find(tag_name, attrs=attrs)
            if tag and tag.get("content"):
                try:
                    return pd.to_datetime(tag["content"]).isoformat()
                except Exception:
                    pass
        t = soup.find("time")
        if t and t.get("datetime"):
            try:
                return pd.to_datetime(t["datetime"]).isoformat()
            except Exception:
                pass
    except Exception:
        return None
    return None


def extract_article_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Prefer <article> text
    parts: List[str] = []
    art = soup.find("article")
    if art:
        for p in art.find_all("p"):
            txt = (p.get_text(" ") or "").strip()
            if len(txt) > 30:
                parts.append(txt)
    else:
        # Fallback: grab first meaningful paragraphs
        for p in soup.find_all("p")[:20]:
            txt = (p.get_text(" ") or "").strip()
            if len(txt) > 50:
                parts.append(txt)
    text = "\n".join(parts)
    return text[:8000]


def choose_best_image(urls: List[str]) -> Optional[str]:
    if not urls:
        return None
    # Score by runway/fashion keywords, longer path, and likely full-size paths
    KEYWORDS = ["runway", "catwalk", "collection", "backstage", "model", "look", "fashion", "show"]
    def score(u: str) -> int:
        path = urlparse(u).path.lower()
        s = 0
        for kw in KEYWORDS:
            if kw in path:
                s += 10
        if "/thumb" in path or "/small" in path or "thumbnail" in path or "/mini" in path:
            s -= 5
        s += min(len(path) // 10, 10)
        return s
    urls_sorted = sorted(urls, key=score, reverse=True)
    return urls_sorted[0]


def download_image(image_url: str, timeout: int = 20) -> Optional[bytes]:
    try:
        resp = requests.get(image_url, headers={"User-Agent": UA}, timeout=timeout, stream=True)
        if resp.status_code >= 400:
            return None
        content_type = resp.headers.get("Content-Type", "").lower()
        if not any(ct in content_type for ct in ["image/jpeg", "image/png", "image/webp", "image/jpg"]):
            # attempt anyway
            data = resp.content
        else:
            data = resp.content
        # Limit to 25MB
        if len(data) > 25 * 1024 * 1024:
            return None
        return data
    except Exception:
        return None


def _safe_filename(url: str, suffix: str = "") -> str:
    parsed = urlparse(url)
    name = os.path.basename(parsed.path) or "image"
    if not _is_image_url(name):
        # add guessed extension
        ext = ".jpg"
        name = name + ext
    if suffix:
        root, ext = os.path.splitext(name)
        name = f"{root}_{suffix}{ext}"
    # shorten overly long names
    if len(name) > 80:
        h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
        root, ext = os.path.splitext(name)
        name = f"{root[:40]}_{h}{ext}"
    return name


def ingest_from_url(
    db_path: str,
    save_dir: str,
    page_url: str,
    source_type: str = "magazine",
    source_name: Optional[str] = None,
    known_date: Optional[str] = None,
    event_name: Optional[str] = None,
) -> Dict[str, Any]:
    html, final_url = fetch_html(page_url)
    if not html:
        return {"ok": False, "error": "failed_html", "page_url": page_url}
    base_url = final_url or page_url
    candidates = extract_image_candidates(html, base_url)
    best = choose_best_image(candidates)
    if not best:
        return {"ok": False, "error": "no_image_found", "page_url": page_url}

    # dedup by image_url
    existing = storage.get_image_by_image_url(db_path, best)
    if existing:
        return {"ok": True, "skipped": True, "image_id": existing, "image_url": best, "page_url": page_url}

    data = download_image(best)
    if not data:
        return {"ok": False, "error": "download_failed", "image_url": best, "page_url": page_url}

    ensure_dir(save_dir)
    fname = _safe_filename(best)
    fpath = os.path.join(save_dir, fname)
    with open(fpath, "wb") as f:
        f.write(data)

    image_id = storage.insert_image_ex(db_path, filename=fname, source=source_type or source_name, source_url=page_url, image_url=best, event=event_name)

    # Palette and vision analysis
    palette = vision.extract_palette(data, k=5)
    event_dt = known_date or extract_published_date(html)
    for color_hex in palette:
        storage.insert_image_tag(db_path, image_id, tag_type="color", tag_value=color_hex, confidence=0.9, source="palette", created_at=event_dt)

    try:
        analysis = llm.analyze_image(data)
    except Exception:
        analysis = {"garments": [], "colors": [], "styles": [], "designers": []}

    for g in analysis.get("garments", []) or []:
        storage.insert_image_tag(db_path, image_id, tag_type="garment", tag_value=str(g), confidence=0.7, source="vision", created_at=event_dt)
    for c in analysis.get("colors", []) or []:
        storage.insert_image_tag(db_path, image_id, tag_type="color", tag_value=str(c), confidence=0.7, source="vision", created_at=event_dt)
    for s in analysis.get("styles", []) or []:
        storage.insert_image_tag(db_path, image_id, tag_type="style", tag_value=str(s), confidence=0.6, source="vision", created_at=event_dt)
    for d in analysis.get("designers", []) or []:
        storage.insert_image_tag(db_path, image_id, tag_type="designer", tag_value=str(d), confidence=0.5, source="vision", created_at=event_dt)

    # Extract article text -> sentiment + entities
    text_content = extract_article_text(html)
    if text_content:
        sent = nlp.sentiment_score(text_content)
        text_id = storage.insert_text(db_path, text=text_content, source=source_type or "web", created_at=event_dt, sentiment=sent, event=event_name)
        try:
            entities = llm.extract_entities(text_content)
        except Exception:
            entities = []
        for ent in entities or []:
            etype = ent.get("type")
            val = ent.get("value")
            conf = ent.get("confidence", 0.6)
            if etype and val:
                storage.insert_entity(db_path, text_id=text_id, entity_type=str(etype), entity_value=str(val), confidence=float(conf))

    return {
        "ok": True,
        "image_id": image_id,
        "filename": fname,
        "image_url": best,
        "page_url": page_url,
        "palette": palette,
        "analysis": analysis,
        "sentiment": nlp.sentiment_score(text_content) if text_content else None,
    }


def ingest_from_rss(
    db_path: str,
    save_dir: str,
    feed_url: str,
    limit: Optional[int] = None,
    source_type: str = "magazine",
    event_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    try:
        feed = feedparser.parse(feed_url)
    except Exception:
        return [{"ok": False, "error": "rss_parse_failed", "feed_url": feed_url}]
    results: List[Dict[str, Any]] = []
    entries = feed.entries if (limit is None or limit <= 0) else feed.entries[:limit]
    for e in entries:
        # Try media content
        page_url = e.get("link")
        dt_iso = None
        for key in ("published", "updated", "created"):
            val = e.get(key)
            if val:
                try:
                    dt_iso = pd.to_datetime(val).isoformat()
                    break
                except Exception:
                    pass
        res = ingest_from_url(db_path, save_dir, page_url=page_url or feed_url, source_type=source_type, known_date=dt_iso, event_name=event_name)
        results.append(res)
    return results
