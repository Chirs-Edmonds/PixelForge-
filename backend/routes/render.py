"""
render.py — PixelForge Phase 1 routes.

Routes:
    POST /upload-mesh   Upload a .glb file to assets/
    POST /render        Start a Blender render job (background)
    GET  /status/{id}   Poll job status
"""

import shutil
import subprocess
import tempfile
import traceback
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
OUTPUT_SHEETS   = PROJECT_ROOT / "output" / "sheets"
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
    mesh_path: str | None = None      # filename within assets/, or None for test primitive
    frame_start: int | None = None    # animation: first frame
    frame_end: int | None = None      # animation: last frame


@router.post("/render")
async def start_render(req: RenderRequest, background_tasks: BackgroundTasks):
    if req.sprite_size not in VALID_SIZES:
        raise HTTPException(400, f"sprite_size must be one of {sorted(VALID_SIZES)}.")

    if req.mesh_path:
        mesh_abs = ASSETS_DIR / req.mesh_path
        if not mesh_abs.exists():
            raise HTTPException(404, f"Mesh not found in assets/: {req.mesh_path}")

    if (req.frame_start is None) != (req.frame_end is None):
        raise HTTPException(400, "frame_start and frame_end must both be provided for animation.")

    job_id = str(uuid.uuid4())
    create_job(job_id)
    background_tasks.add_task(
        _run_render, job_id, req.sprite_size, req.mesh_path, req.frame_start, req.frame_end
    )
    return {"job_id": job_id}


LOG_FILE = PROJECT_ROOT / "output" / "last_render.log"


def _clear_dir(path: Path) -> None:
    """Remove a directory tree, tolerating Windows directory-handle locks.

    Tries a full rmtree first. If Windows raises PermissionError on a locked
    subdirectory, falls back to deleting only files so no stale PNGs survive.
    """
    if not path.exists():
        return
    try:
        shutil.rmtree(path)
    except PermissionError:
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    item.unlink()
                except OSError:
                    pass


def _run_subprocess(cmd: list, label: str) -> tuple[int, str]:
    """Run a subprocess, write output to a persistent log file, return (returncode, output)."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8", errors="replace") as log:
        log.write(f"\n=== {label} ===\nCMD: {' '.join(cmd)}\n\n")
        log.flush()
        result = subprocess.run(cmd, stdout=log, stderr=log)
        log.write(f"\n=== {label} exit={result.returncode} ===\n")

    output = LOG_FILE.read_text(encoding="utf-8", errors="replace")
    print(f"[PixelForge Backend] {label} exit={result.returncode} — full log: {LOG_FILE}")
    return result.returncode, output


def _run_render(
    job_id: str,
    sprite_size: int,
    mesh_path: str | None,
    frame_start: int | None,
    frame_end: int | None,
) -> None:
    try:
        _run_render_inner(job_id, sprite_size, mesh_path, frame_start, frame_end)
    except Exception:
        tb = traceback.format_exc()
        print(f"[PixelForge Backend] UNHANDLED ERROR in _run_render:\n{tb}")
        update_job(job_id, status="error", step="error",
                   progress_msg="Internal pipeline error — see backend terminal.",
                   error=tb[-2000:])


def _run_render_inner(
    job_id: str,
    sprite_size: int,
    mesh_path: str | None,
    frame_start: int | None,
    frame_end: int | None,
) -> None:
    render_size = sprite_size
    is_animation = (
        frame_start is not None
        and frame_end is not None
        and frame_end > frame_start
    )

    if is_animation:
        num_frames = frame_end - frame_start + 1
        progress = f"Step 1/2: Blender rendering {num_frames} frames × 8 directions at {render_size}px..."
    else:
        progress = f"Step 1/2: Blender rendering 8 directions at {render_size}px..."

    update_job(job_id, status="running", step="blender", progress_msg=progress)

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
    if is_animation:
        cmd += ["--frame-start", str(frame_start), "--frame-end", str(frame_end)]

    # Clear stale state from previous runs.
    _clear_dir(OUTPUT_FRAMES)
    OUTPUT_FRAMES.mkdir(parents=True, exist_ok=True)
    if is_animation:
        _clear_dir(OUTPUT_SHEETS)
    sentinel = OUTPUT_FRAMES / ".render_done"
    LOG_FILE.write_text("", encoding="utf-8")  # clear log for this render

    returncode, output = _run_subprocess(cmd, "blender")

    # Blender exits with code 0 even when its embedded Python script crashes.
    # blender_bake.py writes a sentinel file only on successful completion.
    blender_ok = sentinel.exists()

    if returncode != 0 or not blender_ok:
        error_msg = output.strip()[-2000:] or "Blender produced no output. Check the backend terminal."
        update_job(job_id, status="error", step="blender",
                   progress_msg="Blender render failed — see error details.",
                   error=error_msg)
        return

    # Step 2: Assemble
    if is_animation:
        update_job(job_id, step="assemble",
                   progress_msg=f"Step 2/2: Assembling {sprite_size}px animation sheets (8 directions)...")
        OUTPUT_SHEETS.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(PYTHON_EXE),
            str(ASSEMBLE_SCRIPT),
            "--framesdir", str(OUTPUT_FRAMES),
            "--outdir",    str(OUTPUT_SHEETS),
            "--size",      str(sprite_size),
            "--animate",
        ]
    else:
        update_job(job_id, step="assemble",
                   progress_msg=f"Step 2/2: Assembling {sprite_size}px sprite sheet...")
        cmd = [
            str(PYTHON_EXE),
            str(ASSEMBLE_SCRIPT),
            "--framesdir", str(OUTPUT_FRAMES),
            "--outfile",   str(OUTPUT_SHEET),
            "--size",      str(sprite_size),
        ]

    returncode, output = _run_subprocess(cmd, "assemble")
    if returncode != 0:
        error_msg = output.strip()[-2000:] or "Assembly script exited with an error. Check the backend terminal."
        update_job(job_id, status="error", step="assemble",
                   progress_msg="Sprite sheet assembly failed — see error details.",
                   error=error_msg)
        return

    update_job(job_id, status="done", step="done",
               progress_msg="Render complete.",
               output="sheets/" if is_animation else "sprite_sheet.png")


# ---------------------------------------------------------------------------
# Status endpoint (shared by render and mesh generation jobs)
# ---------------------------------------------------------------------------

@router.get("/status/{job_id}")
async def get_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, f"Job not found: {job_id}")
    return job
