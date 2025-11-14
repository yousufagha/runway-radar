"""Helpers for loading runway image datasets and metadata."""
from pathlib import Path
from typing import List


def list_image_files(directory: Path, extensions=None) -> List[Path]:
    """
    List image files under a directory filtered by extensions.

    Parameters
    ----------
    directory : Path
        Root directory containing image files.
    extensions : Iterable[str] or None
        File suffixes (e.g., [".jpg", ".png"]). Defaults to common formats.

    Returns
    -------
    List[Path]
        Sorted list of matching file paths.
    """
    if extensions is None:
        extensions = {".jpg", ".jpeg", ".png", ".bmp"}
    return sorted(path for path in directory.rglob("*") if path.suffix.lower() in extensions)
