"""
Utility functions for vdo2srt.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

_MEDIA_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v',
    '.mp3', '.wav', '.aac', '.flac', '.m4a', '.wma', '.ogg', '.opus',
}

# Folder names that are never movie/show folders — skipped by name alone,
# without checking disk. Shared by process_list.py and translate_srt.py so
# both tools agree on what to walk past.
_SKIP_NAMES = {"thumbs", "folder", "extras", "featurettes", "behind the scenes",
               "deleted scenes", "interviews", "scenes", "shorts", "trailers"}

# Matches a trailing ".xx" or ".xx-xx" language-code-shaped suffix (e.g. the
# ".en" in "movie.en", or ".zh-cn" in "movie.zh-cn") — used to tell an
# already-translated "<stem>.<lang>.srt" apart from an original "<stem>.srt".
# A 3+ letter release tag (e.g. "...AVC") never matches this.
_LANG_SUFFIX_RE = re.compile(r'\.([a-zA-Z]{2}(?:-[a-zA-Z]{2})?)$')


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


def is_skippable_folder(folder: Path) -> bool:
    """
    True if a folder should be skipped when walking a media library — hidden
    (name starts with '.') or a known non-movie folder name (Extras, Sample,
    Featurettes, etc.).
    """
    name = folder.name
    return name.startswith('.') or name.lower() in _SKIP_NAMES


def find_original_srt_files(folder: Path) -> list[Path]:
    """
    Find "original" .srt files in a folder (non-recursive) — excluding any
    file that already looks like a translation output, i.e. one matching
    "<stem>.<lang-code>.srt" (e.g. "movie.en.srt" is excluded, "movie.srt"
    and "movie.S01E01.AVC.srt" are included).

    Used by the translate-only paths (orphan .srt with no matching video,
    and the standalone translate_srt.py tool) to find source files without
    accidentally re-translating an existing translation.
    """
    if not folder.is_dir():
        return []

    originals = [
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() == '.srt'
        and not _LANG_SUFFIX_RE.search(f.stem)
    ]

    return sorted(originals, key=lambda p: p.name)


def find_movie_subfolders(root: Path) -> list[Path]:
    """
    Return the immediate subfolders of *root* (non-recursive), skipping
    hidden/known non-movie folder names. Used for a "library root -> movie
    folders -> files" one-level walk (e.g. translate_srt.py --recursive).
    """
    if not root.is_dir():
        return []

    subfolders = [
        f for f in root.iterdir()
        if f.is_dir() and not is_skippable_folder(f)
    ]

    return sorted(subfolders, key=lambda p: p.name)


def clean_path(raw: str) -> Path:
    """
    Turn a typed/pasted path into a Path: trims whitespace and any surrounding
    double quotes (Explorer's "Copy as path" and drag-and-drop both add them).
    """
    return Path(raw.strip().strip('"').strip())


def backup_if_exists(path: Path) -> Path | None:
    """
    If *path* exists, copy it to "<name>.bak" (overwriting any previous
    backup) before it gets replaced, and return the backup path. No-op
    (returns None) if *path* doesn't exist yet.
    """
    if not path.exists():
        return None
    backup_path = path.with_name(path.name + ".bak")
    shutil.copy2(path, backup_path)
    return backup_path