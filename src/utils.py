"""
Shared constants and utility functions used across the vdo2srt package.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Supported media file extensions
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".m4v",
    ".mp3", ".wav", ".m4a", ".flac", ".ogg",
}


def is_media_file(path: Path) -> bool:
    """Return True if *path* has a supported media extension (case-insensitive)."""
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def find_media_files(folder: Path) -> list[Path]:
    """Return sorted list of supported media files inside *folder*."""
    return sorted(f for f in folder.iterdir() if is_media_file(f))
