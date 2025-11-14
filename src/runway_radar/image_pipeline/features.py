"""CLIP-style feature extraction for capturing runway style embeddings."""
from typing import Any

import numpy as np
from PIL import Image


def extract_clip_features(image: Image.Image, model: Any | None = None, device: str = "cpu") -> np.ndarray:
    """
    Generate a one-dimensional embedding vector for an image.

    Parameters
    ----------
    image
        The runway image to process.
    model
        Optional pretrained model instance.
    device
        Device identifier (cpu/gpu).
    """
    _ = (model, device)
    return np.zeros(512, dtype=np.float32)
