"""
render.py — PixelForge Phase 1 routes.

Routes:
    POST /upload-mesh   Upload a .glb file to assets/
    POST /render        Start a Blender render job (background)
    GET  /status/{id}   Poll job status
"""

import asyncio
import json
import re
import shutil
import subprocess
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
BLEND_INFO_SCRIPT = PROJECT_ROOT / "scripts" / "blend_info.py"
ASSEMBLE_SCRIPT = PROJECT_ROOT / "scripts" / "assemble_sheet.py"
OUTPUT_FRAMES   = PROJECT_ROOT / "output" / "frames"
OUTPUT_SHEETS   = PROJECT_ROOT / "output" / "sheets"
OUTPUT_MERGED   = PROJECT_ROOT / "output" / "merged"
OUTPUT_REFINED  = PROJECT_ROOT / "output" / "refined"
ASSETS_DIR      = PROJECT_ROOT / "assets"
PREVIEW_SCRIPT  = PROJECT_ROOT / "scripts" / "blender_preview.py"
OUTPUT_PREVIEW  = PROJECT_ROOT / "output" / "preview"

VALID_SIZES = {16, 32, 64, 128, 256}


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------

_ALLOWED_MESH_EXTENSIONS = (".glb", ".gltf", ".blend", ".fbx", ".obj")

MAX_UPLOAD_BYTES = 250 * 1024 * 1024   # 250 MB — rigged .blend files with long actions get big


def _asset_path(filename: str) -> Path:
    """Resolve a caller-supplied filename to a path inside assets/, or reject it.

    Filenames arrive from request bodies and query strings, so the resolved path
    must be confined to ASSETS_DIR — otherwise "../../etc/passwd" style values
    would let a request read or render arbitrary files on disk.
    """
    safe_name = Path(filename).name
    if not safe_name or safe_name in {".", ".."}:
        raise HTTPException(400, "Invalid filename.")

    path = ASSETS_DIR / safe_name
    if not path.resolve().is_relative_to(ASSETS_DIR.resolve()):
        raise HTTPException(400, "Invalid filename.")
    return path


def _looks_like_mesh(ext: str, head: bytes) -> bool:
    """Sniff the leading bytes of an upload to confirm they match the extension.

    Binary formats carry a fixed signature. The text formats (.gltf, .obj, and
    ASCII .fbx) have none, so they are checked for a plausible opening token
    instead — enough to reject a renamed executable or archive.
    """
    if ext == ".glb":
        return head[:4] == b"glTF"

    if ext == ".blend":
        # Uncompressed .blend opens with "BLENDER". Blender 3.0+ writes zstd by
        # default and older builds used gzip, so accept those container magics too.
        return (head[:7] == b"BLENDER"
                or head[:4] == b"\x28\xb5\x2f\xfd"      # zstd
                or head[:2] == b"\x1f\x8b")             # gzip

    if ext == ".fbx":
        if head[:20] == b"Kaydara FBX Binary  ":
            return True
        # ASCII FBX: a comment banner, or the FBXHeaderExtension node near the top.
        return head.lstrip()[:1] == b";" or b"FBXHeaderExtension" in head[:2048]

    text = head.lstrip(b"\xef\xbb\xbf").lstrip()

    if ext == ".gltf":
        return text[:1] == b"{"

    if ext == ".obj":
        if b"\x00" in head:
            return False        # NUL bytes mean this is not a text file
        first_line = text.split(b"\n", 1)[0].strip().lower()
        return first_line.startswith(
            (b"#", b"v ", b"vn ", b"vt ", b"o ", b"g ", b"s ", b"f ", b"mtllib", b"usemtl")
        )

    return False


