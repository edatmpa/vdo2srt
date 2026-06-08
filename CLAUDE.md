# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the tool

All commands use the venv Python at `E:\vdo2srt\venv\Scripts\python.exe`.

```powershell
# Single file (CLI)
"E:\vdo2srt\venv\Scripts\python.exe" vdo2srt.py "E:\path\to\film.mkv" --engine local --language ru

# Batch (pass a folder instead of a file)
"E:\vdo2srt\venv\Scripts\python.exe" vdo2srt.py "E:\Movies" --engine local --language ru

# Skip English translation
"E:\vdo2srt\venv\Scripts\python.exe" vdo2srt.py "E:\Movies" --engine local --language ru --no-translate

# Test Google Cloud credentials
"E:\vdo2srt\venv\Scripts\python.exe" test_google_apis.py
```

Key CLI flags: `--engine local|cloud`, `--model tiny|base|small|medium|large-v2|large-v3` (default: large-v3), `--device auto|cuda|cpu`, `--language LANG`, `--max-duration SECS` (default: 6, 0=off), `--no-translate`, `--target-language LANG` (default: en), `--overwrite` (batch mode).

Install dependencies: `venv\Scripts\pip install -r requirements.txt`

## Architecture

**Entry point:** `vdo2srt.py` handles both single-file and batch/folder mode. It detects whether `input` is a file or directory and routes accordingly. When arguments are missing it shows tkinter GUI dialogs (target type → file/folder picker → method picker).

**Pipeline** (single file):
1. `extractor.extract_audio()` — FFmpeg extracts 16kHz mono WAV to `%TEMP%\vdo2srt\`
2. `transcriber.get_transcriber()` returns either `LocalTranscriber` or `CloudTranscriber`
3. `transcriber.transcribe()` returns `list[dict]` with `{start, end, text}` keys
4. `srt_writer.write_srt()` writes the `.srt` file
5. `translator.translate_segments()` translates and writes the `.en.srt` (unless `--no-translate`)

**`transcriber.py`** — Two engines:
- `LocalTranscriber`: faster-whisper on CUDA (int8_float16) or CPU (int8). Auto-detects GPU via ctranslate2. If `max_duration` is set, requests `word_timestamps=True` from Whisper and then calls `split_segments()` to re-cut long entries at word boundaries.
- `CloudTranscriber`: chunks audio into 55-second slices (under the 60s sync API limit), sends each to Google STT, reassembles with corrected timestamps. Language must be BCP-47; a short mapping dict handles `ru`→`ru-RU` etc.

**`translator.py`** — Batches segments in groups of 20, joins with ` ||| ` separator for a single HTTP call, then splits back. Falls back to one-per-segment if the separator is mangled. Retries up to 3 times (5 s, 10 s backoff) on any network error.

**Segment dict shape:** `{start: float, end: float, text: str}`. The `words` key (list of faster-whisper Word objects) is present only during local transcription when `max_duration` is set; it is stripped by `split_segments()` before segments leave `transcriber.py`.

## Google Cloud credentials

Set `GOOGLE_APPLICATION_CREDENTIALS` in a `.env` file (see `.env.example`) or pass `--credentials <path>` at runtime. The STT key is at `E:\API Key\Google API Keys\speech2txt.json`.
