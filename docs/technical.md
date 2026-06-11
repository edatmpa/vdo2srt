# vdo2srt — Technical Reference

## Architecture

```
vdo2srt.py           Thin wrapper — delegates to src/ package (backward-compatible entry point)
vdo2srt.bat          Windows launcher — activates venv automatically
src/
├── __init__.py      Package marker, version string
├── __main__.py      Entry point for `python -m src`
├── cli.py           CLI entry point — argument parsing, orchestration, batch/single-file routing
├── gui.py           Tkinter GUI dialogs — file/folder picker, method picker
├── extractor.py     FFmpeg wrapper — audio extraction and chunking
├── transcriber.py   Transcription engines — faster-whisper (local) and Google STT (cloud)
├── translator.py    Subtitle translation via Google Translate (batched, retry logic)
├── srt_writer.py    SRT formatter — converts segments to subtitle file
└── utils.py         Shared constants (SUPPORTED_EXTENSIONS) and helpers (find_media_files)
```

---

## Pipeline

```
Input file (any video/audio format)
    │
    ▼  [optional] gui.pick_file() / gui.pick_folder() — if no input arg given
    │
    ▼  [optional] gui.pick_method() — if --engine not given
    │
    ▼  extractor.extract_audio()
Normalized 16kHz mono WAV  (temp file under _TEMP_DIR)
    │
    ├── engine=local ──► LocalTranscriber.transcribe()
    │                        faster-whisper (CTranslate2) → segments
    │                        [if max_duration set] word_timestamps=True
    │                        split_segments() re-cuts at word boundaries → segments
    │
    └── engine=cloud ──► CloudTranscriber.transcribe()
                              split into 55s chunks via extractor.extract_chunk()
                              Google STT API per chunk
                              reassemble with timestamp offsets → segments
    │
    ▼  srt_writer.write_srt()
output.srt  (same folder as input by default)
```

---

## Module Reference

### `vdo2srt.py` (root)

Thin wrapper that adds the project root to `sys.path` and delegates to `src.cli.main()`.
Kept for backward compatibility — all existing scripts and the `.bat` launcher continue to work.

### `src/__main__.py`

Allows running the package directly: `python -m src`

### `src/cli.py`

Entry point for the application. Handles argument parsing and orchestration.

#### `build_parser() → argparse.ArgumentParser`
Constructs the argument parser with all CLI flags.

#### `parse_args(argv=None) → argparse.Namespace`
Parses command-line arguments. Accepts an optional list for testing.

#### `process_file(input_path, output_path, transcriber, translate, target_lang) → bool`
Core processing pipeline for a single file:
1. `extract_audio()` → WAV
2. `transcriber.transcribe()` → segments
3. `write_srt()` → `.srt`
4. (if translate) `translate_segments()` → `.{target_lang}.srt`

#### `main(argv=None) → None`
Main entry point. Resolves input (CLI arg or GUI dialog), engine (CLI arg or GUI dialog),
then routes to single-file or batch mode.

### `src/gui.py`

Tkinter GUI dialogs used when arguments are omitted.

#### `make_root() → tk.Tk`
Creates a withdrawn, always-on-top Tk root used by all dialogs.

#### `pick_target_type(root) → str`
Two-button dialog: "Single video / audio file" or "Entire folder (batch)". Returns `'file'` or `'folder'`.

#### `pick_file(root) → Path`
Standard Windows file-open dialog. Filters for common video/audio extensions.
Exits with code 0 if the user cancels.

#### `pick_folder(root) → Path`
Standard Windows folder picker. Exits with code 0 if cancelled.

#### `pick_method(root) → tuple[str, str]`
Three-button window returning `(engine, device)`:

| Button | engine | device |
|---|---|---|
| Local — GPU | `local` | `cuda` |
| Local — CPU | `local` | `cpu` |
| Google Cloud | `cloud` | `auto` |

Closing the window exits the process.

The dialogs only appear when the corresponding argument is absent.
Passing `--engine` on the command line skips `pick_method()`; passing a positional
`input` argument skips `pick_file()`.

---

### `src/extractor.py`

#### `_TEMP_DIR`
Module-level constant: `Path(tempfile.gettempdir()) / "vdo2srt"`.
Both `extract_audio` and `extract_chunk` write here.

#### `check_ffmpeg() → bool`
Returns `True` if FFmpeg is available on the system PATH.

#### `get_duration(audio_path: Path) → float`
Uses `ffprobe` to return audio duration in seconds.

#### `extract_audio(input_path: Path) → Path`
Extracts and normalizes audio from any video or audio file.

