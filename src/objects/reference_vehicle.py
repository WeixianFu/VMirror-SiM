"""
参考车辆（简化方块模型）

用于高速公路和变道场景中的邻车道车辆。
使用简化的长方体表示，不需要详细的车辆模型。
"""

import bpy


def create_reference_vehicle(
    name: str,
    position: tuple,
    dimensions: tuple = (1.85, 4.5, 1.5),
    color: tuple = (0.5, 0.5, 0.5, 1.0),
    collection: "bpy.types.Collection | None" = None,
) -> bpy.types.Object:
    """
    创建简化的参考车辆（彩色长方体）。

    参数:
        name: 物体名称
        position: (x, y) 车辆中心底部位置（Z=0，底部在地面上）
        dimensions: (宽, 长, 高) 米
        color: RGBA 颜色
        collection: 目标 Collection

    返回:
        创建的 Blender 物体
    """
    x, y = position[0], position[1]
    w, l, h = dimensions

    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, h / 2))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (w / 2, l / 2, h / 2)
    bpy.ops.object.transform_apply(scale=True)

    # 材质
    mat = bpy.data.materials.new(f"Mat_{name}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.6
    obj.data.materials.append(mat)

    if collection:
        _move_to_collection(obj, collection)

    return obj


def _move_to_collection(obj, collection):
    for col in obj.users_collection:
        col.objects.unlink(obj)
    collection.objects.link(obj)
