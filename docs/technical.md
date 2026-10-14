# vdo2srt — Technical Reference

## Architecture

```
vdo2srt.py           Single file / one folder — delegates to src/cli.py (backward-compatible entry point)
vdo2srt.bat          Windows launcher — activates venv automatically; menu also offers translate_srt
process_list.py      Batch over many folders read from a plain-text list file (one path per line)
process_list.bat     Windows launcher
translate_srt.py     Translate existing .srt files — no video, no transcription at all
translate_srt.bat    Windows launcher
translate_routing.txt  Per-language translation engine routing (edit to add/move a language)
src/
├── __init__.py      Package marker, version string
├── __main__.py      Entry point for `python -m src`
├── cli.py           vdo2srt.py's CLI — argument parsing, orchestration, batch/single-file routing
├── gui.py           Tkinter GUI dialogs — file/folder picker, method picker
├── extractor.py     FFmpeg wrapper — audio extraction and chunking
├── transcriber.py   Transcription engines — faster-whisper (local) and Google STT (cloud)
├── translator.py    Translation engines (DeepL / free fallback), per-language routing, translate_existing_srt()
├── srt_reader.py    Parses an existing .srt file back into segment dicts
├── srt_writer.py    SRT formatter — converts segments to subtitle file
└── utils.py         Shared file-discovery helpers and a backup-before-overwrite helper
```

**Three entry points, one shared `src/` package.** `vdo2srt.py` handles a single file or one folder (full transcribe+translate pipeline). `process_list.py` does the same, but across every folder named in a text list file (that list's *generation* is the user's own separate tooling — not this project's concern; this script only consumes it). `translate_srt.py` is pure text-to-text — no video, no transcription — for retranslating/replacing `.srt` files that already exist, deliberately built on `src/translator.py` alone so it never imports `src/transcriber.py` (and therefore never pulls in faster-whisper) just to translate text.

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
    │
    ▼  [unless --no-translate]  translator.translate_segments()
output.{target_lang}.srt
```

**Translate-only path** (existing `.srt`, no transcription — `cli.py` batch mode's `to_translate_only`/orphan handling, all of `process_list.py`, and the whole of `translate_srt.py`):
```
existing .srt  ──►  srt_reader.read_srt()  ──►  translator.translate_segments()  ──►  srt_writer.write_srt()
```
`translator.translate_existing_srt(srt_path, target_lang, overwrite)` wraps exactly this: skip if the target already exists (unless `overwrite`, which backs it up to `.bak` first via `utils.backup_if_exists` before replacing it).

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
4. (if translate) `backup_if_exists()` on the translated path, then `translate_segments()` → `.{target_lang}.srt`

#### `main(argv=None) → None`
Main entry point. Resolves input (CLI arg or GUI dialog), engine (CLI arg or GUI dialog),
then routes to single-file or batch mode.

**Batch mode's three-way split** (folder input): given `find_media_files(folder)` and `find_original_srt_files(folder)`,
- `to_transcribe` — media with no `.srt` yet (or any media, if `--overwrite`) → full `process_file()` pipeline. Voice-to-text only ever runs here.
- `to_translate_only` — media whose `.srt` already exists (and `--overwrite` wasn't given) → `translate_existing_srt()`, no re-transcription.
- **orphan `.srt`s** — original `.srt` files with no matching media file at all in the folder (video moved/deleted after a previous run) → also `translate_existing_srt()`, independent of `--overwrite`'s effect on the media-side split.

`--overwrite` therefore means two different things depending on which stage a file is in: for a video with an existing `.srt`, it forces a full re-transcribe (unchanged, pre-existing behavior); for anything routed through `translate_existing_srt()`, it forces a retranslation with a `.bak` backup of the previous output.

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

### `src/srt_reader.py`

#### `read_srt(srt_path: Path) → list[dict]`
Parses an existing `.srt` file back into segment dicts (`{start, end, text}`), the inverse of `srt_writer.write_srt()`. Powers every translate-only path — reading a subtitle file that already exists so it can be fed back through `translate_segments()`.

---

### `src/translator.py`

Pluggable translation engines, routed **per detected source language** — not `--language`/Whisper's guess, since the translate-only paths (existing `.srt`, no fresh transcription) often have no language metadata available at all.

#### `detect_source_language(segments) → str`
Runs `langdetect` on a concatenated sample of the first ~30 non-empty segment texts (capped at 2000 chars) — not per line, since a single subtitle line ("Yes.") is usually too short to detect reliably alone. Normalizes langdetect's regional variants (`zh-cn`, `zh-tw`) down to the base code (`zh`). Returns `"auto"` if detection isn't possible (empty sample, or the exception `langdetect` raises on gibberish input).

#### `translate_routing.txt` (repo root) — the routing table
One line per source language: `<lang>  <engine>  <key_file>`. Parsed by `_load_routing()` into `{lang: (engine_name, key_file_or_None)}`. Comments (`#`) and blank lines are skipped. A language not listed here isn't an error — it just isn't in the dict, and `get_translator()` treats that the same as an explicit `google` entry.

**Current routing:** `ko`, `ja`, `zh`, `ru` → `deepl` + `E:\API Key\Key files\platform\deepl.saksiri.txt`. Everything else falls back to the free engine automatically.

**To add or move a language, edit this file — no code change.** Adding a genuinely new engine *type* (not just a new language) means one new class below plus one entry in the `_ENGINES` registry.

#### Engine classes
Both implement `translate_batch(texts: list[str], source_lang: str, target_lang: str) -> list[str]`.

- **`DeepLEngine(key_file)`** — wraps the official `deepl` package. Reads the key file's first line as the secret (2-line format: line 1 = secret, line 2 = optional endpoint — see `E:\API Key\AGENTS.md`); the endpoint line is not actually used since `deepl.Translator` auto-selects the free/pro API host from the key's `:fx` suffix. Sends the whole batch (up to `_BATCH_SIZE`) to DeepL in one call — DeepL's list-input API needs no join/split trick. Target language `en` is special-cased to `EN-US` (DeepL rejects a bare `en` as a target; add more entries to `_DEEPL_TARGET_OVERRIDES` for other regional variants later). Source language is upper-cased and passed through (DeepL doesn't use regional variants for source).
- **`GoogleEngine()`** — wraps `deep_translator.GoogleTranslator`, free, no key. Since that API is one-string-at-a-time, batches are joined with `" ||| "`, sent as one string, then split back — the same trick the original single-engine implementation used. Caches one `GoogleTranslator` sub-instance per `(source_lang, target_lang)` pair it's asked to translate, since those don't change within one file's batches.

