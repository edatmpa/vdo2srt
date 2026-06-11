"""
vdo2srt — Convert video/audio files to SRT subtitle files.

Modules:
    cli         — Argument parsing and main orchestration
    gui         — Tkinter GUI dialogs for file/method selection
    extractor   — FFmpeg audio extraction and chunking
    transcriber — Transcription engines (local Whisper, Google Cloud STT)
    translator  — Subtitle translation via Google Translate
    srt_writer  — SRT subtitle file formatting
"""

__version__ = "2.0.0"
