"""
mesh.py — PixelForge Phase 3 routes.

Routes:
    POST /generate-mesh   Start Tripo3D mesh generation job (background)
    GET  /status/{id}     Shared with render.py (registered in main.py)
"""

import subprocess
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from pydantic import BaseModel

from backend.jobs import create_job, update_job

router = APIRouter()

PROJECT_ROOT   = Path(__file__).parent.parent.parent
PYTHON_EXE     = Path(r"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe")
TRIPO3D_SCRIPT = PROJECT_ROOT / "scripts" / "tripo3d.py"
ASSETS_DIR     = PROJECT_ROOT / "assets"


class MeshRequest(BaseModel):
    prompt:         str | None = None   # text-to-3D
    image_filename: str | None = None   # image already in assets/ (image-to-3D)
    outfile:        str = "generated.glb"
    timeout:        int = 300


@router.post("/generate-mesh")
async def generate_mesh(req: MeshRequest, background_tasks: BackgroundTasks):
    if not req.prompt and not req.image_filename:
        raise HTTPException(400, "Provide prompt (text-to-3D) or image_filename (image-to-3D).")
    if req.prompt and req.image_filename:
        raise HTTPException(400, "prompt and image_filename are mutually exclusive.")

    if req.image_filename:
        img_path = ASSETS_DIR / req.image_filename
        if not img_path.exists():
            raise HTTPException(404, f"Image not found in assets/: {req.image_filename}")

    job_id = str(uuid.uuid4())
    create_job(job_id)
    background_tasks.add_task(_run_tripo3d, job_id, req)
    return {"job_id": job_id}


def _run_tripo3d(job_id: str, req: MeshRequest) -> None:
    outfile = ASSETS_DIR / req.outfile
    mode = "text-to-3D" if req.prompt else "image-to-3D"
    src  = req.prompt or req.image_filename

    update_job(job_id, status="running", step="tripo3d",
               progress_msg=f"Generating mesh via Tripo3D ({mode}: {src})...")

    cmd = [
        str(PYTHON_EXE),
        str(TRIPO3D_SCRIPT),
        "--outfile", str(outfile),
        "--timeout", str(req.timeout),
    ]
    if req.prompt:
        cmd += ["--prompt", req.prompt]
    else:
        cmd += ["--image", str((ASSETS_DIR / req.image_filename).resolve())]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        update_job(job_id, status="error", step="tripo3d",
                   progress_msg="Mesh generation failed.",
                   error=result.stderr[-2000:] or result.stdout[-2000:])
        return

    update_job(job_id, status="done", step="done",
               progress_msg="Mesh generation complete.",
               output=req.outfile)
