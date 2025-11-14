import io
from typing import List

from PIL import Image

from .utils import to_hex


def extract_palette(image_bytes: bytes, k: int = 5) -> List[str]:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return []
    # Downscale to speed up and reduce noise
    small = img.copy()
    small.thumbnail((200, 200))
    max_colors = 10000
    colors = small.getcolors(maxcolors=max_colors)  # List of (count, (r,g,b))
    if not colors:
        # Fallback to quantize
        palette_img = small.convert("P", palette=Image.ADAPTIVE, colors=min(k, 16))
        palette = palette_img.getpalette()  # flat list
        triples = [tuple(palette[i:i+3]) for i in range(0, len(palette), 3)]
        triples = triples[:k]
        return [to_hex(t) for t in triples]

    colors.sort(reverse=True, key=lambda x: x[0])
    top = [rgb for _, rgb in colors[: max(k, 1)]]
    # Deduplicate nearby colors roughly by rounding to 16s
    dedup = []
    for r, g, b in top:
        key = (r // 16, g // 16, b // 16)
        if key not in [(rr // 16, gg // 16, bb // 16) for rr, gg, bb in dedup]:
            dedup.append((r, g, b))
        if len(dedup) >= k:
            break
    return [to_hex(rgb) for rgb in dedup]

