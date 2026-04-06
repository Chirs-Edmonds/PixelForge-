"""
refine.py — PixelForge Phase 2

Runs OUTSIDE Blender with system Python. Requires Pillow.
Optionally runs Real-ESRGAN upscaling (via ncnn-vulkan binary) and/or palette quantization.

Usage:
    python scripts/refine.py \
        --infile  output/sprite_sheet.png \
        --outfile output/sprite_sheet_refined.png \
        [--upscale] \
        [--colors 16] \
        [--dither]

Arguments:
    --infile  PATH   Input PNG (required)
    --outfile PATH   Output PNG (required)
    --upscale        Run Real-ESRGAN x4 upscale before any other processing
    --colors  INT    Quantize palette to N colors (0 = skip, default 0)
                     Useful values: 8, 16, 32, 64
    --dither         Use Floyd-Steinberg dithering during quantize
                     (omit for no dithering — sharper for pixel art)

Real-ESRGAN binary must be extracted to:
    tools/realesrgan-ncnn-vulkan/realesrgan-ncnn-vulkan.exe
    tools/realesrgan-ncnn-vulkan/models/realesrgan-x4plus-anime.param
    tools/realesrgan-ncnn-vulkan/models/realesrgan-x4plus-anime.bin

Download from: https://github.com/xinntao/Real-ESRGAN/releases
File: realesrgan-ncnn-vulkan-*-windows.zip
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit(
        "[PixelForge] Pillow is not installed.\n"
        "Run: py -3.12 -m pip install Pillow"
    )

# Path to Real-ESRGAN binary, relative to this script's parent (project root)
PROJECT_ROOT = Path(__file__).parent.parent
REALESRGAN_DIR = PROJECT_ROOT / "tools" / "realesrgan-ncnn-vulkan"
REALESRGAN_EXE = REALESRGAN_DIR / "realesrgan-ncnn-vulkan.exe"
REALESRGAN_MODEL = "realesrgan-x4plus-anime"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Refine a sprite sheet: Real-ESRGAN upscale and/or palette quantization."
    )
    parser.add_argument("--infile",  type=str, required=True, help="Input PNG path.")
    parser.add_argument("--outfile", type=str, required=True, help="Output PNG path.")
    parser.add_argument("--upscale", action="store_true",
                        help="Run Real-ESRGAN x4 upscale (requires binary in tools/).")
    parser.add_argument("--colors", type=int, default=0,
                        help="Quantize palette to N colors (0 = skip). Default: 0.")
    parser.add_argument("--dither", action="store_true",
                        help="Use Floyd-Steinberg dithering during quantize.")
    args = parser.parse_args()

    if not args.upscale and args.colors == 0:
        parser.error("Nothing to do: pass --upscale and/or --colors N.")

    return args


def run_realesrgan(infile: Path, outfile: Path) -> None:
    """Call the Real-ESRGAN ncnn-vulkan binary to upscale infile → outfile."""
    if not REALESRGAN_EXE.exists():
        raise FileNotFoundError(
            f"[PixelForge] Real-ESRGAN binary not found at: {REALESRGAN_EXE}\n"
            "Download realesrgan-ncnn-vulkan-*-windows.zip from:\n"
            "  https://github.com/xinntao/Real-ESRGAN/releases\n"
            f"Extract to: {REALESRGAN_DIR}"
        )

    cmd = [
        str(REALESRGAN_EXE),
        "-i", str(infile),
        "-o", str(outfile),
        "-n", REALESRGAN_MODEL,
    ]

    print(f"[PixelForge] Running Real-ESRGAN: {' '.join(cmd)}")
    # cwd must be the binary's directory so it finds the models/ subfolder
    result = subprocess.run(cmd, cwd=str(REALESRGAN_DIR))
    if result.returncode != 0:
        raise RuntimeError(
            f"[PixelForge] Real-ESRGAN exited with code {result.returncode}.\n"
            "Ensure the binary and models/ folder are present in tools/realesrgan-ncnn-vulkan/.\n"
            "Also ensure your GPU supports Vulkan (or use the CPU fallback)."
        )
    print(f"[PixelForge] Real-ESRGAN upscale complete: {outfile}")


def quantize_palette(img: Image.Image, colors: int, dither: bool) -> Image.Image:
    """Quantize an RGBA image to N colors, returning an RGBA image."""
    dither_mode = Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE

    # quantize() only works reliably on RGB or L; handle alpha separately
    rgb = img.convert("RGB")
    alpha = img.split()[3]  # preserve alpha channel

    quantized_rgb = rgb.quantize(colors=colors, dither=dither_mode)
    # Convert back to RGB (palette mode → full color), then reattach alpha
    quantized_rgb = quantized_rgb.convert("RGB")

    result = quantized_rgb.convert("RGBA")
    result.putalpha(alpha)
    return result


def main():
    args = parse_args()
    infile  = Path(args.infile).resolve()
    outfile = Path(args.outfile).resolve()

    if not infile.exists():
        raise FileNotFoundError(f"[PixelForge] Input file not found: {infile}")

    print(f"[PixelForge] refine.py starting")
    print(f"[PixelForge] Input  : {infile}")
    print(f"[PixelForge] Output : {outfile}")
    print(f"[PixelForge] Upscale: {'yes (Real-ESRGAN x4)' if args.upscale else 'no'}")
    print(f"[PixelForge] Colors : {args.colors if args.colors > 0 else 'skip'}")
    if args.colors > 0:
        print(f"[PixelForge] Dither : {'Floyd-Steinberg' if args.dither else 'none'}")

    working = infile

    # --- Step 1: Upscale ---
    if args.upscale:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            upscaled_path = Path(tmp.name)
        try:
            run_realesrgan(working, upscaled_path)
            working = upscaled_path
        except Exception:
            if upscaled_path.exists():
                upscaled_path.unlink()
            raise

    # --- Step 2: Palette quantization ---
    img = Image.open(working).convert("RGBA")
    original_size = img.size

    if args.colors > 0:
        print(f"[PixelForge] Quantizing to {args.colors} colors...")
        img = quantize_palette(img, args.colors, args.dither)
        print(f"[PixelForge] Quantize complete.")

    # --- Save ---
    outfile.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(outfile), "PNG")

    final_size = img.size
    print(f"[PixelForge] Saved: {outfile}  ({final_size[0]}x{final_size[1]}px, was {original_size[0]}x{original_size[1]}px)")
    print("[PixelForge] refine.py complete.")

    # Clean up temp upscale file
    if args.upscale and 'upscaled_path' in locals() and upscaled_path != infile:
        try:
            upscaled_path.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    main()
