"""
blender_bake.py — PixelForge Phase 1

Runs INSIDE Blender's embedded Python (bpy). Do not run with system Python.

Usage (via Blender CLI):
    blender.exe --background --factory-startup --python scripts/blender_bake.py -- \
        --outdir output/frames \
        --size 256 \
        [--mesh path/to/mesh.glb] \
        [--frame-start 1 --frame-end 24]

Arguments (after the "--" separator):
    --outdir       PATH  Directory to write PNG frames into (required)
    --size         INT   Render resolution per frame, square (default: 256)
    --mesh         PATH  Path to a .glb file to import. If omitted, a humanoid test
                         primitive is generated automatically.
    --frame-start  INT   First frame to render (default: scene frame_start)
    --frame-end    INT   Last frame to render (default: scene frame_end)

Output (single-frame mode, frame-start == frame-end):
    {outdir}/N.png, NE.png, E.png, SE.png, S.png, SW.png, W.png, NW.png

Output (animation mode, frame-start < frame-end):
    {outdir}/N/0001.png, {outdir}/N/0002.png, ...
    {outdir}/NE/0001.png, ...  (8 subdirectories, one per direction)
"""

import sys
import os
import math
import argparse

import bpy
import mathutils


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    parser = argparse.ArgumentParser(
        description="Render 8 isometric directions of a mesh using Blender."
    )
    parser.add_argument("--outdir", type=str, required=True,
                        help="Directory to write 8 PNG frames into.")
    parser.add_argument("--size", type=int, default=256,
                        help="Render resolution per frame (square). Default: 256.")
    parser.add_argument("--mesh", type=str, default=None,
                        help="Path to .glb file. If omitted, generates test primitive.")
    parser.add_argument("--frame-start", type=int, default=None,
                        help="First frame to render. Default: scene frame_start.")
    parser.add_argument("--frame-end", type=int, default=None,
                        help="Last frame to render. Default: scene frame_end.")
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------

def setup_scene(size):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    # EEVEE — Blender 5.x uses BLENDER_EEVEE_NEXT
    try:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    except TypeError:
        scene.render.engine = 'BLENDER_EEVEE'

    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.use_file_extension = False

    return scene


# ---------------------------------------------------------------------------
# Lighting
# ---------------------------------------------------------------------------

def add_lighting(scene):
    # Key light — sun from upper-front-right
    key_data = bpy.data.lights.new("KeyLight", type='SUN')
    key_data.energy = 3.0
    key_ob = bpy.data.objects.new("KeyLight", key_data)
    scene.collection.objects.link(key_ob)
    key_ob.rotation_euler = (math.radians(45), 0, math.radians(45))

    # Fill light — sun from opposite side, softer
    fill_data = bpy.data.lights.new("FillLight", type='SUN')
    fill_data.energy = 1.0
    fill_ob = bpy.data.objects.new("FillLight", fill_data)
    scene.collection.objects.link(fill_ob)
    fill_ob.rotation_euler = (math.radians(45), 0, math.radians(225))


# ---------------------------------------------------------------------------
# Mesh: load .glb or generate humanoid test primitive
# ---------------------------------------------------------------------------

def load_or_generate_mesh(args, scene):
    if args.mesh:
        mesh_path = os.path.abspath(args.mesh)
        if not os.path.exists(mesh_path):
            raise FileNotFoundError(f"Mesh file not found: {mesh_path}")
        bpy.ops.import_scene.gltf(filepath=mesh_path)
        print(f"[PixelForge] Imported mesh: {mesh_path}")
    else:
        print("[PixelForge] No mesh provided — generating humanoid test primitive.")
        _generate_humanoid(scene)

    # Compute true bounding box (min/max) across all mesh objects in world space.
    # Evaluate at the first animation frame so armature deformations are applied —
    # obj.data.vertices gives rest-pose positions and will mis-centre animated chars.
    mesh_objects = [o for o in scene.objects if o.type == 'MESH']
    if not mesh_objects:
        raise RuntimeError("No mesh objects found in scene after import/generation.")

    eval_frame = args.frame_start if args.frame_start is not None else scene.frame_start
    scene.frame_set(eval_frame)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()

    all_world_verts = []
    for obj in mesh_objects:
        eval_obj = obj.evaluated_get(depsgraph)
        mat = eval_obj.matrix_world
        for v in eval_obj.data.vertices:
            all_world_verts.append(mat @ v.co)

    xs = [v.x for v in all_world_verts]
    ys = [v.y for v in all_world_verts]
    zs = [v.z for v in all_world_verts]

    bbox_min = mathutils.Vector((min(xs), min(ys), min(zs)))
    bbox_max = mathutils.Vector((max(xs), max(ys), max(zs)))
    center   = (bbox_min + bbox_max) / 2.0

    print(f"[PixelForge] Mesh bbox center : {center}")
    print(f"[PixelForge] Mesh bbox min    : {bbox_min}")
    print(f"[PixelForge] Mesh bbox max    : {bbox_max}")
    return bbox_min, bbox_max, center


