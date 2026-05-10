"""
refine.py — PixelForge Phase 2

Runs OUTSIDE Blender with system Python. Requires Pillow.

Pipeline (in order):
  1. Alpha threshold  — clamp semi-transparent pixels to fully opaque/transparent.
  2. Posterize        — hard colour banding (before quantize).
  3. Palette quantize — reduce to N colors; supports floyd/bayer/none dithering.
  4. Quality pass     — NN ×4 upscale → LANCZOS downscale → second threshold.
  5. Outline          — 1px border injected around sprite silhouette.

Usage:
    python scripts/refine.py \
        --infile  output/sprite_sheet.png \
        --outfile output/sprite_sheet_refined.png \
        [--upscale] [--scale 4] \
        [--alpha-cutoff 16] \
        [--colors 16] [--dither-mode floyd|bayer|none] \
        [--posterize-bits 2|3|4] \
        [--outline] [--outline-color #000000]
"""

import argparse
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageFilter, ImageOps
except ImportError:
    raise SystemExit(
        "[PixelForge] Pillow is not installed.\n"
        "Run: py -3.12 -m pip install Pillow"
    )

_DITHER_MAP = {
    "floyd": Image.Dither.FLOYDSTEINBERG,
    "bayer": getattr(Image.Dither, "ORDERED", Image.Dither.FLOYDSTEINBERG),
    "none":  Image.Dither.NONE,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Refine a sprite sheet: threshold, posterize, quantize, quality pass, outline."
    )
    parser.add_argument("--infile",         type=str, required=True)
    parser.add_argument("--outfile",        type=str, required=True)
    parser.add_argument("--upscale",        action="store_true",   help="NN ×4 quality pass.")
    parser.add_argument("--scale",          type=int, default=4,   help="Upscale factor (default 4).")
    parser.add_argument("--alpha-cutoff",   type=int, default=16,  help="Alpha threshold cutoff (1–254, default 16).")
    parser.add_argument("--colors",         type=int, default=0,   help="Quantize to N colors (0=skip).")
    parser.add_argument("--dither-mode",    type=str, default="none", choices=["none", "floyd", "bayer"])
    parser.add_argument("--posterize-bits", type=int, default=0,   help="Posterize colour depth (0=skip, 2/3/4).")
    parser.add_argument("--outline",        action="store_true",   help="Inject 1px outline around sprite.")
    parser.add_argument("--outline-color",  type=str, default="#000000", help="Outline hex colour.")
    args = parser.parse_args()

    nothing = not args.upscale and args.colors == 0 and not args.outline and args.posterize_bits == 0
    if nothing:
        parser.error("Nothing to do: pass --upscale, --colors N, --outline, or --posterize-bits N.")
    if args.scale < 1:
        parser.error("--scale must be >= 1.")
    if not (1 <= args.alpha_cutoff <= 254):
        parser.error("--alpha-cutoff must be between 1 and 254.")
    return args


def alpha_threshold(img: Image.Image, cutoff: int = 16) -> Image.Image:
    r, g, b, a = img.split()
    a = a.point(lambda v: 255 if v >= cutoff else 0)
    return Image.merge("RGBA", (r, g, b, a))


def posterize(img: Image.Image, bits: int) -> Image.Image:
    alpha = img.split()[3]
    rgb = ImageOps.posterize(img.convert("RGB"), bits)
    result = rgb.convert("RGBA")
    result.putalpha(alpha)
    return result


def quantize_palette(img: Image.Image, colors: int, dither_mode: str) -> Image.Image:
    dither_enum = _DITHER_MAP.get(dither_mode, Image.Dither.NONE)
    alpha = img.split()[3]
    try:
        quantized = img.convert("RGB").quantize(colors=colors, dither=dither_enum)
    except Exception:
        quantized = img.convert("RGB").quantize(colors=colors, dither=Image.Dither.NONE)
    result = quantized.convert("RGBA")
    result.putalpha(alpha)
    return result


def nearest_upscale(img: Image.Image, factor: int) -> Image.Image:
    w, h = img.size
    return img.resize((w * factor, h * factor), Image.NEAREST)


def inject_outline(img: Image.Image, color: str) -> Image.Image:
    hex_c = color.lstrip('#').ljust(6, '0')
    r_c = int(hex_c[0:2], 16)
    g_c = int(hex_c[2:4], 16)
    b_c = int(hex_c[4:6], 16)
    alpha_ch = img.split()[3]
    dilated  = alpha_ch.filter(ImageFilter.MaxFilter(3))
    border   = ImageChops.difference(dilated, alpha_ch)
    colour_layer = Image.new("RGBA", img.size, (r_c, g_c, b_c, 255))
    result = img.copy()
    result.paste(colour_layer, mask=border)
    return result


def main():
    args = parse_args()
    infile  = Path(args.infile).resolve()
    outfile = Path(args.outfile).resolve()

    if not infile.exists():
        raise FileNotFoundError(f"[PixelForge] Input file not found: {infile}")

    print(f"[PixelForge] refine.py starting")
    print(f"[PixelForge] Input        : {infile}")
    print(f"[PixelForge] Output       : {outfile}")
    print(f"[PixelForge] Alpha cutoff : {args.alpha_cutoff}")
    print(f"[PixelForge] Posterize    : {args.posterize_bits}-bit" if args.posterize_bits else "[PixelForge] Posterize    : skip")
    print(f"[PixelForge] Colors       : {args.colors if args.colors > 0 else 'skip'}")
    if args.colors > 0:
        print(f"[PixelForge] Dither mode  : {args.dither_mode}")
    print(f"[PixelForge] Quality pass : x{args.scale} NN+LANCZOS" if args.upscale else "[PixelForge] Quality pass : skip")
    print(f"[PixelForge] Outline      : {args.outline_color}" if args.outline else "[PixelForge] Outline      : skip")

    img = Image.open(infile).convert("RGBA")
    original_size = img.size

    # Step 1: Alpha threshold
    img = alpha_threshold(img, cutoff=args.alpha_cutoff)

    # Step 2: Posterize
    if args.posterize_bits > 0:
        print(f"[PixelForge] Posterizing ({args.posterize_bits}-bit)...")
        img = posterize(img, args.posterize_bits)

    # Step 3: Palette quantize
    if args.colors > 0:
        print(f"[PixelForge] Quantizing to {args.colors} colors ({args.dither_mode} dither)...")
        img = quantize_palette(img, args.colors, args.dither_mode)

    # Step 4: NN upscale → LANCZOS downscale → second threshold (quality pass).
    if args.upscale:
        print(f"[PixelForge] Quality pass (x{args.scale} NN → LANCZOS → threshold)...")
        img = nearest_upscale(img, args.scale)
        img = img.resize(original_size, Image.LANCZOS)
        img = alpha_threshold(img, cutoff=128)

    # Step 5: Outline injection
    if args.outline:
        print(f"[PixelForge] Injecting outline ({args.outline_color})...")
        img = inject_outline(img, args.outline_color)

    outfile.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(outfile), "PNG")

    final_size = img.size
    print(f"[PixelForge] Saved: {outfile}  ({final_size[0]}x{final_size[1]}px, was {original_size[0]}x{original_size[1]}px)")
    print("[PixelForge] refine.py complete.")


if __name__ == "__main__":
    main()