@router.post("/upload-mesh")
async def upload_mesh(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(_ALLOWED_MESH_EXTENSIONS):
        raise HTTPException(400, "Supported formats: .glb, .gltf, .blend, .fbx, .obj")

    dest = _asset_path(file.filename)
    safe_filename = dest.name
    ext = dest.suffix.lower()

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # Stream to a sidecar file first: a rejected upload must never truncate or
    # replace a good mesh that already carries the same name.
    partial = dest.with_name(dest.name + ".part")
    written = 0
    header_checked = False

    try:
        async with aiofiles.open(partial, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)  # 1 MB chunks — avoids OOM on large meshes
                if not chunk:
                    break

                if not header_checked:
                    if not _looks_like_mesh(ext, chunk):
                        raise HTTPException(400, f"File contents do not look like a valid {ext} mesh.")
                    header_checked = True

                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        413,
                        f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit."
                    )
                await out.write(chunk)
    except HTTPException:
        partial.unlink(missing_ok=True)
        raise
    except OSError as e:
        partial.unlink(missing_ok=True)
        raise HTTPException(500, f"Failed to save file: {e}")

    if written == 0:
        partial.unlink(missing_ok=True)
        raise HTTPException(400, "Uploaded file is empty.")

    try:
        partial.replace(dest)
    except OSError as e:
        partial.unlink(missing_ok=True)
        raise HTTPException(500, f"Failed to save file: {e}")

    # Invalidate all cached preview GLBs for this file (all action/body_part combos)
    stem = Path(safe_filename).stem
    OUTPUT_PREVIEW.mkdir(parents=True, exist_ok=True)
    for cached in OUTPUT_PREVIEW.glob(f"{stem}_*_preview.glb"):
        try:
            cached.unlink()
        except OSError:
            pass

    return {"filename": safe_filename}


# ---------------------------------------------------------------------------
# Blend-info endpoint — returns actions list for .blend files
# ---------------------------------------------------------------------------

@router.get("/blend-info")
async def get_blend_info(filename: str):
    """Return action names + frame ranges from a .blend file in assets/."""
    if not filename.lower().endswith(".blend"):
        return {"actions": []}

    filepath = _asset_path(filename)
    if not filepath.exists():
        raise HTTPException(404, f"File not found in assets/: {filepath.name}")

    cmd = [
        str(BLENDER_EXE),
        "--background", "--factory-startup",
        "--python", str(BLEND_INFO_SCRIPT),
        "--", "--mesh", str(filepath.resolve()),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
    except asyncio.TimeoutError:
        proc.kill()
        raise HTTPException(500, "Blender timed out reading blend file info.")

    output = stdout.decode("utf-8", errors="replace") + stderr.decode("utf-8", errors="replace")
    for line in output.splitlines():
        if line.startswith("BLEND_INFO_JSON:"):
            return json.loads(line[len("BLEND_INFO_JSON:"):])

    return {"actions": []}


# body_part → collections to hide before GLB export (mirrors blender_bake.py split logic)
_BODY_PART_HIDE: dict[str, str] = {
    "full":  "",
    "upper": "LowerBody",
    "lower": "UpperBody",
    "split": "",   # show everything for split preview
}

# ---------------------------------------------------------------------------
# Preview-mesh endpoint — converts any supported format to GLB for browser preview
# ---------------------------------------------------------------------------

@router.get("/preview-mesh")
async def preview_mesh(
    filename: str,
    action_name: str = "",
    body_part: str = "full",
):
    """
    Return a URL to a self-contained GLB file for browser-side 3D preview.

    - .glb: served directly from /assets/ (no Blender needed)
    - .gltf / .blend / .fbx / .obj: converted via Blender, cached at output/preview/

    action_name  — pose model at frame 1 of this action (empty = rest pose)
    body_part    — "full"|"upper"|"lower"|"split"; hides the opposite collection
    """
    if not filename:
        raise HTTPException(400, "filename query parameter is required.")

    ext = Path(filename).suffix.lower()
    if ext not in {".glb", ".gltf", ".blend", ".fbx", ".obj"}:
        raise HTTPException(400, f"Unsupported format: {ext}")

    src_path = _asset_path(filename)
    safe_name = src_path.name
    if not src_path.exists():
        raise HTTPException(404, f"File not found in assets/: {safe_name}")

    # GLB is self-contained — serve directly (no Blender conversion)
    if ext == ".glb":
        return {"url": f"/assets/{safe_name}"}

    # Cache key includes action and body_part so each combination is stored separately
    stem = Path(safe_name).stem
    action_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', action_name) if action_name else "default"
    body_safe   = body_part if body_part in _BODY_PART_HIDE else "full"
    glb_filename = f"{stem}_{action_safe}_{body_safe}_preview.glb"
    glb_path = OUTPUT_PREVIEW / glb_filename
    OUTPUT_PREVIEW.mkdir(parents=True, exist_ok=True)

    if not glb_path.exists():
        hide_col = _BODY_PART_HIDE.get(body_safe, "")
        cmd = [
            str(BLENDER_EXE),
            "--background", "--factory-startup",
            "--python", str(PREVIEW_SCRIPT),
            "--", str(src_path.resolve()), str(glb_path.resolve()),
        ]
        if action_name:
            cmd += ["--action", action_name]
        if hide_col:
            cmd += ["--hide-collections", hide_col]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        except asyncio.TimeoutError:
            proc.kill()
            raise HTTPException(500, "Blender preview conversion timed out (>120s).")

        combined = (stdout.decode("utf-8", errors="replace") +
                    stderr.decode("utf-8", errors="replace"))
        if proc.returncode != 0 or not glb_path.exists():
            raise HTTPException(
                500,
                f"Blender preview conversion failed (exit {proc.returncode}).\n\n"
                + combined[-3000:],
            )

    return {"url": f"/output/preview/{glb_filename}"}


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
    action_name: str | None = None    # .blend only: name of action to render
    supersample: int = 1              # 1 | 2 | 4 — Blender renders at sprite_size × supersample
    ortho_scale: float = 0.0          # 0 = auto-fit bbox; >0 LOCKS camera frame width (consistent scale across sheets)


@router.post("/render")
async def start_render(req: RenderRequest, background_tasks: BackgroundTasks):
    if req.sprite_size not in VALID_SIZES:
        raise HTTPException(400, f"sprite_size must be one of {sorted(VALID_SIZES)}.")
    if req.supersample not in (1, 2, 4):
        raise HTTPException(400, "supersample must be 1, 2, or 4.")
    if req.ortho_scale < 0.0:
        raise HTTPException(400, "ortho_scale must be >= 0 (0 = auto-fit).")

    # Confine the mesh to assets/ and pass the sanitized basename downstream —
    # _build_blender_cmd joins it onto ASSETS_DIR again.
    safe_mesh_path = None
    if req.mesh_path:
        mesh_abs = _asset_path(req.mesh_path)
        if not mesh_abs.exists():
            raise HTTPException(404, f"Mesh not found in assets/: {mesh_abs.name}")
        safe_mesh_path = mesh_abs.name

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
        _run_render, job_id, req.sprite_size, safe_mesh_path, req.frame_start, req.frame_end,
        safe_name, req.output_dir, req.merge_sheets, req.body_part, req.action_name, req.supersample,
        req.ortho_scale,
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
    action_name: str | None = None,
    supersample: int = 1,
    ortho_scale: float = 0.0,
) -> None:
    try:
        _run_render_inner(job_id, sprite_size, mesh_path, frame_start, frame_end, name, output_dir, merge_sheets, body_part, action_name, supersample, ortho_scale)
    except Exception:
        tb = traceback.format_exc()
        print(f"[PixelForge Backend] UNHANDLED ERROR in _run_render:\n{tb}")
        update_job(job_id, status="error", step="error",
                   progress_msg="Internal pipeline error — see backend terminal.",
                   error=tb[-2000:])


