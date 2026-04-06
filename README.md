# PixelForge

Generate 8-directional isometric sprite sheets from 3D meshes via Blender headless rendering.

## Quick Start

### 1. Install Pillow (once)
```
py -3.12 -m pip install Pillow
```

### 2. Run the pipeline
```
run_pipeline.bat
```

Output: `output/sprite_sheet.png` — a horizontal strip of 8 isometric views (N → NW).

### 3. Use a custom mesh
Edit `run_pipeline.bat` and uncomment:
```batch
SET MESH_ARG=--mesh "%~dp0assets\your_mesh.glb"
```
Or run directly:
```
python run_pipeline.py --mesh assets/your_mesh.glb
```

## Configuring Output Size
Edit `SPRITE_SIZE` in `run_pipeline.bat`:
```batch
SET SPRITE_SIZE=64   REM change to 16, 32, 64, 128, or 256
```
`RENDER_SIZE` is automatically 4× `SPRITE_SIZE` for clean downscaling.

## Output
- `output/frames/` — 8 individual PNGs (N.png, NE.png, E.png, SE.png, S.png, SW.png, W.png, NW.png)
- `output/sprite_sheet.png` — assembled horizontal strip

## Requirements
- Blender 5.1 at `C:\Program Files\Blender Foundation\Blender 4.x\blender.exe`
- Python 3.12 with Pillow installed
