#!/usr/bin/env python3
"""
cli.py — buddy
~~~~~~~~~~~~~~
Entry point. Run directly:

    python cli.py video.mp4
    python cli.py play video.mp4 -m braille -q 3
    python cli.py modes
    python cli.py help

Or via wrapper scripts:
    buddy video.mp4
"""

import sys
import os
import argparse

# make package importable when running cli.py directly from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ascii_play.renderers import MODES
from ascii_play.player    import play


def _add_play_args(p):
    p.add_argument("filename", help="Video file (any format FFmpeg supports)")
    p.add_argument("-m", "--mode",    choices=list(MODES.keys()), default="half",
                   metavar="MODE",   help="half (default) | ascii | braille")
    p.add_argument("-q", "--quality", type=int, choices=[1,2,3], default=2,
                   metavar="N",      help="1=fast  2=smooth(default)  3=best")
    p.add_argument("-s", "--scale",   type=float, default=1.0,
                   metavar="F",      help="Terminal fill fraction 0.1-1.0 (default: 1.0)")
    p.add_argument("--loop",          action="store_true", help="Loop indefinitely")
    p.add_argument("--no-info",       action="store_true", help="Hide status bar")
    p.add_argument("--no-audio",      action="store_true", help="Disable audio playback")

def _run_play(args):
    if not os.path.isfile(args.filename):
        print(f"buddy: error: file not found: {args.filename}", file=sys.stderr)
        sys.exit(1)
    play(filename=args.filename, mode=args.mode, scale=args.scale,
         loop=args.loop, info=not args.no_info, quality=args.quality,
         audio=not args.no_audio)

HELP = r"""
  _               _     _
 | |__  _   _  __| | __| |_   _
 | '_ \| | | |/ _` |/ _` | | | |
 | |_) | |_| | (_| | (_| | |_| |
 |_.__/ \__,_|\__,_|\__,_|\__, |
                           |___/
 live terminal video player  v0.1.2

USAGE
  buddy <video>                     Play a video (smart default)
  buddy play <video> [options]      Play with explicit options
  buddy modes                       List render modes
  buddy help                        Show this screen

OPTIONS
  -m, --mode   MODE   Render mode (default: half)
  -q, --quality  N    Quality level (default: 2)
  -s, --scale    F    Terminal fill fraction (default: 1.0)
  --loop              Loop video indefinitely
  --no-info           Hide the status bar at the bottom

RENDER MODES
  half      (default) Half-block ▀ chars, true fg+bg 24-bit color
            2× vertical resolution — best overall quality
  ascii     Density chars @%#*+=-:. with true color per character
            Classic ASCII art look
  braille   Braille dots ⣿, 2 wide × 4 tall pixels per cell
            Highest spatial resolution, great for detail

QUALITY
  1   Nearest-neighbor  — fastest, some shimmer on fine detail
  2   4-tap smooth      — default, smooth with near-zero extra cost
  3   Full box filter   — best quality, every source pixel averaged

EXAMPLES
  buddy video.mp4
  buddy video.mp4 -m braille
  buddy video.mp4 -m half -q 3 --loop
  buddy video.mp4 -s 0.8 --no-info
  buddy play video.mp4 -m ascii -q 2 -s 0.9

NEW : AUDIO SUPPORT ADDED! (version 0.1.2)
  Audio is now supported in all render modes. Use --no-audio to disable.

TERMINAL REQUIREMENTS
  Needs 24-bit true color support.
  ✓ Windows Terminal, iTerm2, Kitty, WezTerm, Alacritty, GNOME Terminal
  ✗ macOS Terminal.app (use iTerm2 instead)

  Check: echo $COLORTERM  →  should print "truecolor"
"""

def _print_help():
    print(HELP)

def _print_modes():
    print()
    print("Render modes:\n")
    rows = [
        ("half",    "(default) Half-block ▀, true fg+bg color, 2× vertical res"),
        ("ascii",   "Density chars @%#*+=-:. + true color per char"),
        ("braille", "Braille dots ⣿, 2×4 px per cell, highest resolution"),
    ]
    for name, desc in rows:
        print(f"  {name:<12}{desc}")
    print()

def build_parser():
    # add_help=False so -h/--help doesn't print the ugly default
    parser = argparse.ArgumentParser(prog="buddy", add_help=False)
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    play_p = sub.add_parser("play", add_help=False)
    _add_play_args(play_p)

    sub.add_parser("modes", add_help=False)
    sub.add_parser("help",  add_help=False)
    return parser

def main():
    # bare `buddy` → show help
    if len(sys.argv) == 1:
        _print_help()
        sys.exit(0)

    # -h / --help anywhere → show help
    if "-h" in sys.argv or "--help" in sys.argv:
        _print_help()
        sys.exit(0)

    # smart dispatch: `buddy video.mp4 [opts]` → inject `play`
    known = {"play", "modes", "help"}
    if sys.argv[1] not in known and not sys.argv[1].startswith("-"):
        sys.argv.insert(1, "play")

    parser = build_parser()
    args   = parser.parse_args()

    if   args.command == "help":  _print_help()
    elif args.command == "modes": _print_modes()
    elif args.command == "play":  _run_play(args)
    else:                         _print_help()

if __name__ == "__main__":
    main()