# vdo2srt 🎬➡️📝

Convert video/audio files to SRT subtitle files using **faster-whisper** (local GPU/CPU) or **Google Cloud Speech-to-Text**.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 📖 **Main user guide**: [`docs/user_manual.svg`](docs/user_manual.svg) — visual walkthrough of the entire workflow

## Features

- 🎯 **Two transcription engines**: Local Whisper (offline, free) or Google Cloud STT (cloud, accurate)
- 🚀 **GPU acceleration**: Auto-detects CUDA — falls back to CPU
- 🌍 **Multi-language**: Auto-detect or specify language (en, ru, ja, th, fr, de, etc.)
- 🔄 **Auto-translate**: Produces an English `.en.srt` file automatically
- 🧭 **Routed translation engines**: for `ko`/`ja`/`zh`/`ru`, DeepL first, then DeepSeek once DeepL's quota runs out, then free Google (per `translate_routing.txt`); free Google for everything else — source language is detected from the actual subtitle text, and the routing is a one-line text-file edit away from adding a new language or engine
- 📁 **Batch mode**: Process an entire folder of videos in one go, or every folder listed in a text file (`process_list.py`)
- 📝 **Translate-only tool**: `translate_srt.py` retranslates/replaces existing `.srt` files with no video or transcription involved — single file, one folder, or a whole library root
- 🖥️ **GUI dialogs**: Double-click a `.bat` file for a point-and-click interface
- ✂️ **Smart splitting**: Splits long subtitle entries at word boundaries
- ↔️ **Custom target languages**: Translate to any language
- 🛡️ **Safe overwrite**: Retranslating an existing `.en.srt` backs up the previous version to `.bak` first

## Quick Start (Windows)

### Prerequisites

