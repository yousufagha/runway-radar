import time
from typing import Dict, List, Tuple

import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def _reddit_search(term: str, timeframe: str = "week", limit: int = 50, pause: float = 0.5) -> Tuple[int, List[Dict]]:
    """Lightweight Reddit search without API key. Returns count of fetched items and samples.

    Notes:
    - This is best-effort and rate-limited; not all results are returned.
    - timeframe: 'week'|'month'|'all'
    """
    t = "all"
    if timeframe in ("week", "weekly"):
        t = "week"
    elif timeframe in ("month", "monthly"):
        t = "month"
    headers = {"User-Agent": UA}
    url = "https://www.reddit.com/search.json"
    params = {"q": term, "t": t, "limit": min(100, max(10, limit))}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
        children = data.get("data", {}).get("children", [])
        items = []
        for c in children:
            d = c.get("data", {})
            items.append({
                "title": d.get("title"),
                "url": "https://www.reddit.com" + d.get("permalink", ""),
                "subreddit": d.get("subreddit"),
                "score": d.get("score", 0),
            })
        time.sleep(pause)
        return len(items), items
    except Exception:
        return 0, []


def social_mentions_for_entities(entities: List[str], timeframe: str = "week") -> Dict[str, Dict]:
    """Compute rough social mentions per entity via Reddit search as a free, no-key proxy.

    Returns mapping: entity -> {count: int, samples: [...]}
    """
    out: Dict[str, Dict] = {}
    for e in entities:
        # Compose a fashion-focused query
        term = f"\"{e}\" (runway OR couture OR fashion)"
        count, samples = _reddit_search(term, timeframe=timeframe, limit=50)
        out[e] = {"count": int(count), "samples": samples[:5]}
    return out


def hype_index(internal_freq: Dict[str, int], social_mentions: Dict[str, int]) -> Dict[str, float]:
    """Blend internal frequency and social mentions into a simple hype score [0..100]."""
    max_f = max(internal_freq.values()) if internal_freq else 1
    max_s = max(social_mentions.values()) if social_mentions else 1
    scores: Dict[str, float] = {}
    for k in set(list(internal_freq.keys()) + list(social_mentions.keys())):
        nf = (internal_freq.get(k, 0) / max_f) if max_f else 0.0
        ns = (social_mentions.get(k, 0) / max_s) if max_s else 0.0
        score = (0.5 * nf + 0.5 * ns) * 100.0
        scores[k] = round(float(score), 2)
    return scores

