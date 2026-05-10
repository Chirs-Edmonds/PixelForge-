"""
refine.py — PixelForge Phase 2 routes.

Routes:
    POST /refine        Full pixel art pipeline: threshold → posterize → quantize → quality pass → outline
    GET  /check-esrgan  Legacy probe — always returns available=true (no binary needed)

Refine logic runs in-process via Pillow (no subprocess). Pillow must be installed in
the same Python environment as uvicorn: py -3.12 -m pip install Pillow
"""

import json
import re
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from PIL import Image, ImageChops, ImageFilter, ImageOps
except ImportError:
    raise RuntimeError(
        "Pillow is not installed in the backend environment. "
        "Run: py -3.12 -m pip install Pillow"
    )

router = APIRouter()

PROJECT_ROOT   = Path(__file__).parent.parent.parent
OUTPUT_SHEETS  = PROJECT_ROOT / "output" / "sheets"
OUTPUT_MERGED  = PROJECT_ROOT / "output" / "merged"
OUTPUT_REFINED = PROJECT_ROOT / "output" / "refined"

DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
_SAFE_NAME = re.compile(r'[^a-zA-Z0-9_-]')

_BODY_TARGET = {"full": "body", "upper": "upper", "lower": "legs"}
_BODY_SUFFIX = {"body": "", "upper": "_Upper", "legs": "_Lower"}

_DITHER_MAP = {
    "floyd": Image.Dither.FLOYDSTEINBERG,
    "bayer": getattr(Image.Dither, "ORDERED", Image.Dither.FLOYDSTEINBERG),
    "none":  Image.Dither.NONE,
}


@router.get("/check-esrgan")
async def check_esrgan():
    # Upscale is now pure-Pillow nearest-neighbour — no external binary required.
    return {"available": True}


class GodotExportConfig(BaseModel):
    godot_project_path: str
    sprite_folder: str = "assets/sprites/player/master"
    char_type: str = "Char"
    weapon: str = "None"
    action: str
    direction: str = "None"
    fps: float = 12.0
    loop: bool = False


class RefineRequest(BaseModel):
    upscale:        bool = False
    colors:         int  = 0           # 0 = skip; useful: 8, 16, 32, 64
    dither_mode:    str  = "none"      # "none" | "floyd" | "bayer"
    alpha_cutoff:   int  = 16          # 1–254; pixels with α < cutoff → transparent
    outline:        bool = False       # inject 1px border around sprite silhouette
    outline_color:  str  = "#000000"   # hex colour for outline
    posterize_bits: int  = 0           # 0 = skip; 2 = 4 colours, 3 = 8, 4 = 16
    is_animation:   bool = False
    name:           str  = "sprite_sheet"
    body_part:      str  = "full"
    godot_export:   GodotExportConfig | None = None


