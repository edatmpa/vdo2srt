r"""
process_list.py — Generate SRT subtitles for every folder in a text list file.

The list file should contain one folder path per line, optionally with a
leading number and period (e.g. from a "No Subs.txt" export):

    1. V:\Korean\Movie Title (2022) 1080p
    2. V:\Korean\Another Movie (2023)

Double-click process_list.bat to launch; the script will prompt for the
list file and transcription method via dialog.  All options can also be
passed on the command line — run with --help for details.
"""

import os

# Must be set before any module import that loads OpenMP / CUDA DLLs.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import glob as _glob
_cuda_root = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA"
for _cuda_bin in sorted(_glob.glob(rf"{_cuda_root}\v*\bin"), reverse=True):
    if os.path.isdir(_cuda_bin):
        os.add_dll_directory(_cuda_bin)
        os.environ["PATH"] = _cuda_bin + os.pathsep + os.environ.get("PATH", "")
        break

import re
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import argparse
from src.cli import process_file
from src.gui import make_root, pick_method
from src.transcriber import get_transcriber
from src.translator import translate_existing_srt
from src.utils import clean_path, find_media_files, find_original_srt_files, is_skippable_folder


def _pick_list_file() -> Path:
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Select folder list file",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    )
    root.destroy()
    if not path:
        print("No file selected. Exiting.")
        sys.exit(0)
    return Path(path)


def _parse_list_file(list_path: Path) -> list[Path]:
    """
    Return folder paths from a numbered or plain text list file.
    Skips hidden/system sub-folders (e.g. .actors) and known non-movie names.
    """
    paths = []
    text = list_path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip optional leading "42. " numbering
        m = re.match(r"^\d+\.\s+(.+)$", line)
        path_str = (m.group(1) if m else line).strip()
        p = _remap_missing(clean_path(path_str), list_path)
        if is_skippable_folder(p):
            continue
        paths.append(p)
    return paths


