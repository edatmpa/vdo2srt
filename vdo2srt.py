"""
vdo2srt — Convert a video/audio file (or all files in a folder) to SRT subtitle files.

Usage (GUI):  Double-click vdo2srt.bat — prompts for file/folder then transcription method
Usage (CLI):  python vdo2srt.py <file_or_folder> [options]

An English-translated .en.srt is produced alongside the original .srt by default.
Pass --no-translate to skip translation.

Engines:
    local  (default) — faster-whisper, runs entirely on your machine
    cloud            — Google Cloud Speech-to-Text, requires service account JSON
"""

import argparse
import sys
from pathlib import Path

from extractor import extract_audio
from transcriber import get_transcriber
from srt_writer import write_srt
from translator import translate_segments

SUPPORTED_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".m4v",
    ".mp3", ".wav", ".m4a", ".flac", ".ogg",
}


# ---------------------------------------------------------------------------
# GUI helpers
# ---------------------------------------------------------------------------

def _make_root():
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update()
    return root


def _clear(root):
    for widget in root.winfo_children():
        widget.destroy()


def _pick_target_type(root) -> str:
    """Ask whether to process a single file or an entire folder. Returns 'file' or 'folder'."""
    import tkinter as tk
    _clear(root)
    result = {}

    root.title("vdo2srt")
    root.resizable(False, False)
    root.geometry("")

    tk.Label(root, text="What do you want to process?", font=("Segoe UI", 10), padx=20, pady=12).pack()

    def choose(t):
        result["type"] = t
        root.quit()

    btn_frame = tk.Frame(root, padx=20, pady=4)
    btn_frame.pack()
    tk.Button(btn_frame, text="Single video / audio file", width=28,
              command=lambda: choose("file")).pack(pady=4)
    tk.Button(btn_frame, text="Entire folder  (batch)", width=28,
              command=lambda: choose("folder")).pack(pady=4)

    tk.Frame(root, pady=6).pack()
    root.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))

    root.deiconify()
    root.lift()
    root.focus_force()
    root.mainloop()
    root.withdraw()

    return result["type"]


def _pick_file(root) -> Path:
    from tkinter import filedialog
    path = filedialog.askopenfilename(
        parent=root,
        title="Select video or audio file",
        filetypes=[
            ("Video/Audio files", "*.mp4 *.mkv *.avi *.mov *.wmv *.m4v *.mp3 *.wav *.m4a *.flac *.ogg"),
            ("All files", "*.*"),
        ],
    )
    if not path:
        print("No file selected. Exiting.")
        sys.exit(0)
    return Path(path)


def _pick_folder(root) -> Path:
    from tkinter import filedialog
    path = filedialog.askdirectory(parent=root, title="Select folder of video/audio files")
    if not path:
        print("No folder selected. Exiting.")
        sys.exit(0)
    return Path(path)


