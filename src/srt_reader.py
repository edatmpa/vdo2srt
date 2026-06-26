"""
SRT file reader — parses .srt subtitle files into segment objects.

Returns a list of dictionaries with timing and text data compatible with
write_srt() and translate_segments().
"""

from __future__ import annotations

import re
from pathlib import Path


def read_srt(srt_path: Path) -> list[dict]:
    """
    Read an SRT file and return a list of segment dictionaries.
    
    Each segment has:
    - 'start': start time in seconds (float)
    - 'end': end time in seconds (float)
    - 'text': subtitle text (string)
    
    Args:
        srt_path: Path to the .srt file to read
        
    Returns:
        List of segment dictionaries. Empty list if file is empty or malformed.
        
    Raises:
        FileNotFoundError: If the SRT file doesn't exist
        ValueError: If the file is not readable as text
    """
    if not srt_path.exists():
        raise FileNotFoundError(f"SRT file not found: {srt_path}")
    
    segments = []
    
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try with different encoding
        with open(srt_path, 'r', encoding='latin-1') as f:
            content = f.read()
    
    # Split by double newlines to get individual subtitle blocks
    blocks = content.strip().split('\n\n')
    
    for block in blocks:
        if not block.strip():
            continue
        
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        
        # First line is index (skip it)
        # Second line is timecode
        timecode_line = lines[1]
        # Remaining lines are text
        text_lines = lines[2:]
        
        # Parse timecode: "00:00:01,234 --> 00:00:05,678"
        match = re.match(
            r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})',
            timecode_line
        )
        if not match:
            continue
        
        start_h, start_m, start_s, start_ms, end_h, end_m, end_s, end_ms = map(int, match.groups())
        
        start = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000
        end = end_h * 3600 + end_m * 60 + end_s + end_ms / 1000
        
        text = '\n'.join(text_lines)
        
        segments.append({
            'start': start,
            'end': end,
            'text': text,
        })
    
    return segments