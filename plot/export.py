#!/usr/bin/env python3
import os
import sys
import argparse
from pathlib import Path

# Use a non-interactive backend for file export
import matplotlib as mpl
mpl.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np

from plot_core import load_frames, setup_figure_and_artists, update_artists


def _canvas_to_rgb(fig):
    fig.canvas.draw()
    try:
        buf = fig.canvas.tostring_rgb()  # type: ignore[attr-defined]
        channels = 3
    except Exception:
        buf = fig.canvas.buffer_rgba()
        channels = 4
    cw, ch = fig.canvas.get_width_height()
    arr = np.frombuffer(buf, dtype=np.uint8)
    try:
        arr = arr.reshape((ch, cw, channels))
    except Exception:
        # Fallback: assume RGB
        arr = arr.reshape((ch, cw, 3))
    if channels == 4:
        arr = arr[:, :, :3]
    return arr.copy()


def ensure_pkgs(for_mp4=False):
    missing = []
    try:
        import imageio  # noqa: F401
    except Exception:
        missing.append("imageio")
    if for_mp4:
        try:
            import imageio_ffmpeg  # noqa: F401
        except Exception:
            missing.append("imageio-ffmpeg")
    if missing:
        try:
            import subprocess
            cmd = [sys.executable, "-m", "pip", "install", "--quiet"] + missing
            subprocess.run(cmd, check=False)
        except Exception:
            pass


def export_animation(frames, bounds, outpath, fmt, fps=20, height_px=720, every=1, limit=None):
    ensure_pkgs(for_mp4=(fmt == "mp4"))
    import imageio

    dpi = 100
    # Always fill axes for export (no axes chrome)
    fig, ax, artists = setup_figure_and_artists(bounds, fill_axes=True, dpi=dpi, height_px=height_px)

    # iterate frames
    selected = frames[:: max(1, every)]
    if isinstance(limit, int) and limit > 0:
        selected = selected[:limit]

    if fmt == "gif":
        imgs = []
        for i, fr in enumerate(selected):
            update_artists(artists, fr)
            img = _canvas_to_rgb(fig)
            imgs.append(img)
            if (i + 1) % 50 == 0:
                print(f"Rendered {i+1}/{len(selected)} frames...")
        imageio.mimsave(outpath, imgs, duration=1.0 / max(1, fps))
    else:
        # mp4
        try:
            writer = imageio.get_writer(outpath, fps=fps, codec="libx264", quality=7)
        except Exception:
            # fallback without codec
            writer = imageio.get_writer(outpath, fps=fps)
        with writer as vid_writer:
            for i, fr in enumerate(selected):
                update_artists(artists, fr)
                img = _canvas_to_rgb(fig)
                vid_writer.append_data(img)
                if (i + 1) % 50 == 0:
                    print(f"Rendered {i+1}/{len(selected)} frames...")
    print(f"Saved {fmt.upper()} to {outpath}")


def parse_args():
    p = argparse.ArgumentParser(description="Export warehouse mapping animation to GIF/MP4")
    p.add_argument("--format", choices=["gif", "mp4"], default=None, help="Output format (inferred from --out if omitted)")
    p.add_argument("--out", default=None, help="Output file path (default: main/animation.<fmt>)")
    p.add_argument("--fps", type=int, default=20, help="Frames per second")
    p.add_argument("--height", type=int, default=720, help="Target figure height in pixels")
    p.add_argument("--every", type=int, default=1, help="Keep every Nth frame (thinning)")
    p.add_argument("--limit", type=int, default=None, help="Limit the number of frames")
    return p.parse_args()


def main():
    args = parse_args()

    # Auto-detect data directory (prefers main/)
    frames, bounds = load_frames(None)

    fmt = args.format
    out = args.out
    if out and not fmt:
        if out.lower().endswith(".gif"):
            fmt = "gif"
        elif out.lower().endswith(".mp4"):
            fmt = "mp4"
    if not fmt:
        fmt = "gif"
    if not out:
        # Default to the plot/ folder
        out = str(Path(__file__).resolve().parent / f"animation.{fmt}")

    os.makedirs(os.path.dirname(out), exist_ok=True)

    export_animation(
        frames,
        bounds,
        outpath=out,
        fmt=fmt,
        fps=max(1, args.fps),
        height_px=max(200, args.height),
        every=max(1, args.every),
        limit=args.limit if (args.limit is None or args.limit > 0) else None,
    )


if __name__ == "__main__":
    main()
