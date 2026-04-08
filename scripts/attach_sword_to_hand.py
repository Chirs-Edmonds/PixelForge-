"""
attach_sword_to_hand.py
-----------------------
Attaches a sword object to a character's right hand bone using a
Child Of constraint. Run this in Blender's Scripting workspace.

HOW TO USE:
  1. Open Blender's Scripting workspace (top tab row → Scripting)
  2. Open this file (or paste it into the text editor)
  3. Edit the three variables below to match your scene
  4. Click Run Script
  5. Select the sword, then use the Child Of constraint panel to
     click "Set Inverse" and fine-tune the position/rotation offset
"""

import bpy

# ── CONFIGURE THESE ──────────────────────────────────────────────────────────
SWORD_OBJECT   = "Sword"          # Exact name of your sword object in the Outliner
ARMATURE_OBJ   = "Armature"       # Exact name of your character's armature object
HAND_BONE      = "hand_r"         # Exact bone name (check Armature > Pose Mode > bone name)
CONSTRAINT_NAME = "Sword_Hold"    # Name given to the new constraint (rename if you like)
# ─────────────────────────────────────────────────────────────────────────────


def attach_sword():
    # --- Validate objects exist ---
    sword = bpy.data.objects.get(SWORD_OBJECT)
    armature = bpy.data.objects.get(ARMATURE_OBJ)

    if sword is None:
        raise ValueError(f"Sword object '{SWORD_OBJECT}' not found. "
                         "Check SWORD_OBJECT matches the name in your Outliner.")
    if armature is None:
        raise ValueError(f"Armature object '{ARMATURE_OBJ}' not found. "
                         "Check ARMATURE_OBJ matches the name in your Outliner.")
    if armature.type != 'ARMATURE':
        raise TypeError(f"'{ARMATURE_OBJ}' is not an Armature object.")

    # --- Validate bone exists ---
    bone_names = [b.name for b in armature.data.bones]
    if HAND_BONE not in bone_names:
        raise ValueError(
            f"Bone '{HAND_BONE}' not found in '{ARMATURE_OBJ}'.\n"
            f"Available bones: {bone_names}"
        )

    # --- Remove existing constraint with same name (safe re-run) ---
    existing = sword.constraints.get(CONSTRAINT_NAME)
    if existing:
        sword.constraints.remove(existing)
        print(f"Removed existing '{CONSTRAINT_NAME}' constraint.")

    # --- Add Child Of constraint ---
    con = sword.constraints.new(type='CHILD_OF')
    con.name = CONSTRAINT_NAME
    con.target = armature
    con.subtarget = HAND_BONE

    # Set all channels on (position + rotation + scale)
    con.use_location_x = True
    con.use_location_y = True
    con.use_location_z = True
    con.use_rotation_x = True
    con.use_rotation_y = True
    con.use_rotation_z = True
    con.use_scale_x    = True
    con.use_scale_y    = True
    con.use_scale_z    = True

    # --- Compute Set Inverse automatically ---
    # This bakes the sword's current world transform relative to the hand,
    # so it snaps into place without jumping. Equivalent to clicking
    # "Set Inverse" in the Properties panel.
    context_override = bpy.context.copy()
    context_override["constraint"] = con

    # Blender 4.x / 5.x uses the operator with context override
    with bpy.context.temp_override(**context_override):
        bpy.ops.constraint.childof_set_inverse(
            constraint=CONSTRAINT_NAME,
            owner='OBJECT'
        )

    print(
        f"\n✓ '{SWORD_OBJECT}' is now attached to bone '{HAND_BONE}' "
        f"on '{ARMATURE_OBJ}' via constraint '{CONSTRAINT_NAME}'.\n"
        f"\nNEXT STEPS — to manually tweak the hold position:\n"
        f"  1. Select '{SWORD_OBJECT}' in the Outliner\n"
        f"  2. Object Properties (orange square icon) → Constraints tab\n"
        f"  3. You'll see '{CONSTRAINT_NAME}' listed\n"
        f"  4. Click 'Clear Inverse', reposition the sword by hand, "
             "then click 'Set Inverse' again\n"
        f"  5. To temporarily detach: set Influence slider to 0\n"
        f"  6. To permanently bake: Object → Apply → Visual Transform, "
             "then remove the constraint\n"
    )


attach_sword()
