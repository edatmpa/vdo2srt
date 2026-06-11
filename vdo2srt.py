"""
vdo2srt — Convert a video/audio file (or all files in a folder) to SRT subtitle files.

This is a thin wrapper that delegates to the src/ package.
Usage:  python vdo2srt.py <file_or_folder> [options]
        Double-click vdo2srt.bat for the GUI mode.
"""

import os

# Suppress OpenMP duplicate-library warning (common with faster-whisper + numpy).
# Must be set before any module that loads libiomp5md.dll is imported.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import sys
from pathlib import Path

# Ensure the project root is on sys.path so `src` can be imported
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.cli import main

if __name__ == "__main__":
    main()
