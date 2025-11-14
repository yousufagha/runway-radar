"""CLIP or related feature extractor utilities for runway imagery."""
from typing import Any

import numpy as np
from PIL import Image


def extract_clip_features(image: Image.Image, device: str = "cpu") -> np.ndarray:
    """
    Extract embeddings for an image via CLIP (placeholder implementation).

    Future versions should preprocess the image, run it through a CLIP encoder,
    and return the resulting embedding tensor on the requested device.
    """
    _ = (image, device)
    return np.zeros(512, dtype=np.float32)