def _remap_missing(p: Path, list_path: Path) -> Path:
    """
    If a listed folder doesn't exist as written (e.g. the list was exported
    while the library was mounted under a different drive letter), try it on
    the list file's own drive, then next to the list file itself.
    """
    if p.is_dir():
        return p
    list_dir = list_path.absolute().parent
    candidates = []
    if p.drive:
        candidates.append(Path(list_dir.drive + str(p)[len(p.drive):]))
    candidates.append(list_dir / p.name)
    for c in candidates:
        if c.is_dir():
            return c
    return p


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="process_list",
        description="Generate SRT subtitles for every folder listed in a text file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  process_list.bat                                    (GUI: pick list file, then method)
  process_list.bat no_subs.txt                        (prompts for method only)
  process_list.bat no_subs.txt --engine local --device cuda --language ko
  process_list.bat no_subs.txt --no-translate         (original language only)
  process_list.bat no_subs.txt --overwrite            (re-process files that have .srt)
        """,
    )
    p.add_argument("list_file", nargs="?",
                   help="Path to folder list .txt file. Omit to open a picker dialog.")
    p.add_argument("--engine", choices=["local", "cloud"], default=None)
    p.add_argument("--model",
                   choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
                   default="large-v3")
    p.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    p.add_argument("--language", metavar="LANG", default=None,
                   help="Language code (e.g. ko, ru, ja). Auto-detected if omitted.")
    p.add_argument("--credentials", metavar="PATH", default=None,
                   help="Google Cloud service account JSON (cloud engine only).")
    p.add_argument("--max-duration", type=float, metavar="SECS", default=6.0,
                   help="Max subtitle entry duration in seconds (default: 6, 0=disable).")
    p.add_argument("--no-translate", action="store_true",
                   help="Skip English translation.")
    p.add_argument("--target-language", metavar="LANG", default="en",
                   help="Translation target language (default: en).")
    p.add_argument("--overwrite", action="store_true",
                   help="Re-transcribe files that already have a matching .srt, AND "
                        "retranslate/replace existing translations (backed up to .bak first).")
    return p


def main() -> None:
    args = _build_parser().parse_args()
    translate = not args.no_translate

    # List file — GUI picker if not provided on CLI
    list_path = clean_path(args.list_file) if args.list_file else _pick_list_file()
    if not list_path.exists():
        print(f"Error: List file not found: {list_path}")
        sys.exit(1)

    # Engine/device — GUI picker if not provided on CLI
    engine, device = args.engine, args.device
    if engine is None:
        root = make_root()
        engine, device = pick_method(root)
        root.destroy()

    max_dur = args.max_duration if args.max_duration > 0 else None

    # Parse and filter the folder list
    all_folders = _parse_list_file(list_path)
    if not all_folders:
        print("No folder paths found in list file.")
        sys.exit(0)

    # Per folder, split work into transcription (no original .srt yet — voice-
    # to-text runs) vs. translation-only (original .srt already exists, either
    # next to its video or orphaned with the video moved/deleted — voice-to-
    # text is never re-run for these).
    folder_plans: list[dict] = []
    skipped_no_media = 0
    skipped_nothing_pending = 0

    for folder in all_folders:
        if not folder.is_dir():
            skipped_no_media += 1
            continue

        media = find_media_files(folder)
        originals = find_original_srt_files(folder) if translate else []

        if not media and not originals:
            skipped_no_media += 1
            continue

        transcribe_list = [f for f in media if args.overwrite or not f.with_suffix(".srt").exists()]

        translate_list: list[Path] = []
        if translate:
            translate_list = [
                f.with_suffix(".srt") for f in media
                if not args.overwrite and f.with_suffix(".srt").exists()
            ]
            media_stems = {f.stem.lower() for f in media}
            translate_list.extend(s for s in originals if s.stem.lower() not in media_stems)

        if not transcribe_list and not translate_list:
            skipped_nothing_pending += 1
            continue

        folder_plans.append({"folder": folder, "transcribe": transcribe_list, "translate": translate_list})

    total_transcribe = sum(len(p["transcribe"]) for p in folder_plans)
    total_translate = sum(len(p["translate"]) for p in folder_plans)

    print(f"\nprocess_list")
    print(f"  List     : {list_path.name}  ({len(all_folders)} entries parsed)")
    print(f"  Engine   : {engine}" + (f" ({args.model}, device={device})" if engine == "local" else ""))
    print(f"  Language : {args.language or 'auto-detect'}")
    print(f"  Translate: {'yes → ' + args.target_language if translate else 'no (--no-translate)'}")
    print(f"  Folders  : {len(folder_plans)} with work "
          f"({total_transcribe} to transcribe, {total_translate} to translate), "
          f"{skipped_nothing_pending} already done, {skipped_no_media} not found / no media")
    print()

    if not folder_plans:
        print("Nothing to process. Use --overwrite to re-process existing SRTs/translations.")
        sys.exit(0)

    # Load the transcriber once — reused across every folder/file. Skipped
    # entirely if every pending item is translation-only.
    transcriber = None
    if total_transcribe:
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

    succeeded = failed = 0

    for folder_idx, plan in enumerate(folder_plans, 1):
        folder = plan["folder"]
        n_items = len(plan["transcribe"]) + len(plan["translate"])
        label = f"[{folder_idx}/{len(folder_plans)}] {folder.name}"
        if n_items > 1:
            label += f"  ({n_items} item(s))"
        print(label)

        for file_path in plan["transcribe"]:
            if n_items > 1:
                print(f"  → {file_path.name} (transcribing)")
            output_path = file_path.with_suffix(".srt")
            if process_file(file_path, output_path, transcriber, translate, args.target_language):
                succeeded += 1
            else:
                failed += 1

        for srt_path in plan["translate"]:
            if n_items > 1:
                print(f"  → {srt_path.name} (translating)")
            if translate_existing_srt(srt_path, args.target_language, overwrite=args.overwrite):
                succeeded += 1
            else:
                failed += 1

        print()

    print(f"Done: {succeeded} succeeded, {failed} failed  "
          f"({len(folder_plans)} folders processed).")


if __name__ == "__main__":
    main()
