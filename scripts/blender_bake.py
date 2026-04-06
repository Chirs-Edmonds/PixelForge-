"""
blender_bake.py — PixelForge Phase 1

Runs INSIDE Blender's embedded Python (bpy). Do not run with system Python.

Usage (via Blender CLI):
    blender.exe --background --factory-startup --python scripts/blender_bake.py -- \
        --outdir output/frames \
        --size 256 \
        [--mesh path/to/mesh.glb]

Arguments (after the "--" separator):
    --outdir PATH   Directory to write 8 PNG frames into (required)
    --size   INT    Render resolution per frame, square (default: 256)
    --mesh   PATH   Path to a .glb file to import. If omitted, a humanoid test
                    primitive is generated automatically.

Output:
    {outdir}/N.png, NE.png, E.png, SE.png, S.png, SW.png, W.png, NW.png
    Each is RENDER_SIZE x RENDER_SIZE, RGBA, transparent background.
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

    # Compute true bounding box (min/max) across all mesh objects in world space
    mesh_objects = [o for o in scene.objects if o.type == 'MESH']
    if not mesh_objects:
        raise RuntimeError("No mesh objects found in scene after import/generation.")

    all_world_verts = []
    for obj in mesh_objects:
        mat = obj.matrix_world
        for v in obj.data.vertices:
            all_world_verts.append(mat @ v.co)

    xs = [v.x for v in all_world_verts]
    ys = [v.y for v in all_world_verts]
    zs = [v.z for v in all_world_verts]

    bbox_min = mathutils.Vector((min(xs), min(ys), min(zs)))
    bbox_max = mathutils.Vector((max(xs), max(ys), max(zs)))
    center   = (bbox_min + bbox_max) / 2.0

    # Use the full 3D diagonal so the isometric view (which sees width+height
    # simultaneously) always fits the mesh with 20% padding.
    dx = bbox_max.x - bbox_min.x
    dy = bbox_max.y - bbox_min.y
    dz = bbox_max.z - bbox_min.z
    diagonal = math.sqrt(dx*dx + dy*dy + dz*dz)
    ortho_scale = diagonal * 1.2
    ortho_scale = max(ortho_scale, 0.5)  # minimum sanity floor

    print(f"[PixelForge] Mesh bbox center : {center}")
    print(f"[PixelForge] Mesh bbox extent : {diagonal:.3f} → ortho_scale {ortho_scale:.3f}")
    return center, ortho_scale


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

def setup_camera(scene, ortho_scale):
    cam_data = bpy.data.cameras.new("IsoCamera")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = ortho_scale
    cam_ob = bpy.data.objects.new("IsoCamera", cam_data)
    scene.collection.objects.link(cam_ob)
    scene.camera = cam_ob
    return cam_ob


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


def render_all_directions(scene, cam_ob, center, outdir):
    os.makedirs(outdir, exist_ok=True)
    elev_rad = math.radians(ELEVATION_DEG)

    for direction_name, azimuth_deg in DIRECTIONS:
        az_rad = math.radians(azimuth_deg)

        # Spherical → Cartesian, offset from mesh center
        x = center.x + CAMERA_DISTANCE * math.cos(elev_rad) * math.sin(az_rad)
        y = center.y - CAMERA_DISTANCE * math.cos(elev_rad) * math.cos(az_rad)
        z = center.z + CAMERA_DISTANCE * math.sin(elev_rad)

        cam_ob.location = (x, y, z)

        # Orient camera: -Z axis points from camera toward mesh center
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
    center, ortho_scale = load_or_generate_mesh(args, scene)
    cam_ob = setup_camera(scene, ortho_scale)
    render_all_directions(scene, cam_ob, center, outdir)

    print("[PixelForge] blender_bake.py complete.")


if __name__ == "__main__":
    main()