def _pick_method(root) -> tuple[str, str]:
    import tkinter as tk
    _clear(root)
    result = {}

    root.title("vdo2srt — Select method")
    root.resizable(False, False)
    root.geometry("")

    tk.Label(root, text="Transcription method:", font=("Segoe UI", 10), padx=20, pady=12).pack()

    def choose(engine, device):
        result["engine"] = engine
        result["device"] = device
        root.quit()

    btn_frame = tk.Frame(root, padx=20, pady=4)
    btn_frame.pack()
    tk.Button(btn_frame, text="Local — GPU  (fast, offline)", width=28,
              command=lambda: choose("local", "cuda")).pack(pady=4)
    tk.Button(btn_frame, text="Local — CPU  (slow, offline)", width=28,
              command=lambda: choose("local", "cpu")).pack(pady=4)
    tk.Button(btn_frame, text="Google Cloud  (accurate, online)", width=28,
              command=lambda: choose("cloud", "auto")).pack(pady=4)

    tk.Frame(root, pady=6).pack()
    root.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))

    root.deiconify()
    root.lift()
    root.focus_force()
    root.mainloop()
    root.withdraw()

    return result["engine"], result["device"]


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def _find_media_files(folder: Path) -> list[Path]:
    return sorted(
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        prog="vdo2srt",
        description="Convert a video/audio file (or all files in a folder) to SRT subtitle files.\n"
                    "An English .en.srt translation is produced automatically. Use --no-translate to skip.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vdo2srt.bat                                        (GUI: pick file or folder, then method)
  vdo2srt.bat movie.mkv                             (single file, GPU auto-detect)
  vdo2srt.bat movie.mkv --language ru               (Russian film)
  vdo2srt.bat movie.mkv --no-translate              (skip English translation)
  vdo2srt.bat movie.mkv --target-language fr        (translate to French instead)
  vdo2srt.bat "E:\\Movies"                          (batch: all files in folder)
  vdo2srt.bat "E:\\Movies" --language ru            (batch, all Russian)
  vdo2srt.bat "E:\\Movies" --overwrite              (re-process files that already have .srt)
  vdo2srt.bat movie.mkv --engine cloud --credentials "E:\\key.json"
        """,
    )

    parser.add_argument(
        "input", nargs="?",
        help="Video/audio file or folder. Omit to open a picker dialog.",
    )
    parser.add_argument(
        "--engine", choices=["local", "cloud"], default=None,
        help="Transcription engine: 'local' (Whisper) or 'cloud' (Google STT). Omit to choose via dialog.",
    )
    parser.add_argument(
        "--model", choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"], default="large-v3",
        help="Whisper model size (local only). Default: large-v3.",
    )
    parser.add_argument(
        "--device", choices=["auto", "cuda", "cpu"], default="auto",
        help="Processing device for local engine. Default: auto (GPU if available, else CPU).",
    )
    parser.add_argument(
        "--language", metavar="LANG", default=None,
        help="Language code (e.g. ru, en, ja, fr). Local: auto-detected if omitted.",
    )
    parser.add_argument(
        "--credentials", metavar="PATH", default=None,
        help="Path to Google Cloud service account JSON (cloud engine only).",
    )
    parser.add_argument(
        "--max-duration", type=float, metavar="SECS", default=6.0,
        help="Split subtitle entries longer than this many seconds (local only). Default: 6. Pass 0 to disable.",
    )
    parser.add_argument(
        "--output", "-o", metavar="PATH", default=None,
        help="Output SRT path (single-file mode only). Default: same folder as input, .srt extension.",
    )
    parser.add_argument(
        "--no-translate", action="store_true",
        help="Skip the automatic English translation. By default an .en.srt is always produced.",
    )
    parser.add_argument(
        "--target-language", metavar="LANG", default="en",
        help="Language to translate into (default: en). Ignored when --no-translate is set.",
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="(Folder mode) Re-process files that already have a matching .srt file.",
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def _process_file(
    input_path: Path,
    output_path: Path,
    transcriber,
    translate: bool,
    target_lang: str,
) -> bool:
    """Transcribe one file and write SRT(s). Returns True on success."""
    try:
        audio_path = extract_audio(input_path)
    except (EnvironmentError, RuntimeError) as e:
        print(f"  Audio extraction failed: {e}")
        return False

    try:
        segments = transcriber.transcribe(audio_path)
    except Exception as e:
        print(f"  Transcription failed: {e}")
        return False

    if not segments:
        print("  No speech detected. SRT will be empty.")

    count = write_srt(segments, output_path)
    print(f"  {count} subtitle entries written.")

    if translate:
        try:
            translated = translate_segments(segments, target_lang=target_lang)
            translated_path = output_path.parent / f"{output_path.stem}.{target_lang}.srt"
            write_srt(translated, translated_path)
        except Exception as e:
            print(f"  Translation failed: {e}")

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    translate = not args.no_translate

    root = None
    if not args.input or args.engine is None:
        root = _make_root()

    # Resolve input — file picker / folder picker / command-line path
    if args.input:
        input_path = Path(args.input)
    else:
        target_type = _pick_target_type(root)
        input_path = _pick_file(root) if target_type == "file" else _pick_folder(root)

    # Resolve engine/device
    engine = args.engine
    device = args.device
    if engine is None:
        engine, device = _pick_method(root)

    if root is not None:
        root.destroy()

    if not input_path.exists():
        print(f"Error: Not found: {input_path}")
        sys.exit(1)

    max_dur = args.max_duration if args.max_duration > 0 else None

    try:
        transcriber = get_transcriber(
            engine=engine,
            model=args.model,
            language=args.language,
            credentials=args.credentials,
            device=device,
            max_duration=max_dur,
        )
    except (EnvironmentError, ValueError, FileNotFoundError) as e:
        print(f"Failed to initialise transcriber:\n  {e}")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Single-file mode
    # -----------------------------------------------------------------------
    if input_path.is_file():
        output_path = Path(args.output) if args.output else input_path.with_suffix(".srt")

        print(f"\nvdo2srt")
        print(f"  Input    : {input_path}")
        print(f"  Engine   : {engine}" + (f" ({args.model}, device={device})" if engine == "local" else ""))
        print(f"  Language : {args.language or 'auto-detect'}")
        print(f"  Output   : {output_path}")
        print(f"  Translate: {'yes → ' + args.target_language if translate else 'no (--no-translate)'}\n")

        ok = _process_file(input_path, output_path, transcriber, translate, args.target_language)
        sys.exit(0 if ok else 1)

    # -----------------------------------------------------------------------
    # Folder / batch mode
    # -----------------------------------------------------------------------
    if not input_path.is_dir():
        print(f"Error: Not a file or directory: {input_path}")
        sys.exit(1)

    all_files = _find_media_files(input_path)
    if not all_files:
        print(f"No supported media files found in: {input_path}")
        sys.exit(0)

    to_process = [f for f in all_files if args.overwrite or not f.with_suffix(".srt").exists()]
    skipped = len(all_files) - len(to_process)

    print(f"\nvdo2srt batch")
    print(f"  Folder   : {input_path}")
    print(f"  Engine   : {engine}" + (f" ({args.model}, device={device})" if engine == "local" else ""))
    print(f"  Language : {args.language or 'auto-detect'}")
    print(f"  Translate: {'yes → ' + args.target_language if translate else 'no (--no-translate)'}")
    print(f"  Files    : {len(to_process)} to process, {skipped} skipped (SRT exists)\n")

    if not to_process:
        print("All files already have SRT files. Use --overwrite to re-process.")
        sys.exit(0)

    succeeded = 0
    failed = 0

    for idx, file_path in enumerate(to_process, 1):
        output_path = file_path.with_suffix(".srt")
        print(f"[{idx}/{len(to_process)}] {file_path.name}")
        if _process_file(file_path, output_path, transcriber, translate, args.target_language):
            succeeded += 1
        else:
            failed += 1
        print()

    print(f"Batch complete: {succeeded} succeeded, {failed} failed, {skipped} skipped.")


if __name__ == "__main__":
    main()
