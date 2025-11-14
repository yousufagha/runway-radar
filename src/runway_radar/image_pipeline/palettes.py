"""Convert runway images into representative colour palettes."""
from typing import List, Tuple

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans


def extract_colour_palette(image: Image.Image, num_colours: int = 5) -> List[Tuple[int, int, int]]:
    """
    Resize the image, cluster pixels, and return RGB tuples.
    """
    resized = image.resize((128, 128))
    pixels = np.array(resized).reshape(-1, 3)
    kmeans = KMeans(n_clusters=num_colours, n_init=5, random_state=42)
    kmeans.fit(pixels)
    centres = kmeans.cluster_centers_
    return [tuple(map(int, centre.tolist())) for centre in centres]
