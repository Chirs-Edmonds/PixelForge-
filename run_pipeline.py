"""
run_pipeline.py — PixelForge full pipeline runner (Phases 1–4)

Usage:
    python run_pipeline.py [options]

Phase 1 — Render (always runs):
    --mesh         PATH   .glb file to render. Omit for built-in test primitive.
    --sprite-size  INT    Final sprite size in pixels (square). Default: 64.
    --render-size  INT    Blender internal resolution. Default: sprite-size * 4.

Phase 2 — Refinement (opt-in, runs after Phase 1):
    --upscale             Run Real-ESRGAN x4 pixel art upscale.
    --colors       INT    Quantize palette to N colors (0 = skip). Default: 0.
                          Useful values: 8, 16, 32, 64.
    --dither              Floyd-Steinberg dithering during quantize.

Phase 3 — Mesh generation via Tripo3D (opt-in, runs before Phase 1):
    --generate-mesh       Generate a mesh via Tripo3D before rendering.
    --tripo-prompt TEXT   Text prompt for text-to-3D.
    --tripo-image  PATH   Image path for image-to-3D.

Common sizes: 16, 32, 64 (default), 128, 256
"""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT     = Path(__file__).parent
BLENDER_EXE      = Path(r"C:\Program Files\Blender Foundation\Blender 4.x\blender.exe")
PYTHON_EXE       = Path(r"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe")
BAKE_SCRIPT      = PROJECT_ROOT / "scripts" / "blender_bake.py"
ASSEMBLE_SCRIPT  = PROJECT_ROOT / "scripts" / "assemble_sheet.py"
REFINE_SCRIPT    = PROJECT_ROOT / "scripts" / "refine.py"
TRIPO3D_SCRIPT   = PROJECT_ROOT / "scripts" / "tripo3d.py"
OUTPUT_FRAMES    = PROJECT_ROOT / "output" / "frames"
OUTPUT_SHEET     = PROJECT_ROOT / "output" / "sprite_sheet.png"
OUTPUT_REFINED   = PROJECT_ROOT / "output" / "sprite_sheet_refined.png"
ASSETS_DIR       = PROJECT_ROOT / "assets"


def parse_args():
    parser = argparse.ArgumentParser(description="PixelForge pipeline runner (Phases 1–4).")

    # Phase 1
    parser.add_argument("--mesh", type=str, default=None,
                        help="Path to a .glb file. Omit to use built-in test primitive.")
    parser.add_argument("--sprite-size", type=int, default=64,
                        help="Final sprite size in pixels (square). Default: 64.")
    parser.add_argument("--render-size", type=int, default=None,
                        help="Blender render resolution. Default: sprite-size * 4.")

    # Phase 2
    parser.add_argument("--upscale", action="store_true",
                        help="Phase 2: Run Real-ESRGAN x4 upscale after assembly.")
    parser.add_argument("--colors", type=int, default=0,
                        help="Phase 2: Quantize palette to N colors (0=skip). Default: 0.")
    parser.add_argument("--dither", action="store_true",
                        help="Phase 2: Floyd-Steinberg dithering during quantize.")

    # Phase 3
    parser.add_argument("--generate-mesh", action="store_true",
                        help="Phase 3: Generate mesh via Tripo3D before rendering.")
    parser.add_argument("--tripo-prompt", type=str, default=None,
                        help="Phase 3: Text prompt for text-to-3D.")
    parser.add_argument("--tripo-image", type=str, default=None,
                        help="Phase 3: Image path for image-to-3D.")

    args = parser.parse_args()

    if args.generate_mesh and not args.tripo_prompt and not args.tripo_image:
        parser.error("--generate-mesh requires --tripo-prompt or --tripo-image.")
    if args.tripo_prompt and args.tripo_image:
        parser.error("--tripo-prompt and --tripo-image are mutually exclusive.")

    return args


