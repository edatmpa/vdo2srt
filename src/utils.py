"""
Utility functions for vdo2srt.
"""

from __future__ import annotations

from pathlib import Path

_MEDIA_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v',
    '.mp3', '.wav', '.aac', '.flac', '.m4a', '.wma', '.ogg', '.opus',
}


def find_media_files(folder: Path) -> list[Path]:
    """
    Find all supported media files in a folder (non-recursive).
    
    Args:
        folder: Directory to search
        
    Returns:
        List of media file paths, sorted by name
    """
    if not folder.is_dir():
        return []
    
    media_files = [
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in _MEDIA_EXTENSIONS
    ]
    
    return sorted(media_files, key=lambda p: p.name)