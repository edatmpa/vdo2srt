# vdo2srt 🎬➡️📝

Convert video/audio files to SRT subtitle files using **faster-whisper** (local GPU/CPU) or **Google Cloud Speech-to-Text**.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 📖 **Main user guide**: [`docs/user_manual.svg`](docs/user_manual.svg) — visual walkthrough of the entire workflow

## Features

- 🎯 **Two engines**: Local Whisper (offline, free) or Google Cloud STT (cloud, accurate)
- 🚀 **GPU acceleration**: Auto-detects CUDA — falls back to CPU
- 🌍 **Multi-language**: Auto-detect or specify language (en, ru, ja, th, fr, de, etc.)
- 🔄 **Auto-translate**: Produces an English `.en.srt` file automatically (no API key needed)
- 📁 **Batch mode**: Process an entire folder of videos in one go
- 🖥️ **GUI dialogs**: Double-click the `.bat` file for a point-and-click interface
- ✂️ **Smart splitting**: Splits long subtitle entries at word boundaries
- ↔️ **Custom target languages**: Translate to any language

## Quick Start (Windows)

### Prerequisites

1. Install [Python 3.9+](https://www.python.org/downloads/) (check "Add Python to PATH")
2. Install [FFmpeg](https://ffmpeg.org/download.html) and add it to your system PATH
3. (Optional) NVIDIA GPU with [CUDA](https://developer.nvidia.com/cuda-downloads) for GPU acceleration

### Installation

```bash
# Clone the repository
git clone https://github.com/mappointasia/vdo2srt.git
cd vdo2srt

# Create a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

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

:: Re-process files that already have an .srt
vdo2srt.bat "E:\Movies" --engine local --overwrite
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
- [deep-translator](https://github.com/nidhaloff/deep-translator) — Google Translate (no API key)

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
├── vdo2srt.py          # Entry point
├── vdo2srt.bat         # Windows launcher
├── pyproject.toml       # Python packaging
├── requirements.txt     # Pip dependencies
├── src/
│   ├── cli.py          # Argument parsing & orchestration
│   ├── extractor.py    # FFmpeg audio extraction
│   ├── transcriber.py  # Whisper & Google STT engines
│   ├── translator.py   # Google Translate integration
│   ├── srt_writer.py   # SRT formatting
│   ├── gui.py          # Tkinter GUI dialogs
│   └── utils.py        # File utilities
├── docs/
│   ├── technical.md    # Architecture & decisions
│   ├── user_manual.md  # Detailed user guide
│   └── user_manual.svg # GUI workflow diagram
└── LICENSE
```

## License

[MIT](LICENSE)
