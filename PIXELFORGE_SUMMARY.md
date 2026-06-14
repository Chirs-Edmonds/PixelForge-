# PixelForge — Project Summary

## What It Is

PixelForge is a **local pipeline tool** that converts 3D meshes into 8-directional isometric pixel art sprite sheets using Blender's headless renderer. Given a `.glb`, `.blend`, `.fbx`, `.obj`, or `.gltf` file, it renders the mesh from 8 equidistant azimuth angles at a true isometric camera elevation (35.264°), assembles the results into a horizontal sprite strip, and optionally post-processes the output with palette quantization, dithering, outline injection, and super-sampling. It also supports full animation rendering (frame ranges → 8 per-direction sprite sheets) and 3D mesh generation via the Tripo3D API.

---

## Tech Stack

| Component | Detail |
|-----------|--------|
| **Blender** | 5.1.0 at `C:\Program Files\Blender Foundation\Blender 4.x\blender.exe` (folder name is misleading) |
| **Blender engine** | `BLENDER_EEVEE_NEXT` (Blender 5.x ID) |
| **Blender Python** | 3.13.9 — has numpy, does NOT have Pillow |
| **System Python** | 3.12.9 at `C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe` |
| **Node / npm** | 24.14.0 / 11.9.0 |
| **Backend** | FastAPI + uvicorn on port 8000 |
| **Frontend** | React 18 + Vite on port 3000 |
| **Image processing** | Pillow (system Python only) |
| **Upscaling** | Real-ESRGAN ncnn-vulkan (`tools/realesrgan-ncnn-vulkan/`, manual download required) |
| **Mesh generation** | Tripo3D API (key in `.env` at project root) |

---

## Project Structure

```
start.bat / stop.bat        One-click launchers (kill old processes, start both servers, open browser)
run_pipeline.py             CLI orchestrator (all phases)
scripts/
  blender_bake.py           Blender-internal renderer (8 directions × frames)
  assemble_sheet.py         Pillow sheet assembler
  refine.py                 Post-processing: upscale, quantize, dither, outline
  tripo3d.py                Tripo3D API: text/image → .glb
backend/
  main.py                   FastAPI app; mounts /output and /assets as static
  jobs.py                   In-memory job store (wiped on restart)
  routes/render.py          POST /render, POST /upload-mesh, GET /status/{id}
  routes/refine.py          POST /refine
  routes/mesh.py            POST /generate-mesh
frontend/
  src/App.jsx               Root state machine (animConfig, animConfigRef, renderJobId)
  src/components/
    TopBar.jsx              Logo + render-state indicator + frame count chip
    Sidebar.jsx             56px icon nav (Forge / Library / Queue / Output / Settings)
    MeshInput.jsx           Upload tab + Tripo3D generate tab
    RenderSettings.jsx      All render controls + Render button
    RefinementPanel.jsx     Post-process controls + Refine button
    SpriteSheetOutput.jsx   Tabbed preview (Live Preview / 8-Dir / Master Sheet / Compare)
    StatusBar.jsx           Animated job-status dot + progress message
  src/hooks/
    useJobStatus.js         GET /status/{id} every 2s until done/error
output/
  frames/                   Raw Blender PNGs (flat for single-frame, subdirs for animation)
  sheets/                   Animation sprite sheets (sprite_sheet_{N,NE,E,SE,S,SW,W,NW}.png)
  sprite_sheet.png          Single-frame output
  last_render.log           Full stdout/stderr from last Blender + assemble run
assets/                     Uploaded mesh files
```

---

## Pipeline Architecture

```
[Phase 3 — optional]  tripo3d.py         text/image prompt → assets/generated.glb
                                                    ↓
[Phase 1 — required]  blender_bake.py    mesh → output/frames/{dir}.png  (single-frame)
                                              → output/frames/{dir}/xxxx.png (animation)
                      assemble_sheet.py  frames → output/sprite_sheet.png  (single)
                                              → output/sheets/sprite_sheet_{dir}.png (animation)
                                              → output/merged/{name}_all.png (merged, optional)
                                                    ↓
[Phase 2 — optional]  refine.py          sprite sheet → output/sprite_sheet_refined.png
                                         (skipped in animation mode unless merged)
```

**Sentinel file:** `output/frames/.render_done` is written by `blender_bake.py` only on full success. The backend checks this file to detect Blender failures (Blender exits 0 even on internal Python errors).

**Frontend proxy:** All React fetch calls use `/api/*` → Vite proxies to FastAPI port 8000, stripping the `/api` prefix (e.g., `/api/render` → `/render`).

---

## Render Settings (Phase 1)

| Setting | Options | Default |
|---------|---------|---------|
| Sprite size | 16, 32, 64, 128, 256 px | 64 |
| Super-sampling | Off / 2× / 4× | Off |
| Output mode | Single Frame / Animation | Single Frame |
| Frame range | frame_start – frame_end | — |
| Body part | Full / Upper / Lower / Split | Full |
| Action selector | Dropdown (`.blend` NLA actions only) | first action |
| Output name | Free text, max 40 chars | `sprite_sheet` |
| Output folder | Path copied to after render | — |
| Merge sheets | Boolean (animation only) | false |

**Body part / Split mode:** requires the `.blend` file to have `UpperBody` and `LowerBody` collections with geometry. Split mode runs two full render passes and produces separate upper/lower sprite sheets.

**Camera:** orthographic, 35.264° elevation, 6 Blender units orbit radius. North (N) = camera at +Y looking south. Directions in sheet order: N, NE, E, SE, S, SW, W, NW.

**Render resolution:** equals target sprite size (e.g., 64px render → 64px sprite cells). Super-sampling renders at size × N then LANCZOS-downscales to target.

---

## Refinement Settings (Phase 2)

