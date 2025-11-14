import base64
import os
from typing import Dict, Any, List

from .utils import parse_json_safely


# Backend selection: 'auto' | 'openai' | 'ollama' | 'local'
BACKEND = os.environ.get("FASHION_TREND_BACKEND", "auto").lower()

# OpenAI config
OPENAI_MODEL_TEXT = os.environ.get("FASHION_TREND_MODEL", "gpt-4o-mini")
OPENAI_MODEL_VISION = os.environ.get("FASHION_TREND_VISION_MODEL", "gpt-4o-mini")

# Ollama config (local LLMs)
OLLAMA_MODEL_TEXT = os.environ.get("OLLAMA_MODEL_TEXT", "llama3")
OLLAMA_MODEL_VISION = os.environ.get("OLLAMA_MODEL_VISION", "llava")


def _has_openai_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _ollama_available() -> bool:
    try:
        import ollama  # noqa: F401
        return True
    except Exception:
        return False


def _prefer_openai() -> bool:
    if BACKEND == "openai":
        return True
    if BACKEND == "ollama" or BACKEND == "local":
        return False
    # auto: prefer openai if key exists
    return _has_openai_key()


def _prefer_ollama() -> bool:
    if BACKEND == "ollama":
        return True
    if BACKEND == "openai":
        return False
    # auto: use ollama if no openai key and ollama available
    return (not _has_openai_key()) and _ollama_available()


# ----- OpenAI path -----
def _json_request_openai(messages: List[Dict[str, Any]], model: str) -> Dict[str, Any]:
    try:
        from openai import OpenAI

        client = OpenAI()
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        return parse_json_safely(content, default={})
    except Exception:
        return {}


# ----- Ollama path -----
def _json_request_ollama(prompt_messages: List[Dict[str, Any]], model: str, images_b64: List[str] | None = None) -> Dict[str, Any]:
    try:
        import ollama

        # Convert messages to a single prompt for JSON compliance
        # Preserve system and user parts
        parts = []
        for m in prompt_messages:
            role = m.get("role")
            content = m.get("content")
            if isinstance(content, list):
                # flatten text parts
                texts = []
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        texts.append(c.get("text", ""))
                content = "\n".join(texts)
            parts.append(f"[{role}]\n{content}")
        prompt = "\n\n".join(parts) + "\n\nReturn ONLY strict JSON."

        kwargs: Dict[str, Any] = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        if images_b64:
            # Attach images to the user message (llava supports this)
            kwargs["messages"][0]["images"] = images_b64

        resp = ollama.chat(**kwargs)
        content = resp.get("message", {}).get("content", "")
        return parse_json_safely(content, default={})
    except Exception:
        return {}


def analyze_image(image_bytes: bytes) -> Dict[str, Any]:
    if not image_bytes:
        return {"garments": [], "colors": [], "styles": [], "designers": []}

    # Try preferred backend(s)
    if _prefer_openai():
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        messages = [
            {"role": "system", "content": "You are a fashion vision analyst. Return only strict JSON."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": (
                        "Analyze the runway image. Identify garments (e.g., blazer, midi dress), "
                        "dominant colors (CSS names if obvious, else hex), styles (e.g., minimalism, streetwear, avant-garde), "
                        "and any visible designer logos/identifiers. Return strict JSON with keys: "
                        "garments (array), colors (array), styles (array), designers (array)."
                    )},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            },
        ]
        data = _json_request_openai(messages, OPENAI_MODEL_VISION)
        if data:
            return {
                "garments": data.get("garments", []) or [],
                "colors": data.get("colors", []) or [],
                "styles": data.get("styles", []) or [],
                "designers": data.get("designers", []) or [],
            }

    if _prefer_ollama():
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        messages = [
            {"role": "system", "content": "You are a fashion vision analyst. Return only strict JSON."},
            {"role": "user", "content": (
                "Analyze the runway image and return JSON with keys: garments, colors, styles, designers."
            )},
        ]
        data = _json_request_ollama(messages, OLLAMA_MODEL_VISION, images_b64=[b64])
        if data:
            return {
                "garments": data.get("garments", []) or [],
                "colors": data.get("colors", []) or [],
                "styles": data.get("styles", []) or [],
                "designers": data.get("designers", []) or [],
            }

    # Fallback heuristic (no model)
    return {"garments": [], "colors": [], "styles": [], "designers": []}