def _generate_humanoid(scene):
    # Body — tall cylinder
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.3, depth=1.2, location=(0, 0, 0.6)
    )
    bpy.context.active_object.name = "Body"

    # Head — UV sphere
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.25, location=(0, 0, 1.45)
    )
    bpy.context.active_object.name = "Head"

    # Right arm
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.1, depth=0.8,
        location=(0.5, 0, 0.9),
        rotation=(0, math.radians(90), 0)
    )
    bpy.context.active_object.name = "ArmR"

    # Left arm
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.1, depth=0.8,
        location=(-0.5, 0, 0.9),
        rotation=(0, math.radians(90), 0)
    )
    bpy.context.active_object.name = "ArmL"


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------

def setup_camera(scene):
    cam_data = bpy.data.cameras.new("IsoCamera")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 1.0  # placeholder; set by compute_global_ortho_scale
    cam_ob = bpy.data.objects.new("IsoCamera", cam_data)
    scene.collection.objects.link(cam_ob)
    scene.camera = cam_ob
    return cam_ob


def get_bbox_corners(bbox_min, bbox_max):
    """Return all 8 corners of the AABB."""
    corners = []
    for x in (bbox_min.x, bbox_max.x):
        for y in (bbox_min.y, bbox_max.y):
            for z in (bbox_min.z, bbox_max.z):
                corners.append(mathutils.Vector((x, y, z)))
    return corners


def compute_global_ortho_scale(cam_ob, center, corners):
    """
    Compute the tightest ortho_scale that fits all bbox corners across all 8
    isometric directions, then set it on the camera.

    Uses fully analytic projection — no reliance on Blender's matrix_world
    (which is NOT reliably updated by view_layer.update() in headless mode).

    Camera axes are derived to match to_track_quat('-Z', 'Y'):
      • look_vec  → camera -Z  (forward)
      • world +Y  → cam_up (+Y), Gram-Schmidt orthogonalised against look_vec
      • cam_right → cam_up × (-look_vec)   (camera +X)

    For orthographic projection, the screen-space offset of a corner from the
    frame centre equals the dot products of (corner − centre) with cam_right
    and cam_up.  max_half is therefore the true half-extent on screen.
    """
    elev_rad  = math.radians(ELEVATION_DEG)
    up_hint   = mathutils.Vector((0, 1, 0))   # world +Y  (matches 'Y' in to_track_quat)
    max_scale = 0.0

    for _, az_deg in DIRECTIONS:
        az_rad = math.radians(az_deg)
        cx = center.x + CAMERA_DISTANCE * math.cos(elev_rad) * math.sin(az_rad)
        cy = center.y - CAMERA_DISTANCE * math.cos(elev_rad) * math.cos(az_rad)
        cz = center.z + CAMERA_DISTANCE * math.sin(elev_rad)
        cam_pos  = mathutils.Vector((cx, cy, cz))
        look_vec = (center - cam_pos).normalized()

        # Gram-Schmidt: project world +Y onto the plane ⊥ to look_vec
        cam_up = up_hint - up_hint.dot(look_vec) * look_vec
        if cam_up.length < 1e-6:           # degenerate — look_vec ≈ ±world Y
            cam_up = mathutils.Vector((0, 0, 1)) - \
                     mathutils.Vector((0, 0, 1)).dot(look_vec) * look_vec
        cam_up    = cam_up.normalized()
        cam_right = cam_up.cross(-look_vec)  # camera +X axis

        # Measure screen-space half-extents for every corner
        max_half = 0.0
        for corner in corners:
            rel      = corner - center
            max_half = max(max_half, abs(cam_right.dot(rel)), abs(cam_up.dot(rel)))

        max_scale = max(max_scale, max_half * 2.0 * 1.15)

    max_scale = max(max_scale, 0.1)
    cam_ob.data.ortho_scale = max_scale
    print(f"[PixelForge] Tight ortho_scale (all 8 dirs): {max_scale:.4f}")


# ---------------------------------------------------------------------------
# 8-direction render loop
# ---------------------------------------------------------------------------

# Direction name → azimuth in degrees.
# Azimuth 0° = North = camera positioned at -Y looking toward +Y (Blender convention).
# Increases clockwise when viewed from above (game-standard CW from North).
DIRECTIONS = [
    ("N",   0),
    ("NE",  45),
    ("E",   90),
    ("SE",  135),
    ("S",   180),
    ("SW",  225),
    ("W",   270),
    ("NW",  315),
]

