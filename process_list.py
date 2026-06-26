"""
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
from src.utils import find_media_files


# Folder names that are never movie folders — skip without checking disk.
_SKIP_NAMES = {"thumbs", "folder", "extras", "featurettes", "behind the scenes",
               "deleted scenes", "interviews", "scenes", "shorts", "trailers"}


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
        p = Path(path_str)
        # Skip hidden/system folders (.actors, .thumbnails, etc.)
        if p.name.startswith("."):
            continue
        # Skip known non-movie folder names
        if p.name.lower() in _SKIP_NAMES:
            continue
        paths.append(p)
    return paths


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
                   help="Re-process files that already have a matching .srt.")
    return p


def main() -> None:
    args = _build_parser().parse_args()
    translate = not args.no_translate

    # List file — GUI picker if not provided on CLI
    list_path = Path(args.list_file) if args.list_file else _pick_list_file()
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

    to_process: list[tuple[Path, list[Path]]] = []
    skipped_no_media = 0
    skipped_has_srt = 0

    for folder in all_folders:
        if not folder.is_dir():
            skipped_no_media += 1
            continue
        media = find_media_files(folder)
        if not media:
            skipped_no_media += 1
            continue
        pending = media if args.overwrite else [f for f in media if not f.with_suffix(".srt").exists()]
        if not pending:
            skipped_has_srt += 1
            continue
        to_process.append((folder, pending))

    total_files = sum(len(files) for _, files in to_process)

    print(f"\nprocess_list")
    print(f"  List     : {list_path.name}  ({len(all_folders)} entries parsed)")
    print(f"  Engine   : {engine}" + (f" ({args.model}, device={device})" if engine == "local" else ""))
    print(f"  Language : {args.language or 'auto-detect'}")
    print(f"  Translate: {'yes → ' + args.target_language if translate else 'no (--no-translate)'}")
    print(f"  Folders  : {len(to_process)} to process ({total_files} file(s)), "
          f"{skipped_has_srt} already done, {skipped_no_media} not found / no media")
    print()

    if not to_process:
        print("Nothing to process. Use --overwrite to re-process existing SRTs.")
        sys.exit(0)

    # Load the transcriber once — reused across every folder/file.
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

    for folder_idx, (folder, pending_files) in enumerate(to_process, 1):
        label = f"[{folder_idx}/{len(to_process)}] {folder.name}"
        if len(pending_files) > 1:
            label += f"  ({len(pending_files)} files)"
        print(label)

        for file_path in pending_files:
            if len(pending_files) > 1:
                print(f"  → {file_path.name}")
            output_path = file_path.with_suffix(".srt")
            if process_file(file_path, output_path, transcriber, translate, args.target_language):
                succeeded += 1
            else:
                failed += 1
        print()

    print(f"Done: {succeeded} succeeded, {failed} failed  "
          f"({len(to_process)} folders, {total_files} files total).")


if __name__ == "__main__":
    main()
