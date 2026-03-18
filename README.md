# buddy
``` bash
  _               _     _
 | |__  _   _  __| | __| |_   _
 | '_ \| | | |/ _` |/ _` | | | |
 | |_) | |_| | (_| | (_| | |_| |
 |_.__/ \__,_|\__,_|\__,_|\__, |
                           |___/
 live terminal video player  v0.1.0

```
Buddy (short for Block-based Unicode Direct-color Display Yield) is a live terminal video player that renders in true 24-bit color.

`mpv -vo caca` uses a 256-color palette and nearest-neighbor sampling. buddy uses full RGB ANSI escape sequences with area-averaged downscaling — the difference is visible.

```
buddy video.mp4
```

---

## How it works

Every terminal cell gets its own `\033[38;2;R;G;Bm` foreground and `\033[48;2;R;G;Bm` background escape. By pairing this with the Unicode half-block character `▀`, each cell encodes two pixel rows — one in the foreground color, one in the background. That gives 2x effective vertical resolution out of the character grid with no tricks.

The frame downscaling uses area averaging by default: every source pixel within a cell's coverage area contributes to the final color. This eliminates the shimmer and aliasing that nearest-neighbor produces on motion.

All rendering is vectorized with NumPy — no Python loops over individual pixels. The FFmpeg decode runs through `imageio-ffmpeg` which shells out to a native binary, so the decode path never touches Python either.

---

## Requirements

- Python 3.9 or later
- A terminal with 24-bit true color support

**Supported terminals:**

| Terminal | Platform | Status |
|----------|----------|--------|
| Windows Terminal | Windows | Works |
| iTerm2 | macOS | Works |
| Kitty | Linux / macOS | Works |
| WezTerm | All | Works |
| Alacritty | All | Works |
| GNOME Terminal 3.36+ | Linux | Works |
| Terminal.app | macOS | Does not work (256 colors only) |
| PuTTY (old versions) | Windows | Does not work |

To verify your terminal supports true color:

```bash
# Linux / macOS
echo $COLORTERM
```
should print: `truecolor`
  - Windows Terminal supports it by default — TRUST ME buddy, it DOES


---

## Installation

### Quick setup script

Both platforms have a setup script that handles the pip installs:

```bash
# Linux / macOS
bash setup.sh

# Windows
setup.bat
```

---

### Windows

**1. Install Python dependencies:**

```bat
pip install numpy imageio imageio-ffmpeg
```

**2. Clone or download the repo:**

```bat
git clone https://github.com/yourname/buddy
cd buddy
```

**3. Run it:**

```bat
python ascii_play\cli.py video.mp4
```

**4. Make `buddy` available system-wide:**

Add the repo folder to your PATH:

- Open Start, search "environment variables"
- Under User Variables, select `Path` and click Edit
- Click New and paste the full path to the repo folder (e.g. `G:\buddy`)
- Click OK and restart your terminal

Now you can run `buddy video.mp4` from anywhere.

---

### Linux / macOS

**1. Install Python dependencies:**

```bash
pip install numpy imageio imageio-ffmpeg
```

**2. Clone the repo:**

```bash
git clone https://github.com/yourname/buddy
cd buddy
```

**3. Run it directly:**

```bash
python ascii_play/cli.py video.mp4
```

**4. Make `buddy` available system-wide:**

```bash
chmod +x buddy.sh
sudo ln -sf "$(pwd)/buddy.sh" /usr/local/bin/buddy
```

If you don't have sudo, add this to your `~/.bashrc` or `~/.zshrc` instead:

```bash
export PATH="$PATH:/path/to/buddy"
```

Then reload: `source ~/.bashrc`

Now you can run `buddy video.mp4` from anywhere.

---

## Usage

```
buddy <video>                   Play a video (uses defaults)
buddy play <video> [options]    Play with explicit options
buddy modes                     List render modes
buddy help                      Show help
```

### Options

```
-m, --mode   MODE    Render mode: half | ascii | braille  (default: half)
-q, --quality  N     Quality level: 1, 2, or 3            (default: 2)
-s, --scale    F     Fraction of terminal to fill, 0.1-1.0 (default: 1.0)
    --loop           Loop the video indefinitely
    --no-info        Hide the status bar at the bottom
```

### Examples

```bash
# Play with all defaults
buddy video.mp4

# Best quality downscaling
buddy video.mp4 -q 3

# Braille mode, loop forever
buddy video.mp4 -m braille --loop

# Use 80% of the terminal, no status bar
buddy video.mp4 -s 0.8 --no-info

# Classic ASCII art look
buddy video.mp4 -m ascii

# Explicit play subcommand (same result)
buddy play video.mp4 -m half -q 3 -s 0.9
```

---

## Render modes

### half (default)

Uses the Unicode half-block character `▀`. The foreground color maps to the top pixel row of each cell, the background color to the bottom. This encodes 2 pixel rows per terminal row, giving double the vertical resolution of any character-based approach. Combined with 24-bit color, this is the highest quality mode.

Best for: everything. Use this unless you have a specific reason not to.

### ascii

Maps grayscale brightness to a density character set (`@%#*+=-:. `) and applies the source pixel color as the foreground. Familiar look, lower spatial resolution than half-block, but the true-color tinting makes it look significantly better than traditional ASCII art renderers.

Best for: aesthetic preference, lower-contrast content.

### braille

Each braille character cell covers a 2-wide by 4-tall pixel region. Each dot in the braille pattern is lit or unlit based on whether its corresponding source pixel crosses a brightness threshold. This gives the highest spatial resolution of the three modes. Colors are averaged across the 8-pixel cell.

Best for: high-contrast content, line art, animation with sharp edges.

---

## Quality levels

Controls how source pixels are sampled when downscaling to terminal resolution.

| Flag | Method | Notes |
|------|--------|-------|
| `-q 1` | Nearest-neighbor | One source pixel per cell. Fastest. Shimmers on fine detail and motion. |
| `-q 2` | 4-tap supersample | Samples 4 points per cell and averages. Default. Eliminates most aliasing with near-zero extra cost. |
| `-q 3` | Full box filter | Every source pixel within a cell's coverage area is averaged in. Equivalent to a proper video downscaler. Best quality, highest CPU use. |

For most content at 24-30fps, `-q 2` holds frame rate fine. `-q 3` is worth trying if your machine has headroom.

---

## Repo structure

```
buddy/
├── ascii_play/
│   ├── __init__.py       version and public API
│   ├── __main__.py       enables: python -m ascii_play video.mp4
│   ├── cli.py            entry point — run this directly or via buddy wrapper
│   ├── ansi.py           ANSI escape code helpers
│   ├── resize.py         frame downscaling, three quality levels
│   ├── renderers.py      half / ascii / braille render functions
│   └── player.py         FFmpeg decode loop and frame timing
├── buddy.sh              Linux/macOS wrapper script
├── setup.sh              Linux/macOS one-shot setup
├── setup.bat             Windows one-shot setup
└── README.md
```

The package modules are independent of each other with no circular imports. `cli.py` is the only entry point — it imports from the package and dispatches to `player.py`. Adding a new render mode means adding a function to `renderers.py` and registering it in the `MODES` dict — nothing else needs to change.

---

## Running without installing

If you just want to run it without any path setup:

```bash
# from the repo root
python ascii_play/cli.py video.mp4

# or as a module
python -m ascii_play video.mp4
```

---

## License

GNU General Public License v3.0 (GPL-3.0)