ELEVATION_DEG = 35.264   # True isometric: arctan(1 / sqrt(2))
CAMERA_DISTANCE = 6.0    # Blender units radius of orbit sphere


def render_all_directions(scene, cam_ob, center, outdir, frame_start, frame_end, is_animation):
    os.makedirs(outdir, exist_ok=True)
    elev_rad = math.radians(ELEVATION_DEG)

    if is_animation:
        # Animation mode: position camera once per direction, render all frames.
        # Outer loop = directions (avoid repositioning 8× per frame).
        for direction_name, azimuth_deg in DIRECTIONS:
            az_rad = math.radians(azimuth_deg)

            x = center.x + CAMERA_DISTANCE * math.cos(elev_rad) * math.sin(az_rad)
            y = center.y - CAMERA_DISTANCE * math.cos(elev_rad) * math.cos(az_rad)
            z = center.z + CAMERA_DISTANCE * math.sin(elev_rad)

            cam_ob.location = (x, y, z)
            look_vec = mathutils.Vector((center.x - x, center.y - y, center.z - z)).normalized()
            rot_quat = look_vec.to_track_quat('-Z', 'Y')
            cam_ob.rotation_euler = rot_quat.to_euler()

            dir_out = os.path.join(outdir, direction_name)
            os.makedirs(dir_out, exist_ok=True)

            for f in range(frame_start, frame_end + 1):
                scene.frame_set(f)
                out_path = os.path.join(dir_out, f"{f:04d}.png")
                scene.render.filepath = out_path
                bpy.ops.render.render(write_still=True)
                print(f"[PixelForge] {direction_name} frame {f}/{frame_end} -> {out_path}")

        print(f"[PixelForge] Animation ({frame_start}-{frame_end}) rendered to: {outdir}/{{N,NE,...NW}}/")
    else:
        # Single-frame mode: set frame once, render 8 directions to flat files.
        scene.frame_set(frame_start)

        for direction_name, azimuth_deg in DIRECTIONS:
            az_rad = math.radians(azimuth_deg)

            x = center.x + CAMERA_DISTANCE * math.cos(elev_rad) * math.sin(az_rad)
            y = center.y - CAMERA_DISTANCE * math.cos(elev_rad) * math.cos(az_rad)
            z = center.z + CAMERA_DISTANCE * math.sin(elev_rad)

            cam_ob.location = (x, y, z)
            look_vec = mathutils.Vector((center.x - x, center.y - y, center.z - z)).normalized()
            rot_quat = look_vec.to_track_quat('-Z', 'Y')
            cam_ob.rotation_euler = rot_quat.to_euler()

            out_path = os.path.join(outdir, f"{direction_name}.png")
            scene.render.filepath = out_path
            bpy.ops.render.render(write_still=True)
            print(f"[PixelForge] Rendered {direction_name} -> {out_path}")

        print(f"[PixelForge] All 8 directions rendered to: {outdir}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    outdir = os.path.abspath(args.outdir)

    print(f"[PixelForge] blender_bake.py starting")
    print(f"[PixelForge] Output dir : {outdir}")
    print(f"[PixelForge] Frame size : {args.size}x{args.size}")
    print(f"[PixelForge] Mesh input : {args.mesh or '(test primitive)'}")

    scene = setup_scene(args.size)
    add_lighting(scene)
    bbox_min, bbox_max, center = load_or_generate_mesh(args, scene)
    cam_ob = setup_camera(scene)
    corners = get_bbox_corners(bbox_min, bbox_max)
    compute_global_ortho_scale(cam_ob, center, corners)

    frame_start = args.frame_start if args.frame_start is not None else scene.frame_start
    frame_end   = args.frame_end   if args.frame_end   is not None else scene.frame_end
    is_animation = frame_end > frame_start

    if is_animation:
        print(f"[PixelForge] Animation mode: frames {frame_start}–{frame_end} ({frame_end - frame_start + 1} frames)")
    else:
        print(f"[PixelForge] Single-frame mode: frame {frame_start}")

    render_all_directions(scene, cam_ob, center, outdir, frame_start, frame_end, is_animation)

    # Write sentinel so the web backend can reliably detect success.
    # (Blender exits with code 0 even on Python errors, so file checks are needed.)
    sentinel = os.path.join(outdir, ".render_done")
    with open(sentinel, "w") as f:
        f.write("ok")

    print("[PixelForge] blender_bake.py complete.")


if __name__ == "__main__":
    main()