#### `get_translator(source_lang) → engine instance`
Resolves the routing table entry for `source_lang`, instantiates (and caches, keyed by `"{engine}:{key_file}"`) the right engine. Degrades gracefully — with a printed note, never a crash — if: the routed engine name is unknown, the `deepl` package isn't installed, or the key file is missing/empty. Every failure mode falls back to `GoogleEngine`, so a config typo or a moved key file never aborts a batch run.

#### `translate_segments(segments, target_lang="en", source_lang=None) → list[dict]`
The shared public entry point. `source_lang=None` (or `"auto"`) triggers `detect_source_language()`; an explicit value skips detection. Batches of 20 (`_BATCH_SIZE`) are handed to whichever engine `get_translator()` resolved. Retries up to 3 times (2s, 4s, 8s backoff) on any error, at the engine-call level (`_call_with_retry`, shared by both engines).

#### `translate_existing_srt(srt_path, target_lang, overwrite=False) → bool`
`read_srt()` → `translate_segments()` → `write_srt()` to `<stem>.<target_lang>.srt`. If that output already exists: skipped and returns `True` unless `overwrite=True`, in which case the previous translation is backed up to `<name>.srt.bak` (`utils.backup_if_exists`) before being replaced. This one function is the shared workhorse behind `cli.py`'s translate-only/orphan handling, all of `process_list.py`, and all of `translate_srt.py` — deliberately kept independent of `cli.py`/`transcriber.py` so a pure text-translation run never imports faster-whisper.

---

### `src/utils.py`

#### `find_media_files(folder: Path) → list[Path]`
Returns a sorted list of files in `folder` (non-recursive) matching the internal `_MEDIA_EXTENSIONS` set (`.mp4`, `.mkv`, `.avi`, `.mov`, `.flv`, `.wmv`, `.webm`, `.m4v`, `.mp3`, `.wav`, `.aac`, `.flac`, `.m4a`, `.wma`, `.ogg`, `.opus`).

#### `find_original_srt_files(folder: Path) → list[Path]`
Returns `.srt` files in `folder` (non-recursive) that *aren't* already a translation output — i.e. excludes any file whose name ends in a language-code-shaped suffix (`movie.en.srt`, `movie.zh-cn.srt`, matched by `_LANG_SUFFIX_RE`). A 3+ letter release tag (`Holod.S01E01.AVC.srt`) never collides with this — the regex requires exactly 2 letters (optionally `xx-xx`) right before `.srt`. Used everywhere an "is this an original subtitle or already a translation" decision is needed: orphan-`.srt` detection in `cli.py`/`process_list.py`, and the whole scanning logic in `translate_srt.py`.

