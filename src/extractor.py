"""
Audio extraction and chunking from video/audio files using FFmpeg.
Outputs normalized 16kHz mono WAV suitable for Whisper and Google STT.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

_TEMP_DIR = Path(tempfile.gettempdir()) / "vdo2srt"


def check_ffmpeg() -> bool:
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_duration(audio_path: Path) -> float:
    """Return audio duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe error: {result.stderr}")
    return float(result.stdout.strip())


def has_audio_stream(input_path: Path) -> bool:
    """Return True if the file contains at least one audio stream."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=codec_type",
        "-of", "csv=p=0",
        str(input_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return bool(result.stdout.strip())


def extract_audio(input_path: Path) -> Path:
    """
    Extract and normalize audio from any video or audio file.
    Returns path to a 16kHz mono WAV in the system temp directory.
    """
    if not check_ffmpeg():
        raise OSError(
            "FFmpeg not found. Install from https://ffmpeg.org/download.html "
            "and ensure it is on your system PATH."
        )

    if not has_audio_stream(input_path):
        raise RuntimeError(f"No audio stream found in '{input_path.name}'. The file may be video-only or corrupted.")

    _TEMP_DIR.mkdir(exist_ok=True)
    output_path = _TEMP_DIR / f"{input_path.stem}_16k.wav"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_path),
    ]

    print(f"  Extracting audio from: {input_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed:\n{result.stderr[-1200:]}")

    duration = get_duration(output_path)
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  Audio ready: {size_mb:.1f} MB  ({duration/60:.1f} min)")

    return output_path


def extract_chunk(audio_path: Path, start_sec: float, duration_sec: float) -> Path:
    """
    Extract a time slice of audio for chunked cloud processing.
    Returns path to the chunk WAV file (overwritten on each call).
    """
    chunk_path = _TEMP_DIR / f"chunk_{int(start_sec):06d}.wav"

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_sec),
        "-t", str(duration_sec),
        "-i", str(audio_path),
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(chunk_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Chunk extraction failed at {start_sec}s:\n{result.stderr[-800:]}")

    return chunk_path
