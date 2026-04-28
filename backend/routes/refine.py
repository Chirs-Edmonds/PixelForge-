"""
refine.py — PixelForge Phase 2 routes.

Routes:
    POST /refine        Alpha threshold + palette quantize + nearest-neighbour upscale
    GET  /check-esrgan  Legacy probe — always returns available=true (no binary needed)

Refine logic runs in-process via Pillow (no subprocess). Pillow must be installed in
the same Python environment as uvicorn: py -3.12 -m pip install Pillow
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from PIL import Image
except ImportError:
    raise RuntimeError(
        "Pillow is not installed in the backend environment. "
        "Run: py -3.12 -m pip install Pillow"
    )

router = APIRouter()

PROJECT_ROOT   = Path(__file__).parent.parent.parent
OUTPUT_SHEET   = PROJECT_ROOT / "output" / "sprite_sheet.png"
OUTPUT_REFINED = PROJECT_ROOT / "output" / "sprite_sheet_refined.png"
OUTPUT_SHEETS  = PROJECT_ROOT / "output" / "sheets"

DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']


@router.get("/check-esrgan")
async def check_esrgan():
    # Upscale is now pure-Pillow nearest-neighbour — no external binary required.
    return {"available": True}


class RefineRequest(BaseModel):
    upscale:      bool = False
    colors:       int  = 0      # 0 = skip quantization; useful: 8, 16, 32, 64
    dither:       bool = False
    is_animation: bool = False
    name:         str  = "sprite_sheet"


def _refine_image(src: Path, dst: Path, upscale: bool, colors: int, dither: bool) -> None:
    """Process one PNG: alpha threshold → palette quantize → nearest-neighbour upscale."""
    img = Image.open(src).convert("RGBA")

    # Hard alpha edges: EEVEE produces feathered transparency on sprite borders.
    r, g, b, a = img.split()
    a = a.point(lambda v: 255 if v >= 128 else 0)
    img = Image.merge("RGBA", (r, g, b, a))

    # Palette quantize before upscale so gradients collapse to flat blocks first.
    if colors > 0:
        dither_mode = Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE
        alpha = img.split()[3]
        quantized = img.convert("RGB").quantize(colors=colors, dither=dither_mode).convert("RGB")
        quantized = quantized.convert("RGBA")
        quantized.putalpha(alpha)
        img = quantized

    # Nearest-neighbour 4x upscale: preserves every hard pixel edge.
    if upscale:
        w, h = img.size
        img = img.resize((w * 4, h * 4), Image.NEAREST)

    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(dst), "PNG")


@router.post("/refine")
async def run_refine(req: RefineRequest):
    if not req.upscale and req.colors == 0:
        raise HTTPException(400, "Nothing to do: set upscale=true and/or colors > 0.")
    if req.colors < 0 or req.colors == 1:
        raise HTTPException(400, "colors must be 0 (skip) or >= 2.")

    if req.is_animation:
        if not OUTPUT_SHEETS.exists():
            raise HTTPException(404, "No animation sheets found. Run /render first.")

        failed = []
        for d in DIRECTIONS:
            src = OUTPUT_SHEETS / f"{req.name}_{d}.png"
            dst = OUTPUT_SHEETS / f"{req.name}_{d}_refined.png"
            if not src.exists():
                continue
            try:
                _refine_image(src, dst, req.upscale, req.colors, req.dither)
            except Exception as e:
                failed.append(f"{d}: {e}")

        has_master = False
        master_src = OUTPUT_SHEETS / f"{req.name}_all.png"
        master_dst = OUTPUT_SHEETS / f"{req.name}_all_refined.png"
        if master_src.exists():
            try:
                _refine_image(master_src, master_dst, req.upscale, req.colors, req.dither)
                has_master = True
            except Exception as e:
                failed.append(f"master: {e}")

        if failed:
            raise HTTPException(500, f"Refinement failed: {'; '.join(failed)}")

        return {"output": f"sheets/{req.name}", "is_animation": True, "has_master": has_master}

    # Single-frame
    if not OUTPUT_SHEET.exists():
        raise HTTPException(404, "No sprite sheet found. Run /render first.")

    try:
        _refine_image(OUTPUT_SHEET, OUTPUT_REFINED, req.upscale, req.colors, req.dither)
    except Exception as e:
        raise HTTPException(500, f"Refinement failed: {e}")

    return {"output": "sprite_sheet_refined.png"}
