import os
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple
import colorsys

try:
    from dotenv import load_dotenv as _load_dotenv
except Exception:
    _load_dotenv = None


def ensure_dir(path: str) -> None:
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def load_env() -> None:
    # Load from .env if present; tolerate missing python-dotenv
    if _load_dotenv:
        try:
            _load_dotenv(override=False)
        except Exception:
            pass


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def parse_json_safely(text: str, default):
    if not isinstance(text, str):
        return default
    # Strip code fences if present
    t = text.strip().strip("` ")
    # Try to find outermost JSON object
    if "{" in t and "}" in t:
        try:
            t = t[t.index("{"): t.rindex("}") + 1]
        except Exception:
            pass
    try:
        return json.loads(t)
    except Exception:
        return default


def get_time_bounds(timeframe: str) -> Tuple[Optional[str], Optional[str]]:
    timeframe = (timeframe or "all").lower()
    end = datetime.utcnow()
    start: Optional[datetime] = None
    if timeframe in ("week", "weekly", "this week"):
        start = end - timedelta(days=7)
    elif timeframe in ("month", "monthly", "this month"):
        start = end - timedelta(days=30)
    # 'all' -> no start bound
    start_str = start.isoformat() if start else None
    end_str = end.isoformat()
    return start_str, end_str


def to_hex(rgb):
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def _css3_name_map():
    try:
        import webcolors
        return webcolors.CSS3_HEX_TO_NAMES
    except Exception:
        # Minimal fallback palette
        return {
            "#000000": "black",
            "#ffffff": "white",
            "#ff0000": "red",
            "#00ff00": "lime",
            "#0000ff": "blue",
            "#ffff00": "yellow",
            "#ffa500": "orange",
            "#800080": "purple",
            "#ffc0cb": "pink",
            "#a52a2a": "brown",
            "#808080": "gray",
            "#008080": "teal",
            "#000080": "navy",
            "#ff00ff": "magenta",
            "#00ffff": "cyan",
            "#c0c0c0": "silver",
            "#f5deb3": "wheat",
            "#f5f5dc": "beige",
        }


def color_name_for(hex_value: str) -> str:
    """Return a friendly color name for a hex string; falls back to nearest CSS3 name.

    Example: "#1e3a8a" -> "navy" (approx)
    """
    if not isinstance(hex_value, str) or not hex_value.startswith("#"):
        return str(hex_value)
    hv = hex_value.lower()
    # normalize 3-digit hex
    if len(hv) == 4:
        hv = "#" + "".join([c * 2 for c in hv[1:]])
    cmap = _css3_name_map()
    # exact match
    if hv in cmap:
        return cmap[hv]
    # nearest by RGB distance
    try:
        import webcolors
        from math import sqrt

        def as_rgb(h):
            h = h.lstrip("#")
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        target = as_rgb(hv)
        best_name = None
        best_dist = 1e9
        for hx, name in cmap.items():
            rgb = as_rgb(hx)
            dist = sqrt(sum((a - b) ** 2 for a, b in zip(target, rgb)))
            if dist < best_dist:
                best_dist = dist
                best_name = name
        return best_name or hv
    except Exception:
        # simple fallback: rough buckets
        try:
            r = int(hv[1:3], 16); g = int(hv[3:5], 16); b = int(hv[5:7], 16)
            if r > 200 and g > 200 and b > 200:
                return "white"
            if r < 40 and g < 40 and b < 40:
                return "black"
            if r > g and r > b:
                return "red"
            if g > r and g > b:
                return "green"
            if b > r and b > g:
                return "blue"
            return "gray"
        except Exception:
            return hv


def _rich_hue_name(h: float, s: float, l: float) -> str:
    """Map HSL to a richer base color family name."""
    # h in [0, 360)
    if h < 12 or h >= 348:
        # Deep reds
        if l < 0.22:
            return "burgundy"
        if l < 0.32:
            return "maroon"
        if s > 0.6:
            return "crimson"
        return "red"
    if h < 25:
        return "coral" if l > 0.55 else "vermillion"
    if h < 40:
        return "amber" if l > 0.5 else "burnt orange"
    if h < 55:
        return "mustard" if l < 0.6 else "gold"
    if h < 75:
        return "olive" if s < 0.5 else "chartreuse"
    if h < 140:
        if l < 0.35:
            return "forest"
        return "emerald" if s > 0.6 else "sage"
    if h < 170:
        return "teal"
    if h < 195:
        return "turquoise"
    if h < 210:
        return "cyan"
    if h < 230:
        return "cerulean"
    if h < 245:
        return "royal blue"
    if h < 260:
        return "indigo"
    if h < 285:
        return "violet"
    if h < 310:
        return "magenta"
    if h < 330:
        return "fuchsia"
    # 330-348
    return "rose"


def rich_color_name(hex_value: str) -> str:
    """Return a more descriptive color name (e.g., maroon, magenta, crimson).

    Uses HSL-based rules layered over CSS naming to get richer names.
    """
    if not isinstance(hex_value, str) or not hex_value.startswith("#"):
        return str(hex_value)
    hv = hex_value.lower()
    if len(hv) == 4:
        hv = "#" + "".join([c * 2 for c in hv[1:]])

    try:
        r = int(hv[1:3], 16) / 255.0
        g = int(hv[3:5], 16) / 255.0
        b = int(hv[5:7], 16) / 255.0
        # colorsys uses HLS order (h, l, s)
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        h_deg = (h * 360.0) % 360.0
        base = _rich_hue_name(h_deg, s, l)
        # Adjectives by lightness/saturation
        prefix = ""
        if s < 0.18:
            prefix = "muted "
        elif s > 0.7 and l > 0.55:
            prefix = "vivid "
        if l < 0.18:
            prefix = "deep " + prefix
        elif l < 0.32:
            prefix = "dark " + prefix
        elif l > 0.8:
            prefix = "pale " + prefix
        elif l > 0.65:
            prefix = "light " + prefix
        name = (prefix + base).strip()
        return name
    except Exception:
        # fallback to CSS3 nearest name
        return color_name_for(hv)


def color_label(hex_value: str) -> str:
    name = rich_color_name(hex_value)
    if isinstance(hex_value, str) and hex_value.startswith("#"):
        return f"{name.title()} ({hex_value.lower()})"
    return str(hex_value)