- Output format: PCM signed 16-bit little-endian WAV
- Sample rate: 16,000 Hz (required by both Whisper and Google STT)
- Channels: mono
- Output location: `_TEMP_DIR / <stem>_16k.wav`
- Raises `EnvironmentError` if FFmpeg is not found
- Raises `RuntimeError` on FFmpeg failure

#### `extract_chunk(audio_path: Path, start_sec: float, duration_sec: float) → Path`
Extracts a time slice from a WAV file. Used by `CloudTranscriber` for chunked API calls.
Returns path to `_TEMP_DIR / chunk_<offset>.wav`.

---

### `src/transcriber.py`

Top-level imports: `tqdm`, `get_duration`, `extract_chunk` are imported at module level
(not inside methods) so import errors appear at startup rather than mid-run.

#### `LocalTranscriber`
Wraps the `faster-whisper` library (CTranslate2 backend — faster and lower memory than openai-whisper).

**Constructor parameters:**
- `model` (str): Whisper model name. Options: `tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3`. Default: `large-v3`
- `language` (str | None): BCP-47 short code (e.g. `ru`, `ja`). `None` triggers auto-detection.
- `device` (str): `auto` | `cuda` | `cpu`. `auto` uses CUDA if available, else CPU.
- `max_duration` (float | None): If set, enables word-timestamp mode and splits any segment longer than this many seconds at word boundaries. Default: `6.0`. Pass `None` to disable.

**`transcribe(audio_path: Path) → list[dict]`**  
Returns a list of segment dicts: `{start: float, end: float, text: str}`

When `max_duration` is set, Whisper is called with `word_timestamps=True` and the raw segments are passed through `split_segments()` before being returned.

The model is lazy-loaded on first call. Weights are downloaded automatically from Hugging Face
if not already cached.

**Model storage location (Windows):**  
`%USERPROFILE%\.cache\huggingface\hub\models--Systran--faster-whisper-<model>\`

**Transcription settings:**

| Setting | Value | Purpose |
|---|---|---|
| `beam_size` | 5 | Beam search width — balances speed vs accuracy |
| `vad_filter` | True | Skips non-speech sections; prevents hallucinations in music/silence |
| `condition_on_previous_text` | False | Stops a bad segment from poisoning the next one |

**GPU vs CPU compute types:**

| Device | `compute_type` | Notes |
|---|---|---|
| CPU | `int8` | Quantized — fast and memory-efficient on CPU |
| GPU (CUDA) | `int8_float16` | Quantized weights, float16 compute — best quality/speed on GPU |

> `float16` (pure) is faster on GPU but causes hallucinations on noisy/musical audio.
> `int8_float16` produces quality equivalent to CPU `int8` at ~18x the speed.

**Tested performance (RTX 3060 Ti, 76-min Russian film):**

| Model | Mode | Time | vs realtime |
|---|---|---|---|
| base | GPU (`int8_float16`) | ~1 min | ~76x |
| large-v3 | GPU (`int8_float16`) | ~2 min 22s | ~32x |
| large-v3 | CPU (`int8`) | ~4 hrs | ~0.3x |

---

#### `CloudTranscriber`
Wraps Google Cloud Speech-to-Text v1 API via the `google-cloud-speech` Python client library.

**Constructor parameters:**
- `credentials_path` (str | None): Path to service account JSON key file.  
  Falls back to the `GOOGLE_APPLICATION_CREDENTIALS` environment variable.
- `language` (str | None): Language code. Defaults to `"en"` if not provided.  
  Short codes (e.g. `"ja"`) are mapped to BCP-47 (e.g. `"ja-JP"`) internally.

**Class constant:**
- `CHUNK_DURATION = 55` — seconds per chunk, safely under the 60s sync API limit.

**`transcribe(audio_path: Path) → list[dict]`**  
Splits the audio into 55-second chunks, sends each to the Google STT synchronous API,
and returns a combined list of segments with accurate timestamps.

**Chunking strategy:**  
Google's synchronous `recognize` endpoint accepts audio up to 60 seconds.
Each chunk is extracted by `extractor.extract_chunk()`, sent inline in the request body,
and the returned word-level timestamps are adjusted by the chunk's start offset.
This avoids requiring Google Cloud Storage for long files.

**Recognition config:**
```python
RecognitionConfig(
    encoding=LINEAR16,
    sample_rate_hertz=16000,
    language_code=<bcp47>,
    enable_word_time_offsets=True,
    enable_automatic_punctuation=True,
)
```

**BCP-47 language mappings:**

| Short code | Full code |
|------------|-----------|
| en | en-US |
| ja | ja-JP |
| zh | zh-CN |
| ko | ko-KR |
| fr | fr-FR |
| de | de-DE |
| es | es-ES |
| it | it-IT |
| pt | pt-BR |
| ru | ru-RU |
| ar | ar-SA |
| hi | hi-IN |
| th | th-TH |
| vi | vi-VN |
| id | id-ID |
| ms | ms-MY |

---

#### `split_segments(segments: list[dict], max_duration: float) → list[dict]`
Re-cuts segments that exceed `max_duration` seconds, splitting at word boundaries.

- Segments at or under `max_duration` are passed through unchanged.
- Segments without word data (e.g. from the cloud engine) are passed through unchanged.
- Uses a greedy algorithm: accumulates words into a chunk; flushes to a new entry whenever adding the next word would exceed `max_duration`.
- Word text is joined with `"".join(w.word ...).strip()` — faster-whisper includes leading spaces on each word token, so joining produces natural spacing.

#### `get_transcriber(engine, model, language, credentials, device, max_duration) → LocalTranscriber | CloudTranscriber`
Factory function called by `cli.py`. Returns the correct transcriber instance.
`max_duration` is forwarded to `LocalTranscriber` only; `CloudTranscriber` ignores it.

---

### `src/srt_writer.py`

#### `write_srt(segments: list[dict], output_path: Path) → int`
Writes SRT-formatted subtitle file. Returns the number of entries written.

**SRT format produced:**
```
1
00:00:01,000 --> 00:00:04,500
First subtitle text