def _build_blender_cmd(mesh_path, render_size, frame_start, frame_end, hide_collections="", action_name=None, ortho_scale=0.0):
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
    if action_name:
        cmd += ["--action", action_name]
    if ortho_scale and ortho_scale > 0.0:
        cmd += ["--ortho-scale", str(ortho_scale)]
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
            OUTPUT_MERGED.mkdir(parents=True, exist_ok=True)
            cmd += ["--merge", "--mergeddir", str(OUTPUT_MERGED)]
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
    action_name: str | None = None,
    supersample: int = 1,
    ortho_scale: float = 0.0,
) -> None:
    render_size = sprite_size * supersample
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
        _clear_dir(OUTPUT_MERGED)
        _clear_dir(OUTPUT_REFINED)  # stale refined files don't match new render

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

        blender_cmd = _build_blender_cmd(mesh_path, render_size, frame_start, frame_end, hide_collections, action_name, ortho_scale)
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
            if merge_sheets:
                for _, pass_name in passes:
                    merged_file = OUTPUT_MERGED / f"{pass_name}_all.png"
                    if merged_file.exists():
                        shutil.copy2(merged_file, dest / merged_file.name)
        else:
            for _, pass_name in passes:
                src = PROJECT_ROOT / "output" / f"{pass_name}.png"
                if src.exists():
                    shutil.copy2(src, dest / src.name)

    # Build result metadata
    final_pass_name = passes[-1][1]
    # Split renders have two merged sheets (upper + legs); the frontend constructs both URLs
    # from safeBase itself, so we only return merged_url for single-pass animation renders.
    merged_url = (
        f"/api/output/merged/{final_pass_name}_all.png"
        if (is_animation and merge_sheets and len(passes) == 1)
        else None
    )

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
