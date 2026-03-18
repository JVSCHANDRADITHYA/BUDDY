## How it works

A terminal screen is a grid of character cells. Each cell can display one character, with a foreground color and a background color — both settable via ANSI escape codes. Modern terminals accept full 24-bit RGB for both: `\033[38;2;R;G;Bm` sets the foreground, `\033[48;2;R;G;Bm` sets the background.

buddy exploits this by using the Unicode half-block character `▀` (U+2580). This character fills the top half of a cell with the foreground color and leaves the bottom half as the background color. So one terminal cell encodes two pixel rows — the top pixel as foreground, the bottom pixel as background. That doubles the effective vertical resolution with no font tricks, no pixel shaders, nothing special required from the terminal beyond true color support.

For a 200×50 terminal, that gives a 200×100 pixel canvas. Every pixel gets its own independent RGB value.

**Downscaling**

The source video is typically 1080p or 720p, being mapped down to ~200×100. How you do that downscaling determines most of the perceptual quality.

Nearest-neighbor picks one source pixel per output cell and throws the rest away. It's fast but produces shimmer and aliasing on motion — different frames pick different source pixels for the same cell, causing it to flicker.

buddy defaults to area averaging: for each output cell, it identifies all source pixels that fall within that cell's coverage area and averages their colors together. This is how proper video downscalers work. Motion is smooth, edges are stable, fine detail is represented rather than randomly sampled.

There are three quality levels:

- `-q 1` — nearest-neighbor, one source pixel per cell
- `-q 2` — 4-tap sample, four source pixels averaged per cell (default)
- `-q 3` — full box filter, every source pixel in the coverage area averaged

**Rendering pipeline**

The bottleneck in a naive implementation is the Python loop over every pixel — at 200×50 that's 10,000 iterations per frame, 24 times a second. buddy eliminates this entirely using NumPy's vectorized operations. The entire frame is processed as array operations that execute in C. The only Python-level loop is over terminal rows (50 iterations) to join the ANSI strings, not over pixels.

FFmpeg decode goes through `imageio-ffmpeg`, which shells out to a native FFmpeg binary. Raw RGB frames come back as byte buffers. Python never touches individual pixels during decode either — it just reshapes the buffer into a NumPy array and hands it to the renderer.

The result: the per-frame Python overhead is small enough that frame timing is dominated by terminal I/O, not computation.