def run_tripo3d(prompt, image, outfile):
    cmd = [str(PYTHON_EXE), str(TRIPO3D_SCRIPT), "--outfile", str(outfile)]
    if prompt:
        cmd += ["--prompt", prompt]
    elif image:
        cmd += ["--image", str(Path(image).resolve())]

    print(f"\n[PixelForge] Phase 3: Generating mesh via Tripo3D...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("\n[PixelForge] ERROR: Tripo3D mesh generation failed.")
        sys.exit(1)
    return outfile


def run_blender(mesh_path, render_size):
    cmd = [
        str(BLENDER_EXE),
        "--background",
        "--factory-startup",
        "--python", str(BAKE_SCRIPT),
        "--",
        "--outdir", str(OUTPUT_FRAMES),
        "--size",   str(render_size),
    ]
    if mesh_path:
        cmd += ["--mesh", str(Path(mesh_path).resolve())]

    print(f"\n[PixelForge] Phase 1 Step 1/2: Blender headless render ({render_size}px)...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("\n[PixelForge] ERROR: Blender render failed.")
        sys.exit(1)


def run_assemble(sprite_size):
    cmd = [
        str(PYTHON_EXE),
        str(ASSEMBLE_SCRIPT),
        "--framesdir", str(OUTPUT_FRAMES),
        "--outfile",   str(OUTPUT_SHEET),
        "--size",      str(sprite_size),
    ]
    print(f"\n[PixelForge] Phase 1 Step 2/2: Assembling sprite sheet ({sprite_size}px)...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("\n[PixelForge] ERROR: Assembly failed. Is Pillow installed?")
        print("  py -3.12 -m pip install Pillow")
        sys.exit(1)


def run_refine(upscale, colors, dither):
    cmd = [
        str(PYTHON_EXE),
        str(REFINE_SCRIPT),
        "--infile",  str(OUTPUT_SHEET),
        "--outfile", str(OUTPUT_REFINED),
    ]
    if upscale:
        cmd.append("--upscale")
    if colors > 0:
        cmd += ["--colors", str(colors)]
    if dither:
        cmd.append("--dither")

    print(f"\n[PixelForge] Phase 2: Refining sprite sheet...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("\n[PixelForge] ERROR: Refinement failed.")
        sys.exit(1)


def main():
    args = parse_args()
    sprite_size  = args.sprite_size
    render_size  = args.render_size or sprite_size * 4
    run_phase2   = args.upscale or args.colors > 0
    mesh_path    = args.mesh

    print(f"\n[PixelForge] Pipeline starting")
    print(f"[PixelForge]   Sprite size : {sprite_size}x{sprite_size}px")
    print(f"[PixelForge]   Render size : {render_size}x{render_size}px (internal)")
    if args.generate_mesh:
        src = args.tripo_prompt or args.tripo_image
        print(f"[PixelForge]   Phase 3     : Tripo3D ({src})")
    print(f"[PixelForge]   Mesh        : {mesh_path or '(test primitive)'}")
    if run_phase2:
        parts = []
        if args.upscale: parts.append("Real-ESRGAN x4")
        if args.colors > 0: parts.append(f"palette {args.colors} colors{'+ dither' if args.dither else ''}")
        print(f"[PixelForge]   Phase 2     : {', '.join(parts)}")

    # Phase 3 — mesh generation
    if args.generate_mesh:
        generated = ASSETS_DIR / "generated.glb"
        run_tripo3d(args.tripo_prompt, args.tripo_image, generated)
        mesh_path = str(generated)

    # Phase 1 — render
    run_blender(mesh_path, render_size)
    run_assemble(sprite_size)

    # Phase 2 — refinement (opt-in)
    if run_phase2:
        run_refine(args.upscale, args.colors, args.dither)

    print(f"\n[PixelForge] Done!")
    print(f"[PixelForge]   Sprite sheet : {OUTPUT_SHEET}")
    if run_phase2:
        print(f"[PixelForge]   Refined      : {OUTPUT_REFINED}")


if __name__ == "__main__":
    main()
