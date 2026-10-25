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
"E:\Plex Utility\vdo2srt\venv\Scripts\activate"
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
"E:\Plex Utility\vdo2srt\vdo2srt.bat"
```

> **Note:** The file picker dialog may appear behind other windows — check the taskbar if nothing seems to happen.  
> **Note:** If an error occurs, the terminal stays open so you can read the message. Press any key to close it.

### Option B — Command line
Pass the file and options directly. Useful for scripting or batch processing.
```
"E:\Plex Utility\vdo2srt\vdo2srt.bat" "E:\Movies\my_movie.mp4" --engine local --language ru
```

### Option C — Direct Python (venv must be active)
```
"E:\Plex Utility\vdo2srt\venv\Scripts\activate"
python vdo2srt.py "E:\Movies\my_movie.mp4"
```

### Option D — Module entry point
```
"E:\Plex Utility\vdo2srt\venv\Scripts\activate"
python -m src "E:\Movies\my_movie.mp4" --engine local
```

> **Common mistake:** Running `python vdo2srt.py` from the base conda environment (`(base)` in the
> prompt) will fail because the packages are installed in the venv, not in conda. Always activate
> the venv first, or use `vdo2srt.bat`.

---

## Quick Start Examples

### Transcribe a movie via GUI (no typing required)
```
"E:\Plex Utility\vdo2srt\vdo2srt.bat"
```
Pick the file and method in the dialogs. Output SRT is written to the same folder as the video.

### Transcribe a Russian movie (command line)
```
"E:\Plex Utility\vdo2srt\vdo2srt.bat" "E:\Movies\russian_movie.avi" --engine local --language ru
```

### Force GPU with a specific model
```
"E:\Plex Utility\vdo2srt\vdo2srt.bat" "E:\Movies\my_movie.mp4" --engine local --device cuda --model large-v3
```

### Save the SRT to a specific location
```
"E:\Plex Utility\vdo2srt\vdo2srt.bat" "E:\Movies\my_movie.mp4" --output "E:\Subtitles\movie_subtitles.srt"
```

### Batch process an entire folder
```
"E:\Plex Utility\vdo2srt\vdo2srt.bat" "E:\Movies" --engine local --language ru
```
All supported video/audio files in the folder are processed. Each gets its own `.srt` (and `.en.srt`) next to the original.

Files that already have a `.srt` are **not** re-transcribed — voice-to-text never runs again on them — but they *are* still checked for translation: if the `.en.srt` is missing, it gets translated from the existing `.srt`. Any leftover `.srt` with no matching video at all (the video was moved or deleted after transcription) is picked up the same way. Add `--overwrite` to force a full re-transcribe of everything (and retranslate/replace existing `.en.srt` files too — the previous translation is backed up to `.bak` first).

### Skip the English translation
```
"E:\Plex Utility\vdo2srt\vdo2srt.bat" "E:\Movies\film.mkv" --engine local --language ru --no-translate
```

### Translate to a language other than English
```
"E:\Plex Utility\vdo2srt\vdo2srt.bat" "E:\Movies\film.mkv" --engine local --language ru --target-language fr
```

---

## Batch Processing Many Folders (process_list)

Use `process_list.bat` when you have a whole list of folders to process — e.g. a "no subs" export from your own library-scanning tooling (that list's generation is your own tool; `process_list.py` just consumes it).

The list file is plain text, one folder path per line (optionally numbered, e.g. from a numbered export):
```
1. V:\Korean\Movie Title (2022) 1080p
2. V:\Korean\Another Movie (2023)
```
Hidden folders and known non-movie folder names (`Extras`, `Featurettes`, `Behind the Scenes`, etc.) are skipped automatically.

```
"E:\Plex Utility\vdo2srt\process_list.bat" "E:\no_subs.txt" --engine local --language ru
```

Per folder, this behaves exactly like `vdo2srt.bat`'s folder mode: videos with no `.srt` yet get transcribed; videos that already have a `.srt` are translated only (voice-to-text never re-runs); any leftover `.srt` with no matching video is translated too. `--overwrite` forces a full re-transcribe and retranslates/replaces existing `.en.srt` files (backed up to `.bak` first).

No arguments opens a GUI picker for the list file, same as `vdo2srt.bat`.

---

## Translating Existing Subtitles Only (translate_srt)

Use `translate_srt.bat` when the `.srt` files already exist (in the original language) and you just want a translation — no video, no transcription involved at all. This is also the tool to use to **retranslate** subtitles that already have a weaker translation, now that DeepL is available for several languages.

```
:: Single file
"E:\Plex Utility\vdo2srt\translate_srt.bat" "movie.srt"

:: One folder
"E:\Plex Utility\vdo2srt\translate_srt.bat" "V:\Korean\Movie Title (2022)"

:: A whole library — root -> movie/show folders -> files (one level, not arbitrary depth)
"E:\Plex Utility\vdo2srt\translate_srt.bat" "V:\War Series (Russia)" --recursive