| Setting | Options | Notes |
|---------|---------|-------|
| Pixel art upscale | On / Off | NN×4 upscale → LANCZOS downscale back to original size |
| Alpha cutoff | 1–64 | Lower = keep thin edges; higher = clean transparency |
| Posterize | Off / 4 col / 8 col / 16 col | Hard color banding |
| Palette colors | Off / 8 / 16 / 32 / 64 | Palette quantization |
| Dithering | None / Floyd-Steinberg / Bayer | Only visible when colors > 0 |
| Pixel outline | On / Off + color picker | 1px border injection |

Animation refinement requires **Merge sheets** to be enabled (can't refine 8 separate strips individually via the UI).

---

## Web UI Layout

### TopBar
Fixed 48px header. Shows PF logo, "PixelForge" label, "8-dir generator" chip, a frame-count stats chip (e.g., "24 fr × 8 dir" when animation), and a pulsing status dot (Idle / Rendering / Done / Error).

### Sidebar
Fixed 56px icon-only nav on the left. Views: Forge (main workspace), Library, Queue, Output, Settings. Active view highlighted with accent bar.

### MeshInput
Two tabs: **Upload Mesh** (drag-and-drop zone accepting .glb/.gltf/.blend/.fbx/.obj, or "Use test primitive" to render with default cube) and **Generate (Tripo3D)** (text prompt → Tripo3D API → .glb).

### RenderSettings
All render controls (see Render Settings table above) plus:
- Preset quick-select buttons (RPG 32, Mobile 64, HD 128, Src 256)
- Action dropdown (auto-populates frame range for `.blend` NLA actions)
- Render button with contextual label ("Render Sprite Sheet" / "Render Animation")

### StatusBar
Animated pulse dot + progress text. Polls `GET /status/{job_id}` every 2s. Fires `onDone` / `onError` callbacks to parent.

### RefinementPanel
All post-process controls (see Refinement Settings table). Refine button label is context-aware ("Refine split sheets", "Refine all sheets", etc.). Warns if animation + no merge.

### SpriteSheetOutput
Tabbed output viewer:
- **Live Preview** (animation only): direction wheel (3×3 grid), 192×192px preview box, play/pause + FPS slider (1–24), full strip view below
- **8-Dir**: full sprite strip with direction labels (single-frame) or 8 thumbnail grid (animation)
- **Master Sheet**: full merged sheet view (when merge enabled)
- **Compare**: side-by-side refined vs original

Split mode wraps two SpriteSheetOutput instances (Upper / Lower tabs).

---

## Running the Project

### One-click (recommended)
Double-click `start.bat` from the project root. Kills old uvicorn/vite processes, starts both servers, opens `http://localhost:3000`.

To stop: double-click `stop.bat`.

### Manual
```powershell
# Terminal 1 — backend (no --reload; it kills in-progress renders)
"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn backend.main:app --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
# Open http://localhost:3000
```

### CLI
```powershell
"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe" run_pipeline.py `
  [--mesh path.glb] [--sprite-size 64] `
  [--upscale] [--colors 16] [--dither] `
  [--generate-mesh --tripo-prompt "fantasy sword"] `
  [--frame-start 1 --frame-end 36]
```

---

## Current Branch / In-Progress Work

**Branch:** `feature/v0.2-ui-redesign`

**Status:** v0.2 UI redesign in progress (not yet merged to main). Changes so far:
- New CSS design system: CSS custom properties (`--pf-accent` = `#8b5cf6`, `--pf-bg`, `--pf-panel`, `--pf-border`, `--pf-text`, `--pf-muted`, `--pf-err`, `--pf-good`, etc.)
- Typography: Geist (body) + VT323 (monospace/pixel aesthetic) from Google Fonts
- 3-pane layout: TopBar + Sidebar + main content area
- New `TopBar.jsx` and `Sidebar.jsx` components
- Tabbed preview panel in `SpriteSheetOutput.jsx` (Live Preview / 8-Dir / Master Sheet / Compare)
- Direction wheel in animation Live Preview tab

**What's merged to main (last stable):**
- Phase 1–6 all complete (Blender bake, refinement, Tripo3D, FastAPI, animation, launcher)
- Pixel art quality suite: alpha slider, outline injection, super-sampling, Bayer dithering, posterization
- Split-body render pipeline (UpperBody/LowerBody collections)
- `.blend` action selection via blend-info endpoint
- One-click `start.bat` / `stop.bat`

---

## Known Issues

| Issue | Location | Severity |
|-------|----------|----------|
| Animation preview `translateX` hardcodes 192px per frame — only works for 64px sprites | `SpriteSheetOutput.jsx` | Medium |
| Sentinel `.render_done` not written if Blender crashes mid-animation (no try/except around render loop) | `scripts/blender_bake.py` | Medium |
| Path traversal: `mesh_path` not verified to stay within `assets/` | `backend/routes/render.py` | Security |
| File upload: only checks `.glb` extension, no magic bytes, no size limit | `backend/routes/render.py` | Security |
| `/refine` runs synchronously, blocks HTTP request for full upscale duration | `backend/routes/refine.py` | Low |
| `import tempfile` unused | `backend/routes/render.py:11` | Trivial |

---

## Key Conventions

- **Background:** transparent RGBA PNG
- **Downscaling:** LANCZOS for clean pixel art edges
- **Job store:** in-memory dict in `backend/jobs.py` — wiped on every server restart
- **CORS:** `http://localhost:3000` only
- **North:** camera at +Y (north of object), looking south; azimuth 0° = +Y orbit position
- **Direction sheet order:** N, NE, E, SE, S, SW, W, NW (left to right)
- **Do NOT use `--reload`** with uvicorn — it kills in-progress render jobs when any file is saved
