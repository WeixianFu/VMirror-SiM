import bpy

# def clear_scene():
#     """
#     Clears the current Blender scene by deselecting all objects and deleting them.
#     """
#     # Deselect all objects
#     bpy.ops.object.select_all(action='DESELECT')
    
#     # Select all objects in the current collection
#     for obj in bpy.context.collection.objects:
#         obj.select_set(True)
    
#     # Delete selected objects
#     bpy.ops.object.delete()

import sys, os
# Ensure the script can find the utils module
this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.append(this_dir)

from untils import clear_scene    
clear_scene()

# bpy.ops.wm.obj_import(filepath="C:\Datas\\trailer_mirror\mirror_sim\models\\vehicles\GLS580\GLS580.obj")
from objects import Vehicle
vehicle = Vehicle(model_path="C:\Datas\\trailer_mirror\mirror_sim\models\\vehicles\GLS580\GLS580.obj", location=(15, 0, 10))
# vehicle.obj.location = (15, 0, 10)
vehicle.set_location((15, 0, 10))
