"""
Tkinter GUI dialogs for file/folder selection and transcription method picking.

Used when the user runs the tool without providing command-line arguments.
"""

from __future__ import annotations

import sys
from pathlib import Path


def make_root():
    """Create a hidden, always-on-top Tk root window."""
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update()
    return root


def _clear(root) -> None:
    """Destroy all child widgets of *root*."""
    for widget in root.winfo_children():
        widget.destroy()


def pick_target_type(root) -> str:
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


def pick_file(root) -> Path:
    """Show a file-open dialog and return the selected Path. Exits if cancelled."""
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


def pick_folder(root) -> Path:
    """Show a folder picker dialog and return the selected Path. Exits if cancelled."""
    from tkinter import filedialog
    path = filedialog.askdirectory(parent=root, title="Select folder of video/audio files")
    if not path:
        print("No folder selected. Exiting.")
        sys.exit(0)
    return Path(path)


def pick_method(root) -> tuple[str, str]:
    """Show a three-button dialog to choose transcription engine and device.
    Returns (engine, device)."""
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