#### `is_skippable_folder(folder: Path) → bool`
True for hidden folders (name starts with `.`) or a known non-movie folder name (`_SKIP_NAMES`: Extras, Featurettes, Behind the Scenes, Deleted Scenes, Interviews, Scenes, Shorts, Trailers, Thumbs, Folder). Shared by `process_list.py`'s list-file parsing and `find_movie_subfolders()` below, so both agree on what to walk past.

#### `find_movie_subfolders(root: Path) → list[Path]`
Returns the immediate (non-recursive) subfolders of `root`, filtered through `is_skippable_folder()`. This is the one-level "library root → movie folders" walk `translate_srt.py --recursive` uses — deliberately not an arbitrary-depth walk, since the real library shape is exactly two levels (`root → movie/show folder → video + srt files`).

#### `backup_if_exists(path: Path) → Path | None`
If `path` exists, copies it to `<name>.bak` (overwriting any previous backup) and returns that backup path; no-op (returns `None`) otherwise. Used before any `write_srt()` call that might silently clobber an existing translation — in `process_file()` unconditionally (harmless no-op on a first-time run) and in `translate_existing_srt()` when `overwrite=True`.

---

## Dependencies

| Package | Purpose | Required |
|---|---|---|
| `faster-whisper` | Local speech-to-text (CTranslate2 backend) | Always |
| `ctranslate2` | Inference engine for faster-whisper | Always (installed automatically) |
| `tqdm` | Progress bars | Always |
| `deepl` | DeepL translation engine, routed per `translate_routing.txt` | Always |
| `deep-translator` | Free Google Translate fallback engine (no API key) | Always |
| `langdetect` | Source-language detection for translation routing | Always |
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

### Adding or moving a translation language (no code change)
Add a line to `translate_routing.txt`: `<lang>  <engine>  <key_file>`. `<lang>` should match what `langdetect` emits (ISO 639-1, e.g. `ja` not `jp`, `zh` not `cn`). To move an existing language to a different key or a different engine, just edit its line. Anything not listed automatically falls back to the free engine — no entry needed for that.

### Adding a new translation engine type
1. Create a new class in `src/translator.py` implementing `translate_batch(texts, source_lang, target_lang) -> list[str]`, following `DeepLEngine`'s or `GoogleEngine`'s shape (constructor takes whatever the engine needs — a key file, credentials, nothing at all).
2. Add it to the `_ENGINES` registry dict.
3. Reference its name in `translate_routing.txt` for whichever language(s) should use it.

No changes are needed to `cli.py`, `process_list.py`, or `translate_srt.py` — they all call `translate_segments()`/`translate_existing_srt()`, which resolve the engine internally.

---

## `process_list.py` (root)

Batch entry point for many folders at once, read from a plain-text list file (one path per line, optionally numbered like `"1. V:\Korean\Movie Title (2022)"` — see its own docstring). The list file's *generation* (e.g. a "no subs" export from the user's separate library-scanning tooling) is out of scope for this project.

Per folder, applies the same three-way split as `cli.py`'s batch mode (`to_transcribe` / `to_translate_only` / orphan `.srt`s — see above), accumulating results across every folder in the list before printing a final summary. The transcriber (`get_transcriber()`) is loaded once, lazily — skipped entirely if every pending item across all folders turns out to be translation-only, so a list file of already-transcribed folders never even initializes Whisper/CUDA.

`is_skippable_folder()` (from `utils.py`) filters junk entries out of the parsed list itself (hidden folders, `Extras`, etc.), in addition to being applied per-folder during the scan.

---

## `translate_srt.py` (root)

Pure text-to-text entry point — never imports `src/cli.py` or `src/transcriber.py`, so running it never touches faster-whisper/CUDA at all. Three input shapes, auto-detected from the path:
- A `.srt` file → translates that one file.
- A folder → `find_original_srt_files(folder)`, translate each missing its `<target_lang>.srt`.
- A folder with `--recursive` → treated as a library root; `find_movie_subfolders(root)` walks one level down (not arbitrary depth), scanning each subfolder the same way.

Falls back to a small self-contained Tkinter picker (file vs. folder) when run with no arguments — deliberately not sharing `src/gui.py`'s pickers, since those are filtered for video/audio extensions, not `.srt`. `--overwrite` here means exactly what `translate_existing_srt()`'s `overwrite` parameter means: retranslate and replace, backing up the previous output to `.bak` first.