2
00:00:05,200 --> 00:00:08,000
Second subtitle text
```

- Encoding: UTF-8 (required for non-Latin scripts)
- Empty or whitespace-only segments are skipped
- Timestamps are clamped to ≥ 0

---

### `src/translator.py`

#### `translate_segments(segments, target_lang="en", source_lang="auto") → list[dict]`
Translates segment text using `deep-translator` (Google Translate, no API key).
Returns new segments with translated text but original timing.

**Batching strategy:**
- Segments are grouped in batches of 20 (`_BATCH_SIZE`)
- Each batch is joined with ` ||| ` separator for a single HTTP call
- If the separator is mangled in translation, falls back to one request per segment
- Retries up to 3 times (5s, 10s, 15s backoff) on network errors

---

### `src/utils.py`

#### `SUPPORTED_EXTENSIONS`
Set of supported file extensions (`.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.m4v`, `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`).

#### `is_media_file(path: Path) → bool`
Returns `True` if the path is a file with a supported media extension (case-insensitive).

#### `find_media_files(folder: Path) → list[Path]`
Returns a sorted list of supported media files inside the given folder.

---

## Dependencies

| Package | Purpose | Required |
|---|---|---|
| `faster-whisper` | Local speech-to-text (CTranslate2 backend) | Always |
| `ctranslate2` | Inference engine for faster-whisper | Always (installed automatically) |
| `tqdm` | Progress bars | Always |
| `ffmpeg` (system) | Audio extraction | Always |
| `google-cloud-speech` | Google STT client | Cloud engine only |
| `google-auth` | Service account authentication | Cloud engine only |

> `torch` / `torchvision` are **not** required. faster-whisper uses CTranslate2 instead of PyTorch.

---

## Google Cloud Setup

### Credentials file
Current credentials: `E:\API Key\Google API Keys\speech2txt.json`

### APIs required
Both must be enabled on the Google Cloud project:
- **Cloud Speech-to-Text API** — for audio transcription
- Billing must be enabled on the project (Speech-to-Text is not available on the free tier without billing)

### Authentication flow
`CloudTranscriber` loads credentials using `google.oauth2.service_account.Credentials`
with the `cloud-platform` scope, which covers all Google Cloud APIs.

### Google STT pricing (as of 2025)
- First 60 minutes per month: free
- Standard model: ~$0.004 per 15 seconds (~$0.96/hour)
- A 76-minute movie ≈ 83 chunks × ~$0.004 = ~$0.33

---

## Temp File Locations

| File | Location |
|---|---|
| Extracted audio WAV | `%TEMP%\vdo2srt\<stem>_16k.wav` |
| Chunk WAVs (cloud) | `%TEMP%\vdo2srt\chunk_<offset>.wav` |

Temp files are not automatically deleted after a run, allowing re-use if you run
multiple engine/language combinations on the same source file.

---

## Extending the Tool

### Adding a new cloud engine (e.g. Azure Speech)
1. Create a new class in `src/transcriber.py` following the same interface:
   - Constructor accepts `language` and credential parameters
   - `transcribe(audio_path: Path) → list[dict]` returns `[{start, end, text}]`
2. Add the new engine name to the `get_transcriber()` factory
3. Add the new `--engine` choice to `src/cli.py`'s argument parser

### Changing chunk duration for Google STT
Adjust `CHUNK_DURATION` in the `CloudTranscriber` class body. Must remain below 60 seconds
for the synchronous API. For async API with GCS support, this limit does not apply.
