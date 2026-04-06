"""
refine.py — PixelForge Phase 2 routes.

Routes:
    POST /refine    Run Real-ESRGAN upscale and/or palette quantization (synchronous)
"""

import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

PROJECT_ROOT    = Path(__file__).parent.parent.parent
PYTHON_EXE      = Path(r"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe")
REFINE_SCRIPT   = PROJECT_ROOT / "scripts" / "refine.py"
OUTPUT_SHEET    = PROJECT_ROOT / "output" / "sprite_sheet.png"
OUTPUT_REFINED  = PROJECT_ROOT / "output" / "sprite_sheet_refined.png"
ESRGAN_BINARY   = PROJECT_ROOT / "tools" / "realesrgan-ncnn-vulkan" / "realesrgan-ncnn-vulkan.exe"


@router.get("/check-esrgan")
async def check_esrgan():
    return {"available": ESRGAN_BINARY.exists()}


class RefineRequest(BaseModel):
    upscale: bool = False
    colors:  int  = 0      # 0 = skip quantization; useful: 8, 16, 32, 64
    dither:  bool = False


@router.post("/refine")
async def run_refine(req: RefineRequest):
    if not req.upscale and req.colors == 0:
        raise HTTPException(400, "Nothing to do: set upscale=true and/or colors > 0.")

    if not OUTPUT_SHEET.exists():
        raise HTTPException(404, "No sprite sheet found. Run /render first.")

    if req.upscale and not ESRGAN_BINARY.exists():
        raise HTTPException(400,
            "Real-ESRGAN binary not found. "
            "Download realesrgan-ncnn-vulkan-*-windows.zip from "
            "https://github.com/xinntao/Real-ESRGAN/releases "
            "and extract to tools/realesrgan-ncnn-vulkan/")

    if req.colors < 0 or req.colors == 1:
        raise HTTPException(400, "colors must be 0 (skip) or >= 2.")

    cmd = [
        str(PYTHON_EXE),
        str(REFINE_SCRIPT),
        "--infile",  str(OUTPUT_SHEET),
        "--outfile", str(OUTPUT_REFINED),
    ]
    if req.upscale:
        cmd.append("--upscale")
    if req.colors > 0:
        cmd += ["--colors", str(req.colors)]
    if req.dither:
        cmd.append("--dither")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        error_detail = result.stderr[-2000:] or result.stdout[-2000:]
        raise HTTPException(500, f"Refinement failed: {error_detail}")

    return {"output": "sprite_sheet_refined.png"}
