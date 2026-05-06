"""
render.py — PixelForge Phase 1 routes.

Routes:
    POST /upload-mesh   Upload a .glb file to assets/
    POST /render        Start a Blender render job (background)
    GET  /status/{id}   Poll job status
"""

import re
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
OUTPUT_SHEETS   = PROJECT_ROOT / "output" / "sheets"
ASSETS_DIR      = PROJECT_ROOT / "assets"

VALID_SIZES = {16, 32, 64, 128, 256}


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------

_ALLOWED_MESH_EXTENSIONS = (".glb", ".gltf", ".blend", ".fbx", ".obj")


@router.post("/upload-mesh")
async def upload_mesh(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(_ALLOWED_MESH_EXTENSIONS):
        raise HTTPException(400, "Supported formats: .glb, .gltf, .blend, .fbx, .obj")

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    dest = ASSETS_DIR / file.filename
    async with aiofiles.open(dest, "wb") as out:
        content = await file.read()
        await out.write(content)

    return {"filename": file.filename}


# ---------------------------------------------------------------------------
# Render endpoint
# ---------------------------------------------------------------------------

_SAFE_NAME = re.compile(r'[^a-zA-Z0-9_-]')


class RenderRequest(BaseModel):
    sprite_size: int = 64
    mesh_path: str | None = None      # filename within assets/, or None for test primitive
    frame_start: int | None = None    # animation: first frame
    frame_end: int | None = None      # animation: last frame
    name: str = "sprite_sheet"        # output filename prefix (sanitized server-side)
    output_dir: str | None = None     # optional extra copy destination (e.g. game asset repo)
    merge_sheets: bool = False        # animation only: also produce a combined 8-row master sheet
    body_part: str = "full"           # "full" | "upper" | "lower" | "split"


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

    safe_name = _SAFE_NAME.sub('_', req.name).strip('_') or 'sprite_sheet'

    if req.output_dir:
        out_dir = Path(req.output_dir)
        if not out_dir.is_absolute():
            raise HTTPException(400, "output_dir must be an absolute path.")
        if not out_dir.is_dir():
            raise HTTPException(400, f"output_dir does not exist: {req.output_dir}")

    valid_body_parts = {"full", "upper", "lower", "split"}
    if req.body_part not in valid_body_parts:
        raise HTTPException(400, f"body_part must be one of {sorted(valid_body_parts)}.")

    job_id = str(uuid.uuid4())
    create_job(job_id)
    background_tasks.add_task(
        _run_render, job_id, req.sprite_size, req.mesh_path, req.frame_start, req.frame_end,
        safe_name, req.output_dir, req.merge_sheets, req.body_part
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
    name: str = "sprite_sheet",
    output_dir: str | None = None,
    merge_sheets: bool = False,
    body_part: str = "full",
) -> None:
    try:
        _run_render_inner(job_id, sprite_size, mesh_path, frame_start, frame_end, name, output_dir, merge_sheets, body_part)
    except Exception:
        tb = traceback.format_exc()
        print(f"[PixelForge Backend] UNHANDLED ERROR in _run_render:\n{tb}")
        update_job(job_id, status="error", step="error",
                   progress_msg="Internal pipeline error — see backend terminal.",
                   error=tb[-2000:])


def _build_blender_cmd(mesh_path, render_size, frame_start, frame_end, hide_collections=""):
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
    if frame_start is not None:
        cmd += ["--frame-start", str(frame_start), "--frame-end", str(frame_end)]
    if hide_collections:
        cmd += ["--hide-collections", hide_collections]
    return cmd


def _build_assemble_cmd(sprite_size, is_animation, name, merge_sheets=False):
    out_sheet = PROJECT_ROOT / "output" / f"{name}.png"
    if is_animation:
        OUTPUT_SHEETS.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(PYTHON_EXE), str(ASSEMBLE_SCRIPT),
            "--framesdir", str(OUTPUT_FRAMES),
            "--outdir",    str(OUTPUT_SHEETS),
            "--size",      str(sprite_size),
            "--animate",
            "--prefix",    name,
        ]
        if merge_sheets:
            cmd.append("--merge")
    else:
        cmd = [
            str(PYTHON_EXE), str(ASSEMBLE_SCRIPT),
            "--framesdir", str(OUTPUT_FRAMES),
            "--outfile",   str(out_sheet),
            "--size",      str(sprite_size),
        ]
    return cmd


