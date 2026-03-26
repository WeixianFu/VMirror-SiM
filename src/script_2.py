import bpy

import sys, os
# Ensure the script can find the utils module
this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.append(this_dir)

from untils import clear_scene    
clear_scene()


bpy.ops.mesh.primitive_cube_add(size=1, location=(2, 1, 0))
cube_obj = bpy.context.active_object
cube_obj.location.z = 12