def _refine_image(
    src: Path,
    dst: Path,
    upscale: bool,
    colors: int,
    dither_mode: str,
    alpha_cutoff: int = 16,
    outline: bool = False,
    outline_color: str = "#000000",
    posterize_bits: int = 0,
) -> None:
    """Full pixel art pipeline: threshold → posterize → quantize → quality pass → outline."""
    img = Image.open(src).convert("RGBA")
    original_size = img.size

    # Step 1: Hard alpha threshold — preserves thin EEVEE-feathered geometry
    # (sword blades, fine trim) that renders with low α values.
    r, g, b, a = img.split()
    a = a.point(lambda v: 255 if v >= alpha_cutoff else 0)
    img = Image.merge("RGBA", (r, g, b, a))

    # Step 2: Posterize — hard colour banding before quantize so gradients become blocks.
    if posterize_bits > 0:
        alpha = img.split()[3]
        rgb = ImageOps.posterize(img.convert("RGB"), posterize_bits)
        img = rgb.convert("RGBA")
        img.putalpha(alpha)

    # Step 3: Palette quantize (before upscale so gradients collapse to flat blocks first).
    if colors > 0:
        dither_enum = _DITHER_MAP.get(dither_mode, Image.Dither.NONE)
        alpha = img.split()[3]
        try:
            quantized = img.convert("RGB").quantize(colors=colors, dither=dither_enum)
        except Exception:
            quantized = img.convert("RGB").quantize(colors=colors, dither=Image.Dither.NONE)
        quantized = quantized.convert("RGBA")
        quantized.putalpha(alpha)
        img = quantized

    # Step 4: NN upscale → LANCZOS downscale → second alpha threshold.
    # The roundtrip flattens gradients into crisp pixel blocks then blends them back
    # at original resolution. Second threshold kills fringe pixels LANCZOS creates.
    if upscale:
        w, h = img.size
        img = img.resize((w * 4, h * 4), Image.NEAREST)
        img = img.resize(original_size, Image.LANCZOS)
        r2, g2, b2, a2 = img.split()
        a2 = a2.point(lambda v: 255 if v >= 128 else 0)
        img = Image.merge("RGBA", (r2, g2, b2, a2))

    # Step 5: Outline — 1px border painted around the sprite silhouette.
    if outline:
        hex_c = outline_color.lstrip('#').ljust(6, '0')
        r_c = int(hex_c[0:2], 16)
        g_c = int(hex_c[2:4], 16)
        b_c = int(hex_c[4:6], 16)
        alpha_ch = img.split()[3]
        dilated  = alpha_ch.filter(ImageFilter.MaxFilter(3))
        border   = ImageChops.difference(dilated, alpha_ch)
        colour_layer = Image.new("RGBA", img.size, (r_c, g_c, b_c, 255))
        img.paste(colour_layer, mask=border)

    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(dst), "PNG")


def _call_refine(req: RefineRequest, src: Path, dst: Path) -> None:
    _refine_image(
        src, dst,
        upscale=req.upscale,
        colors=req.colors,
        dither_mode=req.dither_mode,
        alpha_cutoff=req.alpha_cutoff,
        outline=req.outline,
        outline_color=req.outline_color,
        posterize_bits=req.posterize_bits,
    )


def _export_to_godot(body_part: str, name: str, godot_export: GodotExportConfig) -> None:
    project_root = Path(godot_export.godot_project_path)
    master_dir   = project_root / godot_export.sprite_folder
    master_dir.mkdir(parents=True, exist_ok=True)
    config_path  = master_dir / "sprite_config.json"

    base = f"{godot_export.char_type}_{godot_export.weapon}_{godot_export.action}_{godot_export.direction}"

    if body_part == "split":
        passes = [
            (f"{name}_upper_all_refined.png", "upper"),
            (f"{name}_legs_all_refined.png",  "legs"),
        ]
    else:
        target = _BODY_TARGET.get(body_part, "body")
        passes = [(f"{name}_all_refined.png", target)]

    try:
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else None
    except (json.JSONDecodeError, OSError):
        config = None
    if config is None:
        config = {
            "outputs": {
                "body":  "res://resources/sprites/player_sprite_frames.tres",
                "legs":  "res://resources/sprites/player_legs_sprite_frames.tres",
                "upper": "res://resources/sprites/player_upper_sprite_frames.tres",
            },
            "animations": [],
        }

    for refined_filename, target in passes:
        src = OUTPUT_REFINED / refined_filename
        if not src.exists():
            print(f"[PixelForge→Godot] WARNING: refined file not found: {src}")
            continue

        with Image.open(src) as img:
            sprite_size = img.size[1] // 8

        suffix = _BODY_SUFFIX[target]
        master_filename = f"{base}{suffix}_master.png"
        shutil.copy2(src, master_dir / master_filename)
        print(f"[PixelForge→Godot] {refined_filename} → {master_filename}")

        new_entry = {
            "name": base, "target": target, "file": master_filename,
            "fps": godot_export.fps, "loop": godot_export.loop,
            "frame_size": sprite_size, "row_order": "north_first",
        }
        animations = config.setdefault("animations", [])
        for i, entry in enumerate(animations):
            if entry.get("name") == base and entry.get("target") == target:
                animations[i] = new_entry
                break
        else:
            animations.append(new_entry)

    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[PixelForge→Godot] Updated {config_path}")


