"""
assemble_sheet.py — PixelForge Phase 1

Runs OUTSIDE Blender with system Python (requires Pillow).
Stitches 8 direction PNGs into a single horizontal sprite sheet.

Usage:
    python scripts/assemble_sheet.py \
        --framesdir output/frames \
        --outfile output/sprite_sheet.png \
        --size 64

Arguments:
    --framesdir DIR   Directory containing N.png, NE.png, ... NW.png (required)
    --outfile   PATH  Output sprite sheet path (required)
    --size      INT   Target sprite size in pixels, square (default: 64)

Output:
    A single (8 * size) x size RGBA PNG with frames ordered:
    N, NE, E, SE, S, SW, W, NW (left to right)

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
        description="Assemble 8 direction PNGs into a sprite sheet."
    )
    parser.add_argument("--framesdir", type=str, required=True,
                        help="Directory containing N.png … NW.png")
    parser.add_argument("--outfile", type=str, required=True,
                        help="Output sprite sheet path (PNG)")
    parser.add_argument("--size", type=int, default=64,
                        help="Target sprite size in pixels (square). Default: 64.")
    return parser.parse_args()


def main():
    args = parse_args()
    frames_dir = Path(args.framesdir)
    out_file = Path(args.outfile)
    size = args.size

    print(f"[PixelForge] assemble_sheet.py starting")
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

    # Horizontal strip: 8 frames wide, 1 frame tall
    sheet_width = 8 * size
    sheet = Image.new("RGBA", (sheet_width, size), (0, 0, 0, 0))
    for i, frame in enumerate(frames):
        sheet.paste(frame, (i * size, 0))

    out_file.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(out_file), "PNG")

    print(f"[PixelForge] Sprite sheet saved: {out_file}  ({sheet_width}x{size}px)")
    print("[PixelForge] assemble_sheet.py complete.")


if __name__ == "__main__":
    main()
