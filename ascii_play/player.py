"""
ascii_play.player
~~~~~~~~~~~~~~~~~
Video decode + render loop.
"""

import os
import sys
import time
import shutil
import signal
import threading

import numpy as np
import imageio_ffmpeg

from .ansi      import alt_screen, normal_screen, cursor_hide, cursor_show, \
                       clear_screen, reset, move_to
from .renderers import MODES, render_half


def play(
    filename : str,
    mode     : str   = "half",
    scale    : float = 1.0,
    loop     : bool  = False,
    info     : bool  = True,
    quality  : int   = 2,
) -> None:
    """
    Play *filename* in the terminal.

    Parameters
    ----------
    filename : path to any video file FFmpeg can decode
    mode     : "half" | "ascii" | "braille"
    scale    : fraction of terminal to use (0.1 – 1.0)
    loop     : restart when video ends
    info     : show status bar at bottom
    quality  : 1 = fast, 2 = smooth (default), 3 = best
    """
    renderer = MODES.get(mode, render_half)

    interrupted = threading.Event()
    def _on_signal(sig, _frame):
        interrupted.set()
    signal.signal(signal.SIGINT,  _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    sys.stdout.write(alt_screen())
    sys.stdout.write(cursor_hide())
    sys.stdout.write(clear_screen())
    sys.stdout.flush()

    try:
        _loop(filename, renderer, mode, scale, loop, info, quality, interrupted)
    finally:
        sys.stdout.write(reset())
        sys.stdout.write(normal_screen())
        sys.stdout.write(cursor_show())
        sys.stdout.flush()


def _loop(filename, renderer, mode, scale, loop, info, quality, interrupted):
    while True:
        video = imageio_ffmpeg.read_frames(filename)
        meta  = next(video)
        fps   = meta.get("fps", 24) or 24
        vw, vh = meta["size"]
        frame_size = (vh, vw, 3)
        spf   = 1.0 / fps

        frame_count = 0
        t_start     = time.perf_counter()

        for raw in video:
            if interrupted.is_set():
                return

            frame = np.frombuffer(raw, dtype=np.uint8).reshape(frame_size)

            term_cols, term_rows = shutil.get_terminal_size((80, 24))
            cols = max(1, int(term_cols * scale))
            rows = max(1, int(term_rows * scale))
            render_rows = max(1, rows - 1) if info else rows

            out = renderer(frame, cols, render_rows, quality)

            if info:
                elapsed    = time.perf_counter() - t_start
                actual_fps = frame_count / elapsed if elapsed > 0 else 0
                out += (
                    move_to(rows)
                    + "\033[48;2;18;18;18m\033[38;2;170;170;170m"
                    + f"  {os.path.basename(filename)}"
                    + f"  │  {mode}"
                    + f"  │  q{quality}"
                    + f"  │  {cols}×{render_rows}"
                    + f"  │  {actual_fps:.1f}/{fps:.0f} fps"
                    + f"  │  frame {frame_count}"
                    + "\033[K"
                    + reset()
                )

            sys.stdout.write(out)
            sys.stdout.flush()

            frame_count += 1

            target = t_start + frame_count * spf
            slack  = target - time.perf_counter()
            if slack > 0:
                time.sleep(slack)

        if not loop:
            break
