"""
Converts transcription segments to SRT subtitle format.
"""

from __future__ import annotations

from pathlib import Path


def _format_timestamp(seconds: float) -> str:
    """
    Convert seconds (float) to SRT timestamp format: HH:MM:SS,mmm
    """
    seconds = max(0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(segments: list[dict], output_path: Path) -> int:
    """
    Write segments to SRT file.
    
    Args:
        segments: List of dicts with 'start', 'end', 'text' keys
        output_path: Path where SRT file will be written
        
    Returns:
        Number of subtitle entries written
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    srt_lines = []
    count = 0
    
    for idx, seg in enumerate(segments, 1):
        text = seg.get("text", "").strip()
        if not text:
            continue
        
        start = _format_timestamp(seg.get("start", 0))
        end = _format_timestamp(seg.get("end", 0))
        
        srt_lines.append(str(count + 1))
        srt_lines.append(f"{start} --> {end}")
        srt_lines.append(text)
        srt_lines.append("")
        
        count += 1
    
    output_path.write_text('\n'.join(srt_lines), encoding='utf-8')
    print(f"  Wrote {output_path}")
    
    return count