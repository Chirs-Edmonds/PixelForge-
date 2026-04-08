"""
assemble_sheet.py — PixelForge Phase 1

Runs OUTSIDE Blender with system Python (requires Pillow).
Stitches direction PNGs into sprite sheet(s).

Single-frame mode (default):
    python scripts/assemble_sheet.py \
        --framesdir output/frames \
        --outfile output/sprite_sheet.png \
        --size 64

    Reads N.png, NE.png, ... NW.png from framesdir.
    Outputs one (8 * size) x size RGBA PNG.

Animation mode (--animate):
    python scripts/assemble_sheet.py \
        --framesdir output/frames \
        --outdir output/sheets \
        --size 64 \
        --animate

    Reads framesdir/N/0001.png, 0002.png, ... for each direction.
    Outputs 8 sprite sheets: sprite_sheet_N.png, sprite_sheet_NE.png, ...
    Each sheet is (num_frames * size) x size RGBA PNG.

Common sizes:
    16   — micro sprites
    32   — classic RPG / Godot isometric tiles
    64   — modern pixel art, good isometric detail  (default)
    128  — high-res pixel art / pre-downscale preview
    256  — source quality, downscale in engine
"""

import argparse
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit(
        "[PixelForge] Pillow is not installed.\n"
        "Run: py -3.12 -m pip install Pillow"
    )

DIRECTION_ORDER = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Assemble direction PNGs into sprite sheet(s)."
    )
    parser.add_argument("--framesdir", type=str, required=True,
                        help="Directory containing direction frames.")
    parser.add_argument("--outfile", type=str, required=False, default=None,
                        help="Output sprite sheet path (single-frame mode).")
    parser.add_argument("--outdir", type=str, required=False, default=None,
                        help="Output directory for animation sheets (--animate mode).")
    parser.add_argument("--size", type=int, default=64,
                        help="Target sprite size in pixels (square). Default: 64.")
    parser.add_argument("--animate", action="store_true",
                        help="Animation mode: assemble per-direction sheets from subdirectories.")
    args = parser.parse_args()

    if args.animate and not args.outdir:
        parser.error("--animate requires --outdir")
    if not args.animate and not args.outfile:
        parser.error("--outfile is required in single-frame mode")

    return args


def assemble_single(frames_dir, out_file, size):
    print(f"[PixelForge] assemble_sheet.py starting (single-frame mode)")
    print(f"[PixelForge] Frames dir  : {frames_dir}")
    print(f"[PixelForge] Output file : {out_file}")
    print(f"[PixelForge] Sprite size : {size}x{size}")

    frames = []
    for direction in DIRECTION_ORDER:
        png_path = frames_dir / f"{direction}.png"
        if not png_path.exists():
            raise FileNotFoundError(
                f"[PixelForge] Missing frame: {png_path}\n"
                f"Run the Blender bake step first."
            )
        img = Image.open(png_path).convert("RGBA")
        original_size = img.size
        img = img.resize((size, size), Image.LANCZOS)
        frames.append(img)
        print(f"[PixelForge]   {direction}: {original_size[0]}x{original_size[1]} -> {size}x{size}")

    sheet_width = 8 * size
    sheet = Image.new("RGBA", (sheet_width, size), (0, 0, 0, 0))
    for i, frame in enumerate(frames):
        sheet.paste(frame, (i * size, 0))

    out_file.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(out_file), "PNG")

    print(f"[PixelForge] Sprite sheet saved: {out_file}  ({sheet_width}x{size}px)")
    print("[PixelForge] assemble_sheet.py complete.")


def assemble_animation(frames_dir, out_dir, size):
    print(f"[PixelForge] assemble_sheet.py starting (animation mode)")
    print(f"[PixelForge] Frames dir  : {frames_dir}")
    print(f"[PixelForge] Output dir  : {out_dir}")
    print(f"[PixelForge] Sprite size : {size}x{size}")

    out_dir.mkdir(parents=True, exist_ok=True)

    for direction in DIRECTION_ORDER:
        dir_path = frames_dir / direction
        if not dir_path.is_dir():
            raise FileNotFoundError(
                f"[PixelForge] Missing direction subdir: {dir_path}\n"
                f"Run blender_bake.py with --frame-start / --frame-end first."
            )
        frame_files = sorted(dir_path.glob("*.png"), key=lambda p: int(p.stem))
        if not frame_files:
            raise RuntimeError(f"[PixelForge] No PNG files found in {dir_path}")

        num_frames = len(frame_files)
        sheet_width = num_frames * size
        sheet = Image.new("RGBA", (sheet_width, size), (0, 0, 0, 0))

        for i, fpath in enumerate(frame_files):
            img = Image.open(fpath).convert("RGBA").resize((size, size), Image.LANCZOS)
            sheet.paste(img, (i * size, 0))

        out_file = out_dir / f"sprite_sheet_{direction}.png"
        sheet.save(str(out_file), "PNG")
        print(f"[PixelForge]   {direction}: {num_frames} frames -> {out_file}  ({sheet_width}x{size}px)")

    print("[PixelForge] assemble_sheet.py complete.")


def main():
    args = parse_args()
    frames_dir = Path(args.framesdir)
    size = args.size

    if args.animate:
        assemble_animation(frames_dir, Path(args.outdir), size)
    else:
        assemble_single(frames_dir, Path(args.outfile), size)


if __name__ == "__main__":
    main()
