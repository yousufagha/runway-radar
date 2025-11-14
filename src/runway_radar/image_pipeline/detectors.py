"""Detector utilities for Runway Radar's image pipeline."""
from typing import Any, Dict, List

from PIL import Image


def load_yolo_detector(device: str = "cpu") -> Any:
    """
    Placeholder for loading a YOLOv8 style detector (ultralytics/Detectron2).
    """
    _ = device
    return None


def detect_garments(model: Any, image: Image.Image, device: str = "cpu") -> List[Dict[str, Any]]:
    """
    Return garment detections with `label`, `score`, `box` keys.

    Each box should be xyxy coordinates once implemented.
    """
    _ = (model, image, device)
    return []
