"""Extract dominant colour palettes from images."""
from typing import List, Tuple

from PIL import Image


def extract_colour_palette(image: Image.Image, num_colours: int = 5) -> List[Tuple[int, int, int]]:
    """
    Return `num_colours` dominant colours as RGB tuples.

    Placeholder currently samples the centre pixel plus duplicates to match
    the desired length; future logic should perform clustering (e.g., k-means).
    """
    width, height = image.size
    centre_colour = image.getpixel((width // 2, height // 2))
    palette = [centre_colour] * num_colours
    return palette
