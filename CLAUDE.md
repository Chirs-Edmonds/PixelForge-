# PixelForge

## Project Purpose
Local pipeline tool that generates 8-directional isometric sprite sheets from 3D meshes
using Blender headless rendering. Target output: configurable pixel art sprites (default 64×64),
8 directions (N/NE/E/SE/S/SW/W/NW), assembled into a single horizontal PNG sprite sheet.

## Tech Stack
- **Blender:** `C:\Program Files\Blender Foundation\Blender 4.x\blender.exe`
  - Folder says "4.x" but binary is Blender 5.1.0
  - Embedded Python: 3.13.9 (has numpy, does NOT have Pillow)
  - EEVEE engine ID in 5.x: `'BLENDER_EEVEE_NEXT'`
- **System Python:** `C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe` (3.12.9)
- **Node:** 24.14.0 / npm 11.9.0

## Running the Tool

### CLI (all phases)
```
python run_pipeline.py [--mesh path.glb] [--sprite-size 64]
                       [--upscale] [--colors 16] [--dither]
                       [--generate-mesh --tripo-prompt "fantasy sword"]
```

### Web UI (Phases 1–4)
```
# Terminal 1 — backend (from project root)
py -3.12 -m uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
# Open http://localhost:3000
```

## Pipeline Flow
```
[Phase 3: tripo3d.py]     → assets/generated.glb     (opt-in: --generate-mesh)
[Phase 1: blender_bake.py]→ output/frames/N–NW.png   (always)
         assemble_sheet.py→ output/sprite_sheet.png   (always)
[Phase 2: refine.py]      → output/sprite_sheet_refined.png (opt-in: --upscale / --colors)
```

## Project Structure
```
scripts/
  blender_bake.py       Blender-internal renderer (8 directions)
  assemble_sheet.py     Pillow sprite sheet assembler
  refine.py             Real-ESRGAN + palette quantization
  tripo3d.py            Tripo3D API: text/image → .glb
backend/
  main.py               FastAPI app (port 8000)
  jobs.py               In-memory job state store
  routes/render.py      POST /render, POST /upload-mesh, GET /status/{id}
  routes/refine.py      POST /refine
  routes/mesh.py        POST /generate-mesh
frontend/
  src/App.jsx           Main app state machine
  src/components/       MeshInput, RenderSettings, StatusBar, RefinementPanel, SpriteSheetOutput
  src/hooks/            useJobStatus (2s polling hook)
tools/
  realesrgan-ncnn-vulkan/   Manual download required (see Phase 2 setup)
```

## Key Conventions
- **Render resolution:** 4× target sprite size (default 256px → 64px output)
- **Camera:** orthographic, 35.264° elevation (true isometric), 6 Blender units distance
- **Engine:** BLENDER_EEVEE_NEXT (Blender 5.x)
- **Background:** transparent RGBA PNG
- **Direction order in sheet:** N, NE, E, SE, S, SW, W, NW (left to right)
- **North convention:** Blender +Y = North
- **Downscale:** LANCZOS for clean pixel art edges
- **Frontend proxy:** all React fetch calls use `/api/*` → proxied to FastAPI port 8000
- **Job polling:** GET /status/{job_id} every 2s until status == "done" | "error"

## Configurable Sizes
- 16×16 — micro sprites
- 32×32 — classic RPG / Godot isometric tiles
- **64×64 — default**
- 128×128 — high-res pixel art
- 256×256 — source quality, downscale in engine

## Phase 2 Setup (Real-ESRGAN)
Download `realesrgan-ncnn-vulkan-*-windows.zip` from:
  https://github.com/xinntao/Real-ESRGAN/releases
Extract to `tools/realesrgan-ncnn-vulkan/`
The binary must run from its own directory so it finds `models/`.

## Phase 3 Setup (Tripo3D)
Edit `.env` at project root and set: `TRIPO3D_API_KEY=your_actual_key`

## Phase Roadmap (all complete)
- **Phase 1:** Blender headless baking pipeline ✓
- **Phase 2:** Real-ESRGAN pixel art upscale + palette quantisation ✓
- **Phase 3:** Tripo3D API: image/prompt → .glb ✓
- **Phase 4:** FastAPI backend + React/Vite frontend ✓
