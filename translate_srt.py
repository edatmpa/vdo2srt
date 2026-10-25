r"""
translate_srt.py — Translate existing .srt subtitle files. No video, no
transcription — pure text-to-text, for subtitles that are already generated.

Point it at:
  - a single .srt file            -> translate that one file
  - a folder                      -> translate every "original" .srt in it
  - a folder, with --recursive    -> treat it as a library root and scan
                                      each immediate subfolder (movie/show
                                      folders) the same way, one level down
                                      (root -> movie folders -> files; not an
                                      arbitrary-depth walk)

"Original" means a .srt that doesn't already look like a translation output
(e.g. "movie.en.srt" is skipped as a source; "movie.srt" and
"movie.S01E01.AVC.srt" are picked up — see src/utils.py's
find_original_srt_files for the exact rule).

By default, a file whose "<stem>.<target_lang>.srt" already exists is
skipped. --overwrite retranslates and replaces it, backing up the previous
translation to "<name>.srt.bak" first.

Which translation engine is used is automatic — see translate_routing.txt
and src/translator.py.
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import argparse

from src.translator import translate_existing_srt
from src.utils import clean_path, find_movie_subfolders, find_original_srt_files


def _pick_input() -> Path:
    """GUI fallback when run with no arguments — pick a .srt file or a folder."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()

    choice = {}

    def choose(t):
        choice["type"] = t
        root.quit()

    root.title("translate_srt")
    tk.Label(root, text="What do you want to translate?", padx=20, pady=12).pack()
    frame = tk.Frame(root, padx=20, pady=4)
    frame.pack()
    tk.Button(frame, text="Single .srt file", width=28, command=lambda: choose("file")).pack(pady=4)
    tk.Button(frame, text="Folder of .srt files", width=28, command=lambda: choose("folder")).pack(pady=4)
    root.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))
    root.deiconify()
    root.mainloop()
    root.withdraw()

    if choice.get("type") == "file":
        path = filedialog.askopenfilename(
            parent=root, title="Select .srt file",
            filetypes=[("Subtitle files", "*.srt"), ("All files", "*.*")],
        )
    else:
        path = filedialog.askdirectory(parent=root, title="Select folder of .srt files")

    root.destroy()
    if not path:
        print("Nothing selected. Exiting.")
        sys.exit(0)
    return Path(path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="translate_srt",
        description="Translate existing .srt subtitle files (no video/transcription involved).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=r"""
Examples:
  translate_srt.bat                                             (GUI: pick file or folder)
  translate_srt.bat movie.srt                                    (single file)
  translate_srt.bat "V:\Korean\Movie Title (2022)"               (one folder)
  translate_srt.bat "V:\War Series (Russia)" --recursive         (root -> movie folders)
  translate_srt.bat "V:\War Series (Russia)" --recursive --overwrite
        """,
    )
    parser.add_argument(
        "input", nargs="?",
        help="A .srt file, a folder, or (with --recursive) a library root. Omit to open a picker.",
    )
    parser.add_argument(
        "--recursive", action="store_true",
        help="Treat 'input' as a library root and scan each immediate subfolder "
             "(movie/show folders) instead of scanning 'input' itself.",
    )
    parser.add_argument(
        "--target-language", metavar="LANG", default="en",
        help="Language to translate into (default: en).",
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Retranslate and replace existing <stem>.<target_lang>.srt files "
             "(the previous translation is backed up to .bak first).",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    input_path = clean_path(args.input) if args.input else _pick_input()
    if not input_path.exists():
        print(f"Error: Not found: {input_path}")
        sys.exit(1)

    if input_path.is_file():
        if input_path.suffix.lower() != ".srt":
            print(f"Error: Not a .srt file: {input_path}")
            sys.exit(1)
        srt_files = [input_path]
    elif args.recursive:
        srt_files = []
        for folder in find_movie_subfolders(input_path):
            srt_files.extend(find_original_srt_files(folder))
    else:
        srt_files = find_original_srt_files(input_path)

    if not srt_files:
        print(f"No original .srt files found in: {input_path}")
        sys.exit(0)

    target_suffix = f".{args.target_language}.srt"
    pending = [
        s for s in srt_files
        if args.overwrite or not (s.parent / f"{s.stem}{target_suffix}").exists()
    ]

    print(f"\ntranslate_srt")
    print(f"  Input  : {input_path}" + ("  (recursive)" if args.recursive else ""))
    print(f"  Target : {args.target_language}")
    print(f"  Files  : {len(pending)} to translate ({len(srt_files)} original SRT(s) found)\n")

    if not pending:
        print("Nothing to translate. Use --overwrite to retranslate existing translations.")
        sys.exit(0)

    succeeded = failed = 0
    for idx, srt_path in enumerate(pending, 1):
        print(f"[{idx}/{len(pending)}] {srt_path.name}")
        if translate_existing_srt(srt_path, args.target_language, overwrite=args.overwrite):
            succeeded += 1
        else:
            failed += 1
        print()

    print(f"Done: {succeeded} succeeded, {failed} failed.")


if __name__ == "__main__":
    main()
