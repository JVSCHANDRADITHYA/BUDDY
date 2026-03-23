"""
ascii_play.player


Video decode + render loop with audio sync and keyboard controls.

Controls:
  space       pause / resume
  right arrow seek forward 5 seconds
  left arrow  seek backward 5 seconds
  q           quit
"""

import os
import sys
import time
import shutil
import signal
import threading
import tempfile
import subprocess

import numpy as np
import imageio_ffmpeg

from .ansi      import alt_screen, normal_screen, cursor_hide, cursor_show, \
                       clear_screen, reset, move_to
from .renderers import MODES, render_half


# ── keyboard input ────────────────────────────────────────────────────────────

def _make_kb():
    """
    Returns a non-blocking keyboard reader.
    On Windows uses msvcrt, on Linux uses termios raw mode.
    Returns (read_fn, cleanup_fn).
    read_fn() → None | "pause" | "seek_fwd" | "seek_back" | "quit"
    """
    if sys.platform == "win32":
        import msvcrt

        KEY_MAP = {
            b" ":     "pause",
            b"q":     "quit",
            b"Q":     "quit",
        }
        EXTENDED = {
            b"M":     "seek_fwd",   # right arrow
            b"K":     "seek_back",  # left arrow
        }

        def read_key():
            if not msvcrt.kbhit():
                return None
            ch = msvcrt.getch()
            if ch in (b"\x00", b"\xe0"):
                ch2 = msvcrt.getch()
                return EXTENDED.get(ch2)
            return KEY_MAP.get(ch)

        return read_key, lambda: None

    else:
        import tty, termios, select

        fd   = sys.stdin.fileno()
        old  = termios.tcgetattr(fd)
        tty.setraw(fd)

        KEY_MAP = {
            " ":      "pause",
            "q":      "quit",
            "Q":      "quit",
        }
        ESC_MAP = {
            "\x1b[C": "seek_fwd",
            "\x1b[D": "seek_back",
        }

        def read_key():
            r, _, _ = select.select([sys.stdin], [], [], 0)
            if not r:
                return None
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                r2, _, _ = select.select([sys.stdin], [], [], 0.05)
                if r2:
                    ch += sys.stdin.read(2)
                return ESC_MAP.get(ch)
            return KEY_MAP.get(ch)

        def cleanup():
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

        return read_key, cleanup


# ── audio ─────────────────────────────────────────────────────────────────────

def _has_audio_deps():
    try:
        import sounddevice, soundfile
        return True
    except (ImportError, OSError):
        return False


def _extract_audio(filename, tmp_path):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    result = subprocess.run(
        [ffmpeg, "-y", "-i", filename, "-vn", "-acodec", "pcm_s16le",
         "-ar", "44100", "-ac", "2", tmp_path],
        capture_output=True
    )
    return result.returncode == 0


class AudioClock:
    def __init__(self, wav_path):
        import soundfile as sf
        import sounddevice as sd

        self._data, self._sr = sf.read(wav_path, dtype="float32")
        self._pos     = 0
        self._lock    = threading.Lock()
        self._stream  = None
        self._started = threading.Event()
        self._done    = threading.Event()
        self._sd      = sd
        self._paused  = False

    def _callback(self, outdata, frames, time_info, status):
        with self._lock:
            if self._paused:
                outdata[:] = 0
                return
            chunk = self._data[self._pos : self._pos + frames]
            if len(chunk) < frames:
                outdata[:len(chunk)] = chunk
                outdata[len(chunk):] = 0
                self._pos += len(chunk)
                self._done.set()
                raise self._sd.CallbackStop()
            else:
                outdata[:] = chunk
                self._pos += frames
        self._started.set()

    def start(self):
        self._stream = self._sd.OutputStream(
            samplerate=self._sr,
            channels=self._data.shape[1] if self._data.ndim > 1 else 1,
            callback=self._callback,
            dtype="float32",
        )
        self._stream.start()
        self._started.wait(timeout=2.0)

    @property
    def time(self):
        with self._lock:
            return self._pos / self._sr

    def seek(self, seconds):
        with self._lock:
            new_pos = int((self._pos / self._sr + seconds) * self._sr)
            self._pos = max(0, min(new_pos, len(self._data) - 1))

    def pause(self):
        with self._lock:
            self._paused = True

    def resume(self):
        with self._lock:
            self._paused = False

    def is_done(self):
        return self._done.is_set()

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()


# ── player ────────────────────────────────────────────────────────────────────

def play(
    filename : str,
    mode     : str   = "half",
    scale    : float = 1.0,
    loop     : bool  = False,
    info     : bool  = True,
    quality  : int   = 2,
    audio    : bool  = True,
) -> None:
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

    read_key, kb_cleanup = _make_kb()

    try:
        _loop(filename, renderer, mode, scale, loop, info, quality,
              audio, interrupted, read_key)
    finally:
        kb_cleanup()
        sys.stdout.write(reset())
        sys.stdout.write(normal_screen())
        sys.stdout.write(cursor_show())
        sys.stdout.flush()


