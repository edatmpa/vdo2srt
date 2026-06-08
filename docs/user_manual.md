# vdo2srt — User Manual

Convert a movie video or audio file into an SRT subtitle file, ready to edit in SubtitleEdit.

---

## Prerequisites

### 1. Python 3.9 or later
Download from https://www.python.org/downloads/  
During installation, check **"Add Python to PATH"**.

Verify: open a terminal and run:
```
python --version
```

### 2. FFmpeg
FFmpeg extracts the audio track from your video file.

**Windows installation:**
1. Download from https://ffmpeg.org/download.html (get the "Windows builds" from gyan.dev or BtbN)
2. Extract the zip file (e.g. to `C:\ffmpeg`)
3. Add `C:\ffmpeg\bin` to your Windows PATH:
   - Search "Environment Variables" in the Start menu
   - Under System Variables → Path → Edit → New → paste `C:\ffmpeg\bin`
4. Open a new terminal and verify: `ffmpeg -version`

### 3. Install Python packages
Activate the project virtual environment first, then install:
```
E:\vdo2srt\venv\Scripts\activate
pip install -r requirements.txt
```

> **First run note:** Whisper will automatically download the model file the first time it runs.
> The `large-v3` model is ~3 GB. Download happens once and is cached for future runs.

---

## Running the Tool

### Option A — No arguments (recommended, GUI mode)
Double-click `vdo2srt.bat` or run it with no arguments. Two dialogs appear in sequence:

1. **File picker** — select your video or audio file
2. **Method picker** — choose how to transcribe:
   - **Local — GPU** (fast, offline — uses your NVIDIA GPU via CUDA)
   - **Local — CPU** (slow, offline — no GPU required)
   - **Google Cloud** (accurate, requires internet and credentials)

```
E:\vdo2srt\vdo2srt.bat
```

> **Note:** The file picker dialog may appear behind other windows — check the taskbar if nothing seems to happen.  
> **Note:** If an error occurs, the terminal stays open so you can read the message. Press any key to close it.

### Option B — Command line
Pass the file and options directly. Useful for scripting or batch processing.
```
E:\vdo2srt\vdo2srt.bat "E:\Movies\my_movie.mp4" --engine local --language ru
```

### Option C — Direct Python (venv must be active)
```
E:\vdo2srt\venv\Scripts\activate
python vdo2srt.py "E:\Movies\my_movie.mp4"
```

> **Common mistake:** Running `python vdo2srt.py` from the base conda environment (`(base)` in the
> prompt) will fail because the packages are installed in the venv, not in conda. Always activate
> the venv first, or use `vdo2srt.bat`.

---

## Quick Start Examples

### Transcribe a movie via GUI (no typing required)
```
E:\vdo2srt\vdo2srt.bat
```
Pick the file and method in the dialogs. Output SRT is written to the same folder as the video.

### Transcribe a Russian movie (command line)
```
E:\vdo2srt\vdo2srt.bat "E:\Movies\russian_movie.avi" --engine local --language ru
```

### Force GPU with a specific model
```
E:\vdo2srt\vdo2srt.bat "E:\Movies\my_movie.mp4" --engine local --device cuda --model large-v3
```

### Save the SRT to a specific location
```
E:\vdo2srt\vdo2srt.bat "E:\Movies\my_movie.mp4" --output "E:\Subtitles\movie_subtitles.srt"
```

---

## GPU Acceleration

If you have an NVIDIA GPU, transcription is dramatically faster with no setup needed —
the tool detects and uses CUDA automatically when you pick **Local — GPU**.

**Performance example (RTX 3060 Ti, 76-minute Russian film, large-v3 model):**

| Mode | Time |
|------|------|
| CPU only | ~4 hours |
| GPU (RTX 3060 Ti) | **2 minutes 22 seconds** |

GPU acceleration requires no extra installation — CUDA support is built into the
`faster-whisper` package included in `requirements.txt`.

---

## Using Google Cloud Speech-to-Text (Cloud Engine)

Use the cloud engine when local Whisper results are not accurate enough, or when
you want punctuation and word-level timestamps from Google's models.

### Requirements
1. A Google Cloud project with **Cloud Speech-to-Text API** enabled
2. A service account JSON key file for that project
3. **Billing must be enabled** on the Google Cloud project — Speech-to-Text is not available
   without a billing account, even for the free tier

### Current credentials file
```
E:\API Key\Google API Keys\speech2txt.json
```

### Run with the cloud engine
```
E:\vdo2srt\vdo2srt.bat "E:\Movies\my_movie.mp4" --engine cloud --language ru --credentials "E:\API Key\Google API Keys\speech2txt.json"
```

Or just run with no arguments and pick **Google Cloud** in the method dialog —
then pass `--credentials` if the environment variable is not set.

