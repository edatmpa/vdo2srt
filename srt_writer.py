"""
Converts transcription segments to SRT subtitle format.
"""

from __future__ import annotations

from pathlib import Path


def _format_timestamp(seconds: float) -> str:
    """Convert float seconds to SRT timestamp: HH:MM:SS,mmm"""
    seconds = max(0.0, seconds)
    ms = int((seconds % 1) * 1000)
    s = int(seconds) % 60
    m = int(seconds // 60) % 60
    h = int(seconds // 3600)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments: list[dict], output_path: Path) -> int:
    """
    Write SRT file from a list of segment dicts.

    Each segment must have:
        start (float): start time in seconds
        end   (float): end time in seconds
        text  (str):   subtitle text

    Returns the number of subtitle entries written.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    count = 0

    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue
        count += 1
        lines.append(str(count))
        lines.append(f"{_format_timestamp(seg['start'])} --> {_format_timestamp(seg['end'])}")
        lines.append(text)
        lines.append("")  # blank line between entries

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  SRT written: {output_path}  ({count} entries)")
    return count