def _loop(filename, renderer, mode, scale, loop, info, quality,
          audio, interrupted, read_key):

    use_audio = audio and _has_audio_deps()
    SEEK_SECS = 5

    while True:
        # ── extract + start audio ──────────────────────────────────────────
        clock   = None
        tmp_wav = None

        if use_audio:
            tmp_wav = tempfile.mktemp(suffix=".wav")
            if _extract_audio(filename, tmp_wav):
                try:
                    clock = AudioClock(tmp_wav)
                    clock.start()
                except Exception:
                    clock = None
            if clock is None and os.path.exists(tmp_wav):
                os.unlink(tmp_wav)

        # ── video decode ───────────────────────────────────────────────────
        video = imageio_ffmpeg.read_frames(filename)
        meta  = next(video)
        fps   = min(max(float(meta.get("fps", 24) or 24), 1), 120)
        vw, vh = meta["size"]
        frame_size = (vh, vw, 3)
        spf   = 1.0 / fps

        frame_count = 0
        t_start     = time.perf_counter()
        paused      = False
        pause_start = 0.0
        total_paused = 0.0

        try:
            for raw in video:
                if interrupted.is_set():
                    return

                # ── keyboard ───────────────────────────────────────────────
                key = read_key()
                if key == "quit":
                    interrupted.set()
                    return
                elif key == "pause":
                    paused = not paused
                    if paused:
                        pause_start = time.perf_counter()
                        if clock: clock.pause()
                    else:
                        total_paused += time.perf_counter() - pause_start
                        if clock: clock.resume()
                elif key == "seek_fwd":
                    frame_count = min(
                        frame_count + int(SEEK_SECS * fps),
                        int(meta.get("duration", 0) * fps) - 1
                    )
                    t_start -= SEEK_SECS
                    if clock: clock.seek(SEEK_SECS)
                elif key == "seek_back":
                    frame_count = max(frame_count - int(SEEK_SECS * fps), 0)
                    t_start += SEEK_SECS
                    if clock: clock.seek(-SEEK_SECS)

                # ── pause loop ─────────────────────────────────────────────
                while paused and not interrupted.is_set():
                    key2 = read_key()
                    if key2 == "pause":
                        paused = False
                        total_paused += time.perf_counter() - pause_start
                        if clock: clock.resume()
                    elif key2 == "quit":
                        interrupted.set()
                        return
                    time.sleep(0.05)

                frame = np.frombuffer(raw, dtype=np.uint8).reshape(frame_size)

                # ── timing ─────────────────────────────────────────────────
                if clock is not None:
                    audio_time     = clock.time
                    expected_frame = int(audio_time * fps)
                    if expected_frame > frame_count + 2:
                        frame_count = expected_frame
                        continue
                    target = t_start + (audio_time + spf)
                    slack  = target - time.perf_counter()
                    if slack > 0:
                        time.sleep(slack)
                else:
                    effective_start = t_start + total_paused
                    target = effective_start + frame_count * spf
                    slack  = target - time.perf_counter()
                    if slack > 0:
                        time.sleep(slack)

                # ── render ─────────────────────────────────────────────────
                term_cols, term_rows = shutil.get_terminal_size((80, 24))
                cols        = max(1, int(term_cols * scale))
                rows        = max(1, int(term_rows * scale))
                render_rows = max(1, rows - 1) if info else rows

                out = renderer(frame, cols, render_rows, quality)

                if info:
                    elapsed    = time.perf_counter() - t_start - total_paused
                    actual_fps = frame_count / elapsed if elapsed > 0 else 0
                    audio_tag  = "audio" if clock else "no audio"
                    pause_tag  = "  PAUSED" if paused else ""
                    out += (
                        move_to(rows)
                        + "\033[48;2;18;18;18m\033[38;2;170;170;170m"
                        + f"  {os.path.basename(filename)}"
                        + f"  │  {mode}"
                        + f"  │  q{quality}"
                        + f"  │  {cols}×{render_rows}"
                        + f"  │  {actual_fps:.1f}/{fps:.0f} fps"
                        + f"  │  {audio_tag}"
                        + f"  │  [space] pause  [←→] seek 5s  [q] quit"
                        + pause_tag
                        + "\033[K"
                        + reset()
                    )

                sys.stdout.write(out)
                sys.stdout.flush()
                frame_count += 1

        finally:
            if clock:
                clock.stop()
            if tmp_wav and os.path.exists(tmp_wav):
                os.unlink(tmp_wav)

        if not loop:
            break