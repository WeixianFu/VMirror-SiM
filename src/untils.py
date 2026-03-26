import bpy

def clear_scene():
    """
    Clears the current Blender scene by deselecting all objects and deleting them.
    """
    # Deselect all objects
    bpy.ops.object.select_all(action='DESELECT')
    
    # Select all objects in the current collection
    for obj in bpy.context.collection.objects:
        obj.select_set(True)
    
    # Delete selected objects
    bpy.ops.object.delete()