:: Retranslate and replace existing translations across that library
"E:\Plex Utility\vdo2srt\translate_srt.bat" "V:\War Series (Russia)" --recursive --overwrite
```

By default, an `.srt` whose `.en.srt` (or other `--target-language`) already exists is skipped. `--overwrite` retranslates and replaces it — the previous translation is backed up to `<name>.srt.bak` first, so nothing is lost if the new translation turns out worse.

No arguments opens a GUI picker (single file or folder — `--recursive` must be passed on the command line, there's no picker option for it).

---

## Choosing a Translation Engine

Which engine translates a file is chosen **automatically**, based on the subtitle's own text — not on `--language` or Whisper's guess. This matters most for `process_list.bat`/`translate_srt.bat`, where an existing `.srt` may carry no language information at all.

- The source language is **detected from the subtitle text itself**.
- `translate_routing.txt` (in the project root) maps a detected language to a **chain** of engines and key files, tried top to bottom (Japanese shown; `ko`, `zh`, `ru` are the same):
  ```
  ja    deepl       E:\API Key\Key files\platform\deepl.saksiri.txt
  ja    deepseek    E:\API Key\Key files\platform\deepseek.saksiri.txt
  ja    deepseek    E:\API Key\Key files\platform\deepseek.saksiri2.txt
  ```
- When a key runs out of quota/credit (or is rejected) — even halfway through a file — the tool prints a note, skips that key for the rest of the run, and carries on with the next line. Free Google is always the final step, so a batch never stops just because a paid key is empty.
- Any language **not** listed there automatically uses the free, keyless engine (Google Translate via `deep-translator`) — nothing to configure.
- **To reorder engines, add a key, or route a new language, just add/edit lines in `translate_routing.txt`.** No code change needed.
- DeepL's free API plan gives 1,000,000 characters per monthly billing period. Measured: a ~46-min Japanese episode is ≈ 4,300 characters (≈ 230 episodes per month); a Russian episode was ≈ 60,000 (≈ 16).

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
"E:\Plex Utility\vdo2srt\vdo2srt.bat" "E:\Movies\my_movie.mp4" --engine cloud --language ru --credentials "E:\API Key\Google API Keys\speech2txt.json"
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

### `vdo2srt.py` / `process_list.py`

| Option | Description | Default |
|---|---|---|
| `input` / `list_file` | Video/audio file, folder, or (`process_list.py`) a folder-list `.txt`. Omit to open a picker. | *(picker)* |
| `--engine local` | Use local Whisper — works offline, uses GPU if available | *(method picker)* |
| `--engine cloud` | Use Google Cloud Speech-to-Text | |
| `--device` | `auto` / `cuda` / `cpu` — GPU device for local engine | auto |
| `--model` | Whisper model: tiny / base / small / medium / large-v2 / large-v3 | large-v3 |
| `--language` | Language code (e.g. en, ja, ru). Local auto-detects if omitted. | auto-detect |
| `--max-duration` | Split entries longer than N seconds at word boundaries. Pass `0` to disable. | 6 |
| `--no-translate` | Skip the automatic translation | off (translate) |
| `--target-language` | Translate into this language instead of English | en |
| `--credentials` | Path to Google service account JSON | env var |
| `--output` / `-o` | Output SRT file path (`vdo2srt.py` single-file mode only) | same folder as input |
| `--overwrite` | Re-transcribe files that already have a `.srt`, **and** retranslate/replace existing `.en.srt` (backed up to `.bak` first) | off |

### `translate_srt.py`

| Option | Description | Default |
|---|---|---|
| `input` | A `.srt` file, a folder, or (with `--recursive`) a library root. Omit to open a picker. | *(picker)* |
| `--recursive` | Treat `input` as a library root and scan each immediate subfolder (movie/show folders) | off |
| `--target-language` | Language to translate into | en |
| `--overwrite` | Retranslate and replace existing translations (backed up to `.bak` first) | off |

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
"E:\Plex Utility\vdo2srt\vdo2srt.bat" "movie.mp4" --engine local --max-duration 4

# Looser — better for slow narration / monologues
"E:\Plex Utility\vdo2srt\vdo2srt.bat" "movie.mp4" --engine local --max-duration 9

# Disable splitting entirely — raw Whisper segments
"E:\Plex Utility\vdo2srt\vdo2srt.bat" "movie.mp4" --engine local --max-duration 0
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
Activate the venv first (`"E:\Plex Utility\vdo2srt\venv\Scripts\activate"`) then run `pip install faster-whisper`.

**Running from wrong environment (packages not found)**  
Your prompt shows `(base)` instead of `(venv)`. Use `vdo2srt.bat` which handles this automatically,
or run `"E:\Plex Utility\vdo2srt\venv\Scripts\activate"` before using `python vdo2srt.py`.

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

**"deepl is not installed" / "deep-translator is not installed" / "langdetect is not installed"**  
Activate the venv, then `pip install -r requirements.txt` — these are all in the core requirements now.

**Translation used the free engine when I expected DeepL**  
Check `translate_routing.txt` — the detected source language must be listed there to route to DeepL. If it's listed but still fell back, the console prints why (missing/empty key file, or `deepl` not installed) right before the translation runs.

**I want to redo an old translation with DeepL instead of the original engine**  
Run `translate_srt.bat` on the file/folder/library with `--overwrite`. The previous `.en.srt` is backed up to `.en.srt.bak` before being replaced, so nothing is lost.
