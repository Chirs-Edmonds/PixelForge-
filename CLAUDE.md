# PixelForge

## Project Purpose
Local pipeline tool that generates 8-directional isometric sprite sheets from 3D meshes
using Blender headless rendering. Target output: configurable pixel art sprites (default 64×64),
8 directions (N/NE/E/SE/S/SW/W/NW), assembled into a single horizontal PNG sprite sheet.
Also supports full animation rendering: 8 sprite sheets (one per direction), each strip being
num_frames wide.

## Tech Stack
- **Blender:** `C:\Program Files\Blender Foundation\Blender 4.x\blender.exe`
  - Folder says "4.x" but binary is Blender 5.1.0
  - Embedded Python: 3.13.9 (has numpy, does NOT have Pillow)
  - EEVEE engine ID in 5.x: `'BLENDER_EEVEE_NEXT'`
- **System Python:** `C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe` (3.12.9)
- **Node:** 24.14.0 / npm 11.9.0

## Running the Tool

### Web UI — ONE-CLICK LAUNCH (preferred)
Double-click `start.bat` in the project root.
- Kills any old uvicorn/vite processes first (prevents port conflicts)
- Opens backend on port 8000, frontend on port 3000
- Opens browser automatically to http://localhost:3000
- To stop: double-click `stop.bat`, or just close both CMD windows

### Web UI — Manual (if start.bat has issues)
```
# Kill any existing python uvicorn process first (Task Manager → Details → python.exe → End Process Tree)

# Terminal 1 — backend (from project root)
"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn backend.main:app --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
# Open http://localhost:3000
```
NOTE: Do NOT use --reload flag. It restarts the backend mid-render whenever any file is saved,
killing in-progress jobs and losing their state.

### CLI (all phases)
```
"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe" run_pipeline.py [--mesh path.glb] [--sprite-size 64]
                       [--upscale] [--colors 16] [--dither]
                       [--generate-mesh --tripo-prompt "fantasy sword"]
                       [--frame-start 1 --frame-end 36]
```

## Pipeline Flow
```
[Phase 3: tripo3d.py]     → assets/generated.glb           (opt-in: --generate-mesh)
[Phase 1: blender_bake.py]→ output/frames/N–NW.png         (single-frame mode)
                          → output/frames/N/0001.png ...    (animation mode)
         assemble_sheet.py→ output/sprite_sheet.png         (single-frame mode)
                          → output/sheets/sprite_sheet_N.png ... (animation mode, 8 files)
[Phase 2: refine.py]      → output/sprite_sheet_refined.png (opt-in, single-frame only)
```

## Animation Mode
- CLI: add `--frame-start 1 --frame-end 36` (both required together)
- Web UI: switch Output Mode to "Animation", set frame range, click "Render Animation"
- Blender renders outer loop = directions (camera moved 8×), inner loop = frames (efficient)
- Output: 8 sprite sheets in `output/sheets/sprite_sheet_{N,NE,E,SE,S,SW,W,NW}.png`
- Each sheet is `num_frames × sprite_size` wide, `sprite_size` tall
- Phase 2 refinement is skipped in animation mode (by design)
- Sentinel file: `output/frames/.render_done` written by blender_bake.py only on full success.
  Backend checks this file to detect Blender failures (Blender exits 0 even on Python errors).

