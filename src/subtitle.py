"""
Subtitle overlay — displays bilingual subtitles (jp_text + zh_text) in a
transparent always-on-top tkinter window.
"""

import logging
import threading
import tkinter as tk
from typing import Optional

logger = logging.getLogger(__name__)


class SubtitleOverlay:
    """Always-on-top transparent subtitle window."""

    def __init__(self):
        self._root: Optional[tk.Tk] = None
        self._jp_label: Optional[tk.Label] = None
        self._zh_label: Optional[tk.Label] = None
        self._emotion_label: Optional[tk.Label] = None
        self._ready = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Create and show the subtitle window in a daemon thread."""
        self._thread = threading.Thread(target=self._tk_main, daemon=True)
        self._thread.start()
        # Wait for tkinter to initialize
        for _ in range(50):
            if self._ready:
                break
            time.sleep(0.05)

    def show(self, jp_text: str, zh_text: str, emotion: str = "neutral"):
        """Update subtitle display. Thread-safe."""
        if not self._ready or not self._root:
            return

        color = {"neutral": "#FFFFFF", "happy": "#FFD700", "angry": "#FF6B6B",
                  "sad": "#87CEEB", "surprised": "#FFA500", "teasing": "#FF69B4"}.get(emotion, "#FFFFFF")

        def _update():
            try:
                self._jp_label.config(text=jp_text, fg=color)
                self._zh_label.config(text=zh_text)
                self._emotion_label.config(text=f"[{emotion}]")
                self._root.deiconify()
                self._root.lift()
            except Exception:
                pass

        self._root.after(0, _update)

    def hide(self):
        """Hide the subtitle window."""
        if self._root:
            self._root.after(0, self._root.withdraw)

    def _tk_main(self):
        """Tkinter main loop — runs in daemon thread."""
        self._root = tk.Tk()
        self._root.title("莲华 - Renge")
        self._root.geometry("800x160+560+700")  # Bottom center of 1920x1080
        self._root.overrideredirect(True)        # No title bar
        self._root.attributes("-topmost", True)  # Always on top
        self._root.attributes("-alpha", 0.85)    # Semi-transparent
        self._root.configure(bg="#1a1a2e")

        # Drop shadow effect via dark background frame
        frame = tk.Frame(self._root, bg="#1a1a2e", padx=20, pady=10)
        frame.pack(fill="both", expand=True)

        self._jp_label = tk.Label(
            frame, text="", font=("Yu Gothic", 20, "bold"),
            fg="#FFFFFF", bg="#1a1a2e", anchor="w", justify="left", wraplength=760,
        )
        self._jp_label.pack(fill="x", pady=(5, 2))

        self._zh_label = tk.Label(
            frame, text="", font=("Microsoft YaHei", 16),
            fg="#CCCCCC", bg="#1a1a2e", anchor="w", justify="left", wraplength=760,
        )
        self._zh_label.pack(fill="x", pady=(2, 2))

        self._emotion_label = tk.Label(
            frame, text="", font=("Consolas", 10),
            fg="#888888", bg="#1a1a2e", anchor="e",
        )
        self._emotion_label.pack(fill="x")

        # Allow dragging the window
        frame.bind("<Button-1>", self._start_drag)
        frame.bind("<B1-Motion>", self._on_drag)
        self._jp_label.bind("<Button-1>", self._start_drag)
        self._jp_label.bind("<B1-Motion>", self._on_drag)
        self._zh_label.bind("<Button-1>", self._start_drag)
        self._zh_label.bind("<B1-Motion>", self._on_drag)

        self._ready = True
        self._root.withdraw()  # Start hidden
        self._root.mainloop()

    def _start_drag(self, event):
        self._drag_x = event.x_root - self._root.winfo_x()
        self._drag_y = event.y_root - self._root.winfo_y()

    def _on_drag(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self._root.geometry(f"+{x}+{y}")

    def close(self):
        """Clean shutdown."""
        if self._root:
            self._root.after(0, self._root.destroy)


# Required for _start_drag/_on_drag timing
import time
