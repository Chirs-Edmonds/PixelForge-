"""
render.py — PixelForge Phase 1 routes.

Routes:
    POST /upload-mesh   Upload a .glb file to assets/
    POST /render        Start a Blender render job (background)
    GET  /status/{id}   Poll job status
"""

import asyncio
import subprocess
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from pydantic import BaseModel

from backend.jobs import create_job, get_job, update_job

router = APIRouter()

PROJECT_ROOT    = Path(__file__).parent.parent.parent
BLENDER_EXE     = Path(r"C:\Program Files\Blender Foundation\Blender 4.x\blender.exe")
PYTHON_EXE      = Path(r"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe")
BAKE_SCRIPT     = PROJECT_ROOT / "scripts" / "blender_bake.py"
ASSEMBLE_SCRIPT = PROJECT_ROOT / "scripts" / "assemble_sheet.py"
OUTPUT_FRAMES   = PROJECT_ROOT / "output" / "frames"
OUTPUT_SHEET    = PROJECT_ROOT / "output" / "sprite_sheet.png"
ASSETS_DIR      = PROJECT_ROOT / "assets"

VALID_SIZES = {16, 32, 64, 128, 256}


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------

@router.post("/upload-mesh")
async def upload_mesh(file: UploadFile = File(...)):
    if not file.filename.endswith(".glb"):
        raise HTTPException(400, "Only .glb files are supported.")

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    dest = ASSETS_DIR / file.filename
    async with aiofiles.open(dest, "wb") as out:
        content = await file.read()
        await out.write(content)

    return {"filename": file.filename}


# ---------------------------------------------------------------------------
# Render endpoint
# ---------------------------------------------------------------------------

class RenderRequest(BaseModel):
    sprite_size: int = 64
    mesh_path: str | None = None  # filename within assets/, or None for test primitive


@router.post("/render")
async def start_render(req: RenderRequest, background_tasks: BackgroundTasks):
    if req.sprite_size not in VALID_SIZES:
        raise HTTPException(400, f"sprite_size must be one of {sorted(VALID_SIZES)}.")

    if req.mesh_path:
        mesh_abs = ASSETS_DIR / req.mesh_path
        if not mesh_abs.exists():
            raise HTTPException(404, f"Mesh not found in assets/: {req.mesh_path}")

    job_id = str(uuid.uuid4())
    create_job(job_id)
    background_tasks.add_task(_run_render, job_id, req.sprite_size, req.mesh_path)
    return {"job_id": job_id}


def _run_render(job_id: str, sprite_size: int, mesh_path: str | None) -> None:
    render_size = sprite_size * 4
    update_job(job_id, status="running", step="blender",
               progress_msg=f"Step 1/2: Blender rendering 8 directions at {render_size}px...")

    # Step 1: Blender
    cmd = [
        str(BLENDER_EXE),
        "--background", "--factory-startup",
        "--python", str(BAKE_SCRIPT),
        "--",
        "--outdir", str(OUTPUT_FRAMES),
        "--size",   str(render_size),
    ]
    if mesh_path:
        cmd += ["--mesh", str((ASSETS_DIR / mesh_path).resolve())]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        update_job(job_id, status="error", step="blender",
                   progress_msg="Blender render failed.",
                   error=result.stderr[-2000:] or result.stdout[-2000:])
        return

    # Step 2: Assemble
    update_job(job_id, step="assemble",
               progress_msg=f"Step 2/2: Assembling {sprite_size}px sprite sheet...")

    cmd = [
        str(PYTHON_EXE),
        str(ASSEMBLE_SCRIPT),
        "--framesdir", str(OUTPUT_FRAMES),
        "--outfile",   str(OUTPUT_SHEET),
        "--size",      str(sprite_size),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        update_job(job_id, status="error", step="assemble",
                   progress_msg="Sprite sheet assembly failed.",
                   error=result.stderr[-2000:] or result.stdout[-2000:])
        return

    update_job(job_id, status="done", step="done",
               progress_msg="Render complete.",
               output="sprite_sheet.png")


# ---------------------------------------------------------------------------
# Status endpoint (shared by render and mesh generation jobs)
# ---------------------------------------------------------------------------

@router.get("/status/{job_id}")
async def get_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, f"Job not found: {job_id}")
    return job
