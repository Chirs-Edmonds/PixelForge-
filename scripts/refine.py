"""
refine.py — PixelForge Phase 2

Runs OUTSIDE Blender with system Python. Requires Pillow.

Pipeline (in order):
  1. Alpha threshold  — clamp semi-transparent edge pixels to fully opaque or fully
                        transparent (hard sprite outlines, no feathering).
  2. Palette quantize — reduce to N colors BEFORE upscaling so the upscaler sees
                        flat color blocks, not gradients.
  3. Nearest-neighbor upscale — scale by --scale factor with no interpolation,
                        preserving every hard pixel edge.

Usage:
    python scripts/refine.py \
        --infile  output/sprite_sheet.png \
        --outfile output/sprite_sheet_refined.png \
        [--upscale] [--scale 4] \
        [--colors 16] \
        [--dither]

Arguments:
    --infile  PATH    Input PNG (required)
    --outfile PATH    Output PNG (required)
    --upscale         Nearest-neighbor upscale after quantize
    --scale   INT     Upscale factor (default 4)
    --colors  INT     Quantize palette to N colors (0 = skip, default 0)
    --dither          Use Floyd-Steinberg dithering during quantize
                      (omit for no dithering — sharper for pixel art)
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit(
        "[PixelForge] Pillow is not installed.\n"
        "Run: py -3.12 -m pip install Pillow"
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Refine a sprite sheet: alpha threshold, palette quantize, pixel upscale."
    )
    parser.add_argument("--infile",  type=str, required=True,  help="Input PNG path.")
    parser.add_argument("--outfile", type=str, required=True,  help="Output PNG path.")
    parser.add_argument("--upscale", action="store_true",      help="Nearest-neighbour upscale.")
    parser.add_argument("--scale",   type=int, default=4,      help="Upscale factor (default 4).")
    parser.add_argument("--colors",  type=int, default=0,
                        help="Quantize palette to N colors (0 = skip). Default: 0.")
    parser.add_argument("--dither",  action="store_true",
                        help="Floyd-Steinberg dithering during quantize.")
    args = parser.parse_args()

    if not args.upscale and args.colors == 0:
        parser.error("Nothing to do: pass --upscale and/or --colors N.")
    if args.scale < 1:
        parser.error("--scale must be >= 1.")

    return args


def alpha_threshold(img: Image.Image, cutoff: int = 128) -> Image.Image:
    """Clamp semi-transparent pixels to fully opaque or fully transparent."""
    r, g, b, a = img.split()
    a = a.point(lambda v: 255 if v >= cutoff else 0)
    return Image.merge("RGBA", (r, g, b, a))


def quantize_palette(img: Image.Image, colors: int, dither: bool) -> Image.Image:
    """Quantize an RGBA image to N colors, preserving the thresholded alpha."""
    dither_mode = Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE
    alpha = img.split()[3]
    rgb = img.convert("RGB")
    quantized = rgb.quantize(colors=colors, dither=dither_mode).convert("RGB")
    result = quantized.convert("RGBA")
    result.putalpha(alpha)
    return result


def nearest_upscale(img: Image.Image, factor: int) -> Image.Image:
    w, h = img.size
    return img.resize((w * factor, h * factor), Image.NEAREST)


def main():
    args = parse_args()
    infile  = Path(args.infile).resolve()
    outfile = Path(args.outfile).resolve()

    if not infile.exists():
        raise FileNotFoundError(f"[PixelForge] Input file not found: {infile}")

    print(f"[PixelForge] refine.py starting")
    print(f"[PixelForge] Input   : {infile}")
    print(f"[PixelForge] Output  : {outfile}")
    print(f"[PixelForge] Colors  : {args.colors if args.colors > 0 else 'skip'}")
    if args.colors > 0:
        print(f"[PixelForge] Dither  : {'Floyd-Steinberg' if args.dither else 'none'}")
    print(f"[PixelForge] Upscale : {'x' + str(args.scale) + ' nearest-neighbour' if args.upscale else 'no'}")

    img = Image.open(infile).convert("RGBA")
    original_size = img.size

    # Step 1: Hard alpha edges (always applied — removes EEVEE feathering)
    img = alpha_threshold(img)

    # Step 2: Palette quantize (before upscale so gradients collapse into flat blocks)
    if args.colors > 0:
        print(f"[PixelForge] Quantizing to {args.colors} colors...")
        img = quantize_palette(img, args.colors, args.dither)
        print(f"[PixelForge] Quantize complete.")

    # Step 3: Nearest-neighbour upscale
    if args.upscale:
        print(f"[PixelForge] Upscaling x{args.scale} (nearest-neighbour)...")
        img = nearest_upscale(img, args.scale)
        print(f"[PixelForge] Upscale complete.")

    outfile.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(outfile), "PNG")

    final_size = img.size
    print(f"[PixelForge] Saved: {outfile}  ({final_size[0]}x{final_size[1]}px, was {original_size[0]}x{original_size[1]}px)")
    print("[PixelForge] refine.py complete.")


if __name__ == "__main__":
    main()
