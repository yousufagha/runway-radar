import re
from typing import List

import feedparser
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


FASHION_DOMAINS = [
    "vogue.com",
    "vogue.co.uk",
    "nowfashion.com",
    "harpersbazaar.com",
    "elle.com",
    "businessoffashion.com",
    "wwd.com",
    "guardian.com",
    "theguardian.com",
    "hypebeast.com",
    "highsnobiety.com",
    "nytimes.com",
    "cnn.com",
    "fashionmagazine.com",
]


def discover_news_links(query: str, max_links: int = 20) -> List[str]:
    """Use Google News RSS (no key) to find related links for an event name."""
    q = requests.utils.quote(query)
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(url)
        links: List[str] = []
        for e in feed.entries[: max_links * 2]:
            href = e.get("link") or ""
            if any(d in href for d in FASHION_DOMAINS):
                links.append(href)
            if len(links) >= max_links:
                break
        return links
    except Exception:
        return []


def discover_reddit_links(query: str, max_links: int = 15) -> List[str]:
    """Use Reddit search json (no key) to find external links related to query."""
    import json
    import time

    headers = {"User-Agent": UA}
    r = requests.get(
        "https://www.reddit.com/search.json",
        params={"q": query, "t": "all", "sort": "relevance", "limit": max(25, max_links)},
        headers=headers,
        timeout=12,
    )
    if r.status_code >= 400:
        return []
    try:
        data = r.json()
    except Exception:
        try:
            data = json.loads(r.text)
        except Exception:
            return []
    links = []
    for c in data.get("data", {}).get("children", []):
        d = c.get("data", {})
        url = d.get("url") or ""
        if any(dom in url for dom in FASHION_DOMAINS) and url not in links:
            links.append(url)
        if len(links) >= max_links:
            break
    time.sleep(0.4)
    return links


def generate_previous_event_names(event_name: str, count: int = 3) -> List[str]:
    """Very lightweight parser to create previous-event variations.

    Examples: "Chanel Couture Fall-Winter 2025 Paris" ->
    ["Chanel Couture Spring-Summer 2025", "Chanel Couture Fall-Winter 2024", "Chanel Couture Spring-Summer 2024"]
    """
    if not event_name:
        return []
    brand_match = re.match(r"([A-Za-zÀ-ÿ'\- ]+)", event_name)
    brand = brand_match.group(1).strip() if brand_match else event_name
    # detect couture/ready-to-wear
    typ = "Couture" if re.search(r"couture", event_name, re.I) else "Ready-To-Wear"
    # detect season and year
    year_match = re.search(r"(20\d{2})", event_name)
    year = int(year_match.group(1)) if year_match else None
    is_fw = bool(re.search(r"fall|autumn|winter", event_name, re.I))
    names: List[str] = []
    def make(y, fw):
        season = "Fall-Winter" if fw else "Spring-Summer"
        return f"{brand} {typ} {season} {y}"
    if year:
        names.append(make(year, not is_fw))
        names.append(make(year - 1, is_fw))
        names.append(make(year - 1, not is_fw))
    return names

