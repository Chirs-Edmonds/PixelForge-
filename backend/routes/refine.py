"""
refine.py — PixelForge Phase 2 routes.

Routes:
    POST /refine        Alpha threshold + palette quantize + nearest-neighbour upscale
    GET  /check-esrgan  Legacy probe — always returns available=true (no binary needed)

Refine logic runs in-process via Pillow (no subprocess). Pillow must be installed in
the same Python environment as uvicorn: py -3.12 -m pip install Pillow
"""

import re
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
OUTPUT_SHEETS  = PROJECT_ROOT / "output" / "sheets"
OUTPUT_MERGED  = PROJECT_ROOT / "output" / "merged"
OUTPUT_REFINED = PROJECT_ROOT / "output" / "refined"

DIRECTIONS  = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
_SAFE_NAME  = re.compile(r'[^a-zA-Z0-9_-]')


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
    body_part:    str  = "full"


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

    # Sanitize name the same way render.py does — files on disk use the safe version.
    name = _SAFE_NAME.sub('_', req.name).strip('_') or 'sprite_sheet'

    if req.is_animation:
        if not OUTPUT_SHEETS.exists():
            raise HTTPException(404, "No animation sheets found. Run /render first.")

        if req.body_part == "split":
            # Split animation: refine only the merged master sheet for each body part.
            failed = []
            has_master_upper = False
            has_master_legs  = False

            for suffix, master_flag in [("_upper", "upper"), ("_legs", "legs")]:
                prefix = f"{name}{suffix}"
                master_src = OUTPUT_MERGED / f"{prefix}_all.png"
                master_dst = OUTPUT_REFINED / f"{prefix}_all_refined.png"
                if not master_src.exists():
                    failed.append(f"{suffix}: no merged master sheet — run render with 'Merge 8-direction' enabled")
                    continue
                try:
                    _refine_image(master_src, master_dst, req.upscale, req.colors, req.dither)
                    if master_flag == "upper":
                        has_master_upper = True
                    else:
                        has_master_legs = True
                except Exception as e:
                    failed.append(f"{suffix}/master: {e}")

            if failed:
                raise HTTPException(500, f"Refinement failed: {'; '.join(failed)}")

            return {
                "output":           f"sheets/{name}",
                "is_animation":     True,
                "is_split":         True,
                "has_master_upper": has_master_upper,
                "has_master_legs":  has_master_legs,
            }

        # Non-split animation: refine only the merged master sheet.
        master_src = OUTPUT_MERGED / f"{name}_all.png"
        master_dst = OUTPUT_REFINED / f"{name}_all_refined.png"
        if not master_src.exists():
            raise HTTPException(
                404,
                "No merged master sheet found. Run /render with 'Merge 8-direction' enabled first."
            )
        try:
            _refine_image(master_src, master_dst, req.upscale, req.colors, req.dither)
        except Exception as e:
            raise HTTPException(500, f"Refinement failed: {e}")

        return {"output": f"sheets/{name}", "is_animation": True, "has_master": True}

    # Single-frame — split produces two files
    if req.body_part == "split":
        suffixes = [("_upper", f"{name}_upper"), ("_legs", f"{name}_legs")]
        outputs = []
        for _, base in suffixes:
            src = PROJECT_ROOT / "output" / f"{base}.png"
            dst = OUTPUT_REFINED / f"{base}_refined.png"
            if not src.exists():
                raise HTTPException(404, f"No sprite sheet found: {base}.png. Run /render first.")
            try:
                _refine_image(src, dst, req.upscale, req.colors, req.dither)
                outputs.append(f"refined/{base}_refined.png")
            except Exception as e:
                raise HTTPException(500, f"Refinement failed for {base}: {e}")
        return {"output": outputs, "is_split": True}

    # Single-frame — full / upper / lower
    src = PROJECT_ROOT / "output" / f"{name}.png"
    dst = OUTPUT_REFINED / f"{name}_refined.png"
    if not src.exists():
        raise HTTPException(404, "No sprite sheet found. Run /render first.")
    try:
        _refine_image(src, dst, req.upscale, req.colors, req.dither)
    except Exception as e:
        raise HTTPException(500, f"Refinement failed: {e}")
    return {"output": f"refined/{name}_refined.png"}