@router.post("/refine")
async def run_refine(req: RefineRequest):
    nothing_to_do = not req.upscale and req.colors == 0 and not req.outline and req.posterize_bits == 0
    if nothing_to_do:
        raise HTTPException(400, "Nothing to do: enable at least one refinement option.")
    if req.colors < 0 or req.colors == 1:
        raise HTTPException(400, "colors must be 0 (skip) or >= 2.")
    if req.posterize_bits not in (0, 2, 3, 4):
        raise HTTPException(400, "posterize_bits must be 0 (skip), 2, 3, or 4.")
    if not (1 <= req.alpha_cutoff <= 254):
        raise HTTPException(400, "alpha_cutoff must be between 1 and 254.")
    if req.godot_export is not None:
        if not req.is_animation:
            raise HTTPException(400, "Godot export only supports animation mode.")
        gp = Path(req.godot_export.godot_project_path)
        if not gp.is_absolute() or not gp.is_dir():
            raise HTTPException(400, f"Godot project path invalid: {gp}")

    # Sanitize name the same way render.py does — files on disk use the safe version.
    name = _SAFE_NAME.sub('_', req.name).strip('_') or 'sprite_sheet'

    if req.is_animation:
        if not OUTPUT_SHEETS.exists():
            raise HTTPException(404, "No animation sheets found. Run /render first.")

        if req.body_part == "split":
            failed = []
            has_master_upper = False
            has_master_legs  = False

            for suffix, master_flag in [("_upper", "upper"), ("_legs", "legs")]:
                prefix = f"{name}{suffix}"
                master_src = OUTPUT_MERGED / f"{prefix}_all.png"
                master_dst = OUTPUT_REFINED / f"{prefix}_all_refined.png"
                if not master_src.exists():
                    failed.append(f"{suffix}: no merged master sheet — run render with 'Merge 8-direction' enabled")
                    continue
                try:
                    _call_refine(req, master_src, master_dst)
                    if master_flag == "upper":
                        has_master_upper = True
                    else:
                        has_master_legs = True
                except Exception as e:
                    failed.append(f"{suffix}/master: {e}")

            if failed:
                raise HTTPException(500, f"Refinement failed: {'; '.join(failed)}")

            if req.godot_export is not None:
                try:
                    _export_to_godot(req.body_part, name, req.godot_export)
                except Exception as e:
                    print(f"[PixelForge→Godot] WARNING: export failed: {e}")

            return {
                "output":           f"sheets/{name}",
                "is_animation":     True,
                "is_split":         True,
                "has_master_upper": has_master_upper,
                "has_master_legs":  has_master_legs,
            }

        master_src = OUTPUT_MERGED / f"{name}_all.png"
        master_dst = OUTPUT_REFINED / f"{name}_all_refined.png"
        if not master_src.exists():
            raise HTTPException(
                404,
                "No merged master sheet found. Run /render with 'Merge 8-direction' enabled first."
            )
        try:
            _call_refine(req, master_src, master_dst)
        except Exception as e:
            raise HTTPException(500, f"Refinement failed: {e}")

        if req.godot_export is not None:
            try:
                _export_to_godot(req.body_part, name, req.godot_export)
            except Exception as e:
                print(f"[PixelForge→Godot] WARNING: export failed: {e}")

        return {"output": f"sheets/{name}", "is_animation": True, "has_master": True}

    if req.body_part == "split":
        suffixes = [("_upper", f"{name}_upper"), ("_legs", f"{name}_legs")]
        outputs = []
        for _, base in suffixes:
            src = PROJECT_ROOT / "output" / f"{base}.png"
            dst = OUTPUT_REFINED / f"{base}_refined.png"
            if not src.exists():
                raise HTTPException(404, f"No sprite sheet found: {base}.png. Run /render first.")
            try:
                _call_refine(req, src, dst)
                outputs.append(f"refined/{base}_refined.png")
            except Exception as e:
                raise HTTPException(500, f"Refinement failed for {base}: {e}")
        return {"output": outputs, "is_split": True}

    src = PROJECT_ROOT / "output" / f"{name}.png"
    dst = OUTPUT_REFINED / f"{name}_refined.png"
    if not src.exists():
        raise HTTPException(404, "No sprite sheet found. Run /render first.")
    try:
        _call_refine(req, src, dst)
    except Exception as e:
        raise HTTPException(500, f"Refinement failed: {e}")
    return {"output": f"refined/{name}_refined.png"}
