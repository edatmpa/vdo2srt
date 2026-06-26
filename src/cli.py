"""
Command-line interface and main orchestration for vdo2srt.

Handles argument parsing, GUI fallback dialogs, and the processing pipeline
for both single-file and batch/folder modes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.extractor import extract_audio
from src.transcriber import get_transcriber
from src.srt_writer import write_srt
from src.srt_reader import read_srt
from src.translator import translate_segments
from src.utils import find_media_files
from src.gui import make_root, pick_target_type, pick_file, pick_folder, pick_method


# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
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

    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    return build_parser().parse_args(argv)


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_file(
    input_path: Path,
    output_path: Path,
    transcriber,
    translate: bool,
    target_lang: str,
) -> bool:
    """Transcribe one file and write SRT(s). Returns True on success."""
    try:
        audio_path = extract_audio(input_path)
    except (OSError, RuntimeError) as e:
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
            translated_path = output_path.parent / f"{output_path.stem}.{target_lang}.srt"
            translated = translate_segments(segments, target_lang=target_lang)
            write_srt(translated, translated_path)
        except Exception as e:
            print(f"  Translation failed: {e}")

    return True


def translate_existing_srt(
    srt_path: Path,
    target_lang: str,
) -> bool:
    """Load existing SRT and translate it. Returns True on success."""
    # Check if translated file already exists
    translated_path = srt_path.parent / f"{srt_path.stem}.{target_lang}.srt"
    if translated_path.exists():
        print(f"  Translation already exists: {translated_path.name}. Skipping.")
        return True
    
    try:
        segments = read_srt(srt_path)
    except Exception as e:
        print(f"  Failed to read SRT: {e}")
        return False

    if not segments:
        print("  SRT file is empty, skipping translation.")
        return False

    try:
        translated = translate_segments(segments, target_lang=target_lang)
        count = write_srt(translated, translated_path)
        print(f"  {count} entries translated to {target_lang}.")
    except Exception as e:
        print(f"  Translation failed: {e}")
        return False

    return True


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    """Main entry point for vdo2srt."""
    args = parse_args(argv)
    translate = not args.no_translate

    root = None
    if not args.input or args.engine is None:
        root = make_root()

    # Resolve input — file picker / folder picker / command-line path
    if args.input:
        input_path = Path(args.input)
    else:
        target_type = pick_target_type(root)
        input_path = pick_file(root) if target_type == "file" else pick_folder(root)

    # Resolve engine/device
    engine = args.engine
    device = args.device
    if engine is None:
        engine, device = pick_method(root)

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
    except (OSError, ValueError, FileNotFoundError) as e:
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

        ok = process_file(input_path, output_path, transcriber, translate, args.target_language)
        sys.exit(0 if ok else 1)

    # -----------------------------------------------------------------------
    # Folder / batch mode
    # -----------------------------------------------------------------------
    if not input_path.is_dir():
        print(f"Error: Not a file or directory: {input_path}")
        sys.exit(1)

    all_files = find_media_files(input_path)
    if not all_files:
        print(f"No supported media files found in: {input_path}")
        sys.exit(0)

    # Separate files into two groups: need transcription vs. need translation-only
    to_transcribe = [f for f in all_files if args.overwrite or not f.with_suffix(".srt").exists()]
    to_translate_only = [f for f in all_files if not args.overwrite and f.with_suffix(".srt").exists()]

    print(f"\nvdo2srt batch")
    print(f"  Folder   : {input_path}")
    print(f"  Engine   : {engine}" + (f" ({args.model}, device={device})" if engine == "local" else ""))
    print(f"  Language : {args.language or 'auto-detect'}")
    print(f"  Translate: {'yes → ' + args.target_language if translate else 'no (--no-translate)'}")
    print(f"  Files    : {len(to_transcribe)} to process, {len(to_translate_only)} to translate (SRT exists)\n")

    if not to_transcribe and not to_translate_only:
        print("No files to process or translate.")
        sys.exit(0)

    if not to_transcribe and not translate:
        print("All files already have SRT files. Use --overwrite to re-process.")
        sys.exit(0)

    succeeded = 0
    failed = 0

    # Process transcription
    for idx, file_path in enumerate(to_transcribe, 1):
        output_path = file_path.with_suffix(".srt")
        print(f"[{idx}/{len(to_transcribe)}] {file_path.name} (transcribing)")
        if process_file(file_path, output_path, transcriber, translate, args.target_language):
            succeeded += 1
        else:
            failed += 1
        print()

    # Process translation-only for existing SRT files
    if translate and to_translate_only:
        for idx, file_path in enumerate(to_translate_only, 1):
            srt_path = file_path.with_suffix(".srt")
            print(f"[{len(to_transcribe) + idx}/{len(to_transcribe) + len(to_translate_only)}] {file_path.name} (translating)")
            if translate_existing_srt(srt_path, args.target_language):
                succeeded += 1
            else:
                failed += 1
            print()

    print(f"Batch complete: {succeeded} succeeded, {failed} failed.")


if __name__ == "__main__":
    main()