def extract_entities(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []

    schema = (
        "Extract fashion-related entities from the text. Types: garment, color, style, designer, brand, trend, catalyst "
        "(cultural catalyst like celebrity, event, or movement). Return JSON: {\"entities\": ["
        "{\"type\": string, \"value\": string, \"confidence\": number}]}. Use lowercase for type and normalize values (singular)."
    )
    messages = [
        {"role": "system", "content": "You are a precise NER annotator. Return strict JSON."},
        {"role": "user", "content": f"{schema}\n\nText:\n{text}"},
    ]

    data: Dict[str, Any] = {}
    if _prefer_openai():
        data = _json_request_openai(messages, OPENAI_MODEL_TEXT)
    elif _prefer_ollama():
        data = _json_request_ollama(messages, OLLAMA_MODEL_TEXT)

    ents = data.get("entities") if isinstance(data, dict) else None
    if isinstance(ents, list):
        out = []
        for e in ents:
            et = str(e.get("type", "")).strip().lower()
            val = str(e.get("value", "")).strip()
            if et and val:
                conf = float(e.get("confidence", 0.7))
                out.append({"type": et, "value": val, "confidence": conf})
        return out

    # Fallback heuristic without model
    COLOR_WORDS = {
        "red", "blue", "green", "yellow", "black", "white", "purple", "pink", "orange", "beige", "brown", "gray", "grey",
        "navy", "teal", "maroon", "gold", "silver"
    }
    GARMENTS = {"dress", "blazer", "coat", "trench", "skirt", "jeans", "denim", "sneakers", "heels", "boots", "shirt", "blouse", "suit"}
    STYLES = {"minimalism", "streetwear", "boho", "vintage", "y2k", "punk", "preppy", "athleisure"}
    BRANDS = {"chanel", "dior", "gucci", "prada", "balenciaga", "valentino", "louis vuitton", "saint laurent", "burberry", "versace", "hermes", "fendi", "armani"}
    TRENDS = {"couture", "ready-to-wear", "rtw", "resort", "pre-fall", "spring-summer", "fall-winter", "runway", "catwalk"}
    words = [w.strip(".,!?:;()[]{}\"'\n\t ").lower() for w in text.split()]
    out: List[Dict[str, Any]] = []
    for w in words:
        if w in COLOR_WORDS:
            out.append({"type": "color", "value": w, "confidence": 0.5})
        if w in GARMENTS:
            out.append({"type": "garment", "value": w, "confidence": 0.5})
        if w in STYLES:
            out.append({"type": "style", "value": w, "confidence": 0.5})
        if w in TRENDS:
            out.append({"type": "trend", "value": w, "confidence": 0.5})
    # brand heuristic: look for Title Case tokens
    tokens = [t.strip(".,!?:;()[]{}\"'\n\t ") for t in text.split()]
    
    for i, tok in enumerate(tokens):
        if tok[:1].isupper() and tok.isalpha() and len(tok) > 2:
            name = tok
            # Try to join with next capitalized token
            if i + 1 < len(tokens) and tokens[i + 1][:1].isupper():
                name = f"{tok} {tokens[i+1]}"
            low = name.lower()
            if low in BRANDS:
                out.append({"type": "brand", "value": name, "confidence": 0.6})
            else:
                out.append({"type": "designer", "value": name, "confidence": 0.4})
            break

    return out


def interpret_query(query: str) -> Dict[str, Any]:
    if not query:
        return {"intent": "rank", "metric": "popularity", "timeframe": "all", "chart_type": "bar", "entity_type": "color", "entities": []}

    schema = (
        "Interpret the user's trend question and return JSON with keys: "
        "intent (rank|compare|trend), metric (popularity), timeframe (all|week|month), "
        "chart_type (bar|table|line), entity_type (color|garment|style|designer|catalyst), "
        "entities (array of strings)."
    )
    examples = (
        "Example: 'Rank colors by popularity this week' -> {\"intent\":\"rank\",\"metric\":\"popularity\",\"timeframe\":\"week\",\"chart_type\":\"bar\",\"entity_type\":\"color\",\"entities\":[]}"
    )
    messages = [
        {"role": "system", "content": "You are an intent parser. Return strict JSON only."},
        {"role": "user", "content": f"{schema}\n{examples}\n\nQuery:\n{query}"},
    ]

    data: Dict[str, Any] = {}
    if _prefer_openai():
        data = _json_request_openai(messages, OPENAI_MODEL_TEXT)
    elif _prefer_ollama():
        data = _json_request_ollama(messages, OLLAMA_MODEL_TEXT)

    if data:
        out = {
            "intent": (data.get("intent") or "rank").lower(),
            "metric": (data.get("metric") or "popularity").lower(),
            "timeframe": (data.get("timeframe") or "all").lower(),
            "chart_type": (data.get("chart_type") or "bar").lower(),
            "entity_type": (data.get("entity_type") or "color").lower(),
            "entities": data.get("entities") or [],
        }
        if not isinstance(out["entities"], list):
            out["entities"] = []
        return out

    # Heuristic fallback
    q = query.lower()
    timeframe = "all"
    if "week" in q:
        timeframe = "week"
    elif "month" in q:
        timeframe = "month"
    entity_type = "color"
    for et in ["color", "garment", "style", "designer", "catalyst"]:
        if et in q or et + "s" in q:
            entity_type = et
            break
    chart_type = "bar"
    if "table" in q:
        chart_type = "table"
    elif "line" in q or "trend" in q:
        chart_type = "line"
    return {
        "intent": "rank",
        "metric": "popularity",
        "timeframe": timeframe,
        "chart_type": chart_type,
        "entity_type": entity_type,
        "entities": [],
    }