### Avoid typing the credentials path every time
Set it as a permanent Windows environment variable:
```powershell
[System.Environment]::SetEnvironmentVariable("GOOGLE_APPLICATION_CREDENTIALS", "E:\API Key\Google API Keys\speech2txt.json", "User")
```
Open a new terminal after running this. Then credentials are picked up automatically.

### Cloud engine language codes

| Language   | Code  |
|------------|-------|
| English    | en    |
| Russian    | ru    |
| Japanese   | ja    |
| Chinese    | zh    |
| Korean     | ko    |
| French     | fr    |
| German     | de    |
| Spanish    | es    |
| Thai       | th    |
| Vietnamese | vi    |
| Indonesian | id    |

---

## All Options

| Option | Description | Default |
|---|---|---|
| `input` | Video or audio file to process. Omit to open a file picker. | *(file picker)* |
| `--engine local` | Use local Whisper — works offline, uses GPU if available | *(method picker)* |
| `--engine cloud` | Use Google Cloud Speech-to-Text | |
| `--device` | `auto` / `cuda` / `cpu` — GPU device for local engine | auto |
| `--model` | Whisper model: tiny / base / small / medium / large-v2 / large-v3 | large-v3 |
| `--language` | Language code (e.g. en, ja, ru). Local auto-detects if omitted. | auto-detect |
| `--max-duration` | Split entries longer than N seconds at word boundaries. Pass `0` to disable. | 6 |
| `--credentials` | Path to Google service account JSON | env var |
| `--output` / `-o` | Output SRT file path | same folder as input |

---

## Choosing a Whisper Model

| Model | Size | GPU time* | CPU time* | Accuracy |
|-------|------|-----------|-----------|----------|
| tiny | 75 MB | <1 min | ~20 min | Low |
| base | 150 MB | ~1 min | ~35 min | Good |
| small | 470 MB | ~2 min | ~60 min | Better |
| medium | 1.5 GB | ~3 min | ~2 hrs | High |
| large-v3 | 3 GB | ~2–5 min | ~4 hrs | **Highest — default** |

*Approximate times for a 76-minute film on RTX 3060 Ti / Intel CPU.

**Default is `large-v3`** — best accuracy, and fast enough on GPU that there's no reason
to use a smaller model unless you're on CPU-only.

---

## Subtitle Entry Length (Splitting)

By default, entries longer than **6 seconds** are automatically split at word boundaries
so subtitles are easier to read. This uses Whisper's word-level timestamps to find natural
cut points — it never cuts mid-word, and prefers cutting between phrases.

### Adjust the threshold
```
# Tighter — better for fast dialogue
E:\vdo2srt\vdo2srt.bat "movie.mp4" --engine local --max-duration 4

# Looser — better for slow narration / monologues
E:\vdo2srt\vdo2srt.bat "movie.mp4" --engine local --max-duration 9

# Disable splitting entirely — raw Whisper segments
E:\vdo2srt\vdo2srt.bat "movie.mp4" --engine local --max-duration 0
```

Splitting applies to the **local engine only**. The cloud engine (Google STT) returns
its own segment boundaries and is not affected by `--max-duration`.

---

## Opening the SRT in SubtitleEdit

1. Open SubtitleEdit
2. File → Open → select your `.srt` file
3. Review timing: the waveform view shows exactly where each subtitle lands
4. To translate: Auto-translate → Google Translate (SubtitleEdit handles this built-in)
5. File → Save As to export the final SRT

---

## Troubleshooting

**"FFmpeg not found"**  
FFmpeg is not on your PATH. See the FFmpeg installation steps above.

**"faster-whisper is not installed"**  
Activate the venv first (`E:\vdo2srt\venv\Scripts\activate`) then run `pip install faster-whisper`.

**Running from wrong environment (packages not found)**  
Your prompt shows `(base)` instead of `(venv)`. Use `vdo2srt.bat` which handles this automatically,
or run `E:\vdo2srt\venv\Scripts\activate` before using `python vdo2srt.py`.

**"No speech detected"**  
The audio may be music-only or very low volume. Try opening it in a media player to confirm.

**Cloud: "403 Permission Denied" or "billing disabled"**  
Billing is not enabled on your Google Cloud project. Enable it in the Google Cloud Console.

**Cloud: "401 Unauthenticated"**  
The service account key may be revoked or invalid. Check the service account keys in the
Google Cloud Console under IAM & Admin → Service Accounts.

**Cloud: "Credentials file not found"**  
Double-check the path to your JSON file. Use quotes if the path contains spaces.

**Poor subtitle quality — garbage text, wrong languages, single characters**  
This is a Whisper hallucination on music or silent sections. It is fixed in the current version
via VAD filtering (`vad_filter=True`) which skips non-speech sections automatically.

**Poor subtitle quality — wrong words (not garbage)**  
The default `large-v3` model is already the most accurate. Try the cloud engine instead.

**Poor subtitle timing (text appears at wrong time)**  
The transcript is correct but timing is off. Open in SubtitleEdit and use the waveform
to adjust individual entries.