def _run_render_inner(
    job_id: str,
    sprite_size: int,
    mesh_path: str | None,
    frame_start: int | None,
    frame_end: int | None,
    name: str = "sprite_sheet",
    output_dir: str | None = None,
    merge_sheets: bool = False,
    body_part: str = "full",
) -> None:
    render_size = sprite_size
    is_animation = (
        frame_start is not None
        and frame_end is not None
        and frame_end > frame_start
    )

    # Determine render passes: [(hide_collections, output_name_suffix), ...]
    if body_part == "split":
        passes = [("LowerBody", f"{name}_upper"), ("UpperBody", f"{name}_legs")]
    elif body_part == "upper":
        passes = [("LowerBody", name)]
    elif body_part == "lower":
        passes = [("UpperBody", name)]
    else:  # "full"
        passes = [("", name)]

    total_passes = len(passes)
    out_sheet = PROJECT_ROOT / "output" / f"{name}.png"

    LOG_FILE.write_text("", encoding="utf-8")  # clear log for this render
    if is_animation:
        _clear_dir(OUTPUT_SHEETS)

    for pass_idx, (hide_collections, pass_name) in enumerate(passes):
        pass_label = f" (pass {pass_idx + 1}/{total_passes})" if total_passes > 1 else ""
        pass_out_sheet = PROJECT_ROOT / "output" / f"{pass_name}.png"

        # Step 1: Blender
        if is_animation:
            num_frames = frame_end - frame_start + 1
            progress = f"Blender: {num_frames} frames × 8 dirs at {render_size}px{pass_label}..."
        else:
            progress = f"Blender: rendering 8 directions at {render_size}px{pass_label}..."
        update_job(job_id, status="running", step="blender", progress_msg=progress)

        _clear_dir(OUTPUT_FRAMES)
        OUTPUT_FRAMES.mkdir(parents=True, exist_ok=True)
        sentinel = OUTPUT_FRAMES / ".render_done"

        blender_cmd = _build_blender_cmd(mesh_path, render_size, frame_start, frame_end, hide_collections)
        returncode, output = _run_subprocess(blender_cmd, f"blender{pass_label}")

        blender_ok = sentinel.exists()
        if returncode != 0 or not blender_ok:
            error_msg = output.strip()[-2000:] or "Blender produced no output. Check the backend terminal."
            update_job(job_id, status="error", step="blender",
                       progress_msg="Blender render failed — see error details.",
                       error=error_msg)
            return

        # Step 2: Assemble
        update_job(job_id, step="assemble",
                   progress_msg=f"Assembling {sprite_size}px sheets{pass_label}...")
        assemble_cmd = _build_assemble_cmd(sprite_size, is_animation, pass_name, merge_sheets)
        returncode, output = _run_subprocess(assemble_cmd, f"assemble{pass_label}")
        if returncode != 0:
            error_msg = output.strip()[-2000:] or "Assembly script exited with an error. Check the backend terminal."
            update_job(job_id, status="error", step="assemble",
                       progress_msg="Sprite sheet assembly failed — see error details.",
                       error=error_msg)
            return

    # Copy final outputs to user-specified directory if requested
    if output_dir:
        dest = Path(output_dir)
        dest.mkdir(parents=True, exist_ok=True)
        if is_animation:
            for _, pass_name in passes:
                for f in OUTPUT_SHEETS.glob(f"{pass_name}_*.png"):
                    shutil.copy2(f, dest / f.name)
        else:
            for _, pass_name in passes:
                src = PROJECT_ROOT / "output" / f"{pass_name}.png"
                if src.exists():
                    shutil.copy2(src, dest / src.name)

    # Build result metadata
    final_pass_name = passes[-1][1]
    merged_url = f"/api/output/sheets/{final_pass_name}_all.png" if (is_animation and merge_sheets) else None

    update_job(job_id, status="done", step="done",
               progress_msg="Render complete.",
               output=f"sheets/{final_pass_name}" if is_animation else f"{final_pass_name}.png",
               merged_url=merged_url)


# ---------------------------------------------------------------------------
# Status endpoint (shared by render and mesh generation jobs)
# ---------------------------------------------------------------------------

@router.get("/status/{job_id}")
async def get_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, f"Job not found: {job_id}")
    return job