1. Install [Python 3.10+](https://www.python.org/downloads/) (check "Add Python to PATH")
2. (Optional) NVIDIA GPU for fast local transcription. Without one, the CPU is used automatically.

### Installation

Clone or download the repository, then **double-click `setup.bat`**. It:
- builds the Python environment (`venv`) for *this* PC and installs `requirements.txt`
  (a venv copied from another PC never works; setup renames it to `venv_old_<date>`)
- installs the NVIDIA CUDA libraries (`requirements-gpu.txt`) only if an NVIDIA GPU is present
- checks FFmpeg and offers to install it with winget

Run `setup.bat` again whenever a launcher says the venv is missing or broken.

```bash
git clone https://github.com/SaksiriK/create-EN-SRT-from-video-sound-track.git
```

> **Windows Smart App Control:** if it is on, Windows blocks unsigned program files it doesn't know
> ("An Application Control policy has blocked this file"). `requirements.txt` pins `ctranslate2==4.8.1`,
> a version Windows allows. Don't upgrade it without testing that `import ctranslate2` still works.

### Usage — GUI Mode

1. **Double-click** `vdo2srt.bat`
2. Choose **"Single video / audio file"** or **"Entire folder (batch)"**
3. Select your file or folder
4. Choose a transcription method:
   - **Local — GPU** (fast, offline) — requires NVIDIA CUDA
   - **Local — CPU** (slow, offline) — works on any machine
   - **Google Cloud** (accurate, online) — requires a service account key

Two files are saved beside each video:
- `film.srt` — subtitles in the original language
- `film.en.srt` — auto-generated English translation

### Usage — Command Line

```bat
:: Single Russian film with GPU
vdo2srt.bat "E:\Movies\film.mkv" --engine local --language ru

:: Skip translation (original subtitles only)
vdo2srt.bat "E:\Movies\film.mkv" --engine local --language ru --no-translate

:: Translate to French instead of English
vdo2srt.bat "E:\Movies\film.mkv" --engine local --language ru --target-language fr

:: Auto-detect language
vdo2srt.bat "E:\Movies\film.mp4" --engine local

:: Batch process an entire folder
vdo2srt.bat "E:\Movies" --engine local --language ru

:: Use Google Cloud engine
vdo2srt.bat "E:\Movies\film.mkv" --engine cloud --credentials "path\to\key.json"

:: Custom output location (single-file only)
vdo2srt.bat "E:\Movies\film.mkv" --engine local -o "E:\Subtitles\film.srt"

:: Tighter subtitle splitting (4 seconds)
vdo2srt.bat "E:\Movies\film.mkv" --engine local --max-duration 4

:: Re-process files that already have an .srt (also retranslates existing .en.srt, backed up first)
vdo2srt.bat "E:\Movies" --engine local --overwrite

:: Batch across many folders listed in a text file
process_list.bat "E:\no_subs.txt" --engine local --language ru

:: Translate existing .srt files only (no video/transcription) — one folder
translate_srt.bat "V:\Korean\Movie Title (2022)"

:: Translate existing .srt files across a whole library (root -> movie folders)
translate_srt.bat "V:\War Series (Russia)" --recursive

:: Retranslate and replace existing translations across that library
translate_srt.bat "V:\War Series (Russia)" --recursive --overwrite
```

## Defaults

| Setting | Default |
|---------|---------|
| Engine | GUI picker (if not specified) |
| Model | `large-v3` (best quality) |
| Device | Auto — GPU if available, CPU otherwise |
| Language | Auto-detected |
| Max entry duration | 6 seconds |
| Output location | Same folder as video, `.srt` extension |
| Translation | ON — always produces `.en.srt` (use `--no-translate` to skip) |
| Target language | `en` (English) |
| Translation engine | Auto-routed per detected source language — see `translate_routing.txt` |

## Options

```
positional arguments:
  input                 Video/audio file or folder (omit for GUI picker)

options:
  --engine {local,cloud}
                        Transcription engine
  --model {tiny,base,small,medium,large-v2,large-v3}
                        Whisper model size (local only, default: large-v3)
  --device {auto,cuda,cpu}
                        Processing device (local only, default: auto)
  --language LANG       Language code (e.g. ru, en, ja, th)
  --credentials PATH    Google Cloud service account JSON (cloud engine only)
  --max-duration SECS   Max subtitle entry duration in seconds (default: 6, 0=disable)
  --output PATH, -o PATH
                        Output SRT path (single-file only)
  --no-translate        Skip English translation
  --target-language LANG
                        Translation target language (default: en)
  --overwrite           Re-process files that already have an .srt
```

## Requirements

### Core (always needed)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — Whisper transcription with CTranslate2
- [tqdm](https://github.com/tqdm/tqdm) — Progress bars
- [deepl](https://github.com/DeepLcom/deepl-python) — DeepL translation engine, routed per `translate_routing.txt`
- [deep-translator](https://github.com/nidhaloff/deep-translator) — Google Translate, free fallback engine (no API key)
- [langdetect](https://github.com/Mimino666/langdetect) — source-language detection for translation routing

### Cloud engine (optional)
- `google-cloud-speech`
- `google-auth`

### System
- **FFmpeg** — Audio extraction ([download](https://ffmpeg.org/download.html))
- **NVIDIA CUDA** (optional) — GPU acceleration

## Install as a Package

```bash
pip install .
```

Or with cloud support:

```bash
pip install .[cloud]
```

After installing, you can run `vdo2srt` from anywhere:

```bash
vdo2srt "movie.mkv" --engine local --language ru
```

## Project Structure

```
vdo2srt/
├── vdo2srt.py           # Single file / one folder — delegates to src/cli.py
├── vdo2srt.bat          # Windows launcher (menu: vdo2srt / process_list / translate_srt)
├── process_list.py      # Batch over many folders listed in a text file
├── process_list.bat     # Windows launcher
├── translate_srt.py     # Translate existing .srt files only — no video/transcription
├── translate_srt.bat    # Windows launcher
├── translate_routing.txt # Per-language translation engine routing (edit to add/move languages)
├── pyproject.toml       # Python packaging (pip install .)
├── requirements.txt     # Pip dependencies
├── requirements-gpu.txt # NVIDIA cuBLAS/cuDNN wheels (setup.bat adds them on a GPU PC)
├── setup.bat            # Builds/repairs venv\ for this PC
├── _env.bat             # Shared launcher start-up (ROOT, PY, GPU DLL path, venv check)
├── .env.example         # Credentials env var template
├── src/
│   ├── __init__.py     # Package marker, version string
│   ├── __main__.py     # python -m src entry point
│   ├── cli.py          # vdo2srt.py's argument parsing & orchestration
│   ├── extractor.py    # FFmpeg audio extraction
│   ├── transcriber.py  # Whisper & Google STT engines
│   ├── translator.py   # Translation engines (DeepL/DeepSeek/free fallback), routing chains, translate_existing_srt()
│   ├── srt_reader.py   # Parses an existing .srt back into segments
│   ├── srt_writer.py   # SRT formatting
│   ├── gui.py          # Tkinter GUI dialogs
│   └── utils.py        # Shared file utilities (media/srt discovery, backup helper)
├── docs/
│   ├── technical.md    # Architecture & module reference
│   ├── user_manual.md  # Detailed user guide
│   ├── how_to_run_windows.txt # Quick Windows how-to (menu + command-line examples)
│   └── user_manual.svg # Visual workflow diagram
└── LICENSE
```

## License

[MIT](LICENSE)
