"""
blend_info.py — PixelForge utility
Runs INSIDE Blender's embedded Python.  Opens a .blend file and prints a
JSON summary (actions list) to stdout so the backend can return it to the UI.

Usage (called by the backend):
    blender.exe --background --factory-startup --python scripts/blend_info.py -- --mesh path.blend

Output line format (surrounded by Blender noise):
    BLEND_INFO_JSON:{"actions": [{"name": "...", "frame_start": 0, "frame_end": 12}, ...]}
"""

import sys
import os
import json
import argparse
import bpy


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", required=True, help="Path to the .blend file.")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    filepath = os.path.abspath(args.mesh)

    bpy.ops.wm.open_mainfile(filepath=filepath)

    # Collect all actions, sorted by name.
    # Filter out internal Rigify widget actions (prefixed with WGT- or WGTS_).
    actions = []
    for action in sorted(bpy.data.actions, key=lambda a: a.name):
        if action.name.startswith(("WGT-", "WGTS_")):
            continue
        fr = action.frame_range
        actions.append({
            "name": action.name,
            "frame_start": int(fr[0]),
            "frame_end":   int(fr[1]),
        })

    print("BLEND_INFO_JSON:" + json.dumps({"actions": actions}))
    bpy.ops.wm.quit_blender()


main()