## Project Structure
```
start.bat               One-click launcher (kills old servers, starts both, opens browser)
stop.bat                One-click stop (kills both server windows)
run_pipeline.py         CLI orchestrator (all phases)
scripts/
  blender_bake.py       Blender-internal renderer (8 directions, single + animation)
  assemble_sheet.py     Pillow sprite sheet assembler (single + animation modes)
  refine.py             Real-ESRGAN + palette quantization
  tripo3d.py            Tripo3D API: text/image → .glb
backend/
  main.py               FastAPI app (port 8000), mounts /output and /assets as static
  jobs.py               In-memory job state store (lost on server restart)
  routes/render.py      POST /render, POST /upload-mesh, GET /status/{id}
  routes/refine.py      POST /refine
  routes/mesh.py        POST /generate-mesh
frontend/
  src/App.jsx           Main app state machine (animConfig, animConfigRef, renderJobId)
  src/components/       MeshInput, RenderSettings, StatusBar, RefinementPanel, SpriteSheetOutput
  src/hooks/            useJobStatus (2s polling, clears on jobId change)
tools/
  realesrgan-ncnn-vulkan/   Manual download required (see Phase 2 setup)
output/
  frames/               Blender raw PNG output (flat for single-frame, subdirs for animation)
  sheets/               Animation sprite sheets (sprite_sheet_N.png … sprite_sheet_NW.png)
  sprite_sheet.png      Single-frame sprite sheet
  last_render.log       Full stdout/stderr from last Blender + assemble run
assets/                 Uploaded .glb files
```

## Key Conventions
- **Render resolution:** equals target sprite size (e.g. 64px render → 64px sprite cells; no 4× multiplier)
- **Camera:** orthographic, 35.264° elevation (true isometric), 6 Blender units distance
- **Engine:** BLENDER_EEVEE_NEXT (Blender 5.x)
- **Background:** transparent RGBA PNG
- **Direction order in sheet:** N, NE, E, SE, S, SW, W, NW (left to right)
- **North convention:** Blender +Y = North
- **Downscale:** LANCZOS for clean pixel art edges
- **Frontend proxy:** all React fetch calls use `/api/*` → proxied to FastAPI port 8000
  (rewrite strips /api prefix: `/api/render` → `/render`, `/api/output/...` → `/output/...`)
- **Job polling:** GET /status/{job_id} every 2s until status == "done" | "error"
- **Job store:** in-memory dict in jobs.py — wiped on every server restart
- **CORS:** allowed origin is http://localhost:3000 only

## Configurable Sizes
- 16×16 — micro sprites
- 32×32 — classic RPG / Godot isometric tiles
- **64×64 — default**
- 128×128 — high-res pixel art
- 256×256 — source quality, downscale in engine

## Known Issues / Next Work
- **Animation preview frame width (frontend bug):** SpriteSheetOutput.jsx hardcodes 192px
  per frame in the `translateX` calculation. Works only for 64px sprites at 192px display
  height. Breaks for other sprite sizes. Fix: derive frameDisplayWidth from spriteSize prop.
- **Sentinel not written if Blender crashes mid-animation:** blender_bake.py has no try/except
  around the per-frame render loop. If Blender crashes partway through, partial frames exist
  in output/frames/ but no sentinel is written → backend reports "Blender render failed."
  Fix: add try/except around render loop in blender_bake.py with explicit error logging.
- **Path traversal in mesh_path:** render.py doesn't verify mesh_path stays within assets/.
  Fix: check `mesh_abs.resolve().is_relative_to(ASSETS_DIR.resolve())`.
- **No file upload validation:** upload endpoint only checks .glb extension, no magic bytes,
  no size limit.
- **/refine runs synchronously:** blocks the HTTP request for the full upscale duration.
  Fix: move to BackgroundTasks like /render.
- **Unused import:** `import tempfile` in render.py line 11.

## Phase 2 Setup (Real-ESRGAN)
Download `realesrgan-ncnn-vulkan-*-windows.zip` from:
  https://github.com/xinntao/Real-ESRGAN/releases
Extract to `tools/realesrgan-ncnn-vulkan/`
The binary must run from its own directory so it finds `models/`.

## Phase 3 Setup (Tripo3D)
Edit `.env` at project root and set: `TRIPO3D_API_KEY=your_actual_key`

## Phase Roadmap
- **Phase 1:** Blender headless baking pipeline ✓
- **Phase 2:** Real-ESRGAN pixel art upscale + palette quantisation ✓
- **Phase 3:** Tripo3D API: image/prompt → .glb ✓
- **Phase 4:** FastAPI backend + React/Vite frontend ✓
- **Phase 5:** Animation rendering + 8-direction sprite sheet strips ✓
- **Phase 6:** One-click launcher (start.bat / stop.bat) ✓
