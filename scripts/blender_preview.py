"""
blender_preview.py — PixelForge 3D Viewport Preview

Runs INSIDE Blender's embedded Python (bpy). Do not run with system Python.

Converts any supported mesh format to a self-contained GLB for browser preview.
Supports posing to the first frame of a named action and hiding collections for
split-body renders.

Usage (via Blender CLI):
    blender.exe --background --factory-startup --python scripts/blender_preview.py -- \
        <input_path> <output_path> [--action <name>] [--hide-collections <col1,col2>]

Arguments (positional, after "--"):
    input_path           Absolute path to input mesh (.glb, .gltf, .blend, .fbx, .obj)
    output_path          Absolute path for output .glb file

Optional flags:
    --action             Action name to apply; model posed at frame 1 of this action
    --hide-collections   Comma-separated collection names to hide before export

Exit codes:
    0  Success
    1  Import/export error (details printed to stdout)
"""

import sys
import os
import bpy


def parse_args():
    import argparse
    argv = sys.argv
    if "--" not in argv:
        print("[blender_preview] ERROR: No arguments after '--'")
        sys.exit(1)
    argv = argv[argv.index("--") + 1:]

    parser = argparse.ArgumentParser(prog='blender_preview')
    parser.add_argument('input_path',  help='Input mesh path')
    parser.add_argument('output_path', help='Output GLB path')
    parser.add_argument('--action',            type=str, default='',
                        help='Action name; model posed at first frame of this action')
    parser.add_argument('--hide-collections',  type=str, default='',
                        help='Comma-separated collection names to hide (e.g. LowerBody)')
    return parser.parse_args(argv)


def apply_action_at_frame1(action_name):
    """Set the named action on all objects that have animation data, go to frame 1."""
    action = bpy.data.actions.get(action_name)
    if action is None:
        print(f"[blender_preview] Warning: action '{action_name}' not found — using rest pose")
        return
    for obj in bpy.data.objects:
        if obj.animation_data:
            try:
                obj.animation_data.action = action
            except Exception:
                pass
    frame_start = int(action.frame_range[0])
    bpy.context.scene.frame_set(frame_start)
    print(f"[blender_preview] Applied action '{action_name}' at frame {frame_start}")


def hide_collections(col_names_csv):
    """Hide named collections so they are excluded from the GLB export."""
    for col_name in col_names_csv.split(','):
        col_name = col_name.strip()
        if not col_name:
            continue
        col = bpy.data.collections.get(col_name)
        if col:
            col.hide_render = True
            col.hide_viewport = True
            print(f"[blender_preview] Hidden collection: {col_name!r}")
        else:
            print(f"[blender_preview] Warning: collection {col_name!r} not found — skipped")


def main():
    args = parse_args()
    input_path  = os.path.abspath(args.input_path)
    output_path = os.path.abspath(args.output_path)

    if not os.path.exists(input_path):
        print(f"[blender_preview] ERROR: Input file not found: {input_path}")
        sys.exit(1)

    ext = os.path.splitext(input_path)[1].lower()

    try:
        if ext == ".blend":
            # Open the .blend directly — preserves collections, materials, rig.
            # Same pattern as blend_info.py.
            bpy.ops.wm.open_mainfile(filepath=input_path)
        else:
            # Clean empty scene before importing
            bpy.ops.wm.read_factory_settings(use_empty=True)

            if ext in (".glb", ".gltf"):
                bpy.ops.import_scene.gltf(filepath=input_path)
            elif ext == ".fbx":
                bpy.ops.import_scene.fbx(filepath=input_path)
            elif ext == ".obj":
                # Blender 4+/5+ API — old import_scene.obj deprecated in 3.3
                bpy.ops.wm.obj_import(filepath=input_path)
            else:
                print(f"[blender_preview] ERROR: Unsupported format: {ext}")
                sys.exit(1)

        # Apply selected action → pose model at frame 1 of that action
        if args.action:
            apply_action_at_frame1(args.action)

        # Hide collections for split-body preview (same pattern as blender_bake.py)
        if args.hide_collections:
            hide_collections(args.hide_collections)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # use_visible=True ensures hidden collections are excluded from the GLB.
        # export_apply=True bakes the current pose into vertex positions.
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format='GLB',
            export_apply=True,
            use_selection=False,
            use_visible=True,
        )
        print(f"[blender_preview] SUCCESS: Exported GLB to {output_path}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[blender_preview] ERROR: {e}")
        sys.exit(1)


main()
