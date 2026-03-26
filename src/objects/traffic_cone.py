"""
交通锥（雪糕桶）和参考立杆

用于停车场场景的系统化可见性测试网格。
"""

import bpy


def create_traffic_cone(
    name: str,
    position: tuple,
    height: float = 0.5,
    base_radius: float = 0.15,
    top_radius: float = 0.02,
    color: tuple = (1.0, 0.5, 0.0, 1.0),
    collection: "bpy.types.Collection | None" = None,
) -> bpy.types.Object:
    """
    创建交通锥（雪糕桶）。

    参数:
        name: 物体名称
        position: (x, y) 底部中心位置
        height: 高度 (m)
        base_radius: 底部半径 (m)
        top_radius: 顶部半径 (m)
        color: RGBA 颜色（默认橙色）
        collection: 目标 Collection
    """
    x, y = position[0], position[1]

    bpy.ops.mesh.primitive_cone_add(
        radius1=base_radius,
        radius2=top_radius,
        depth=height,
        location=(x, y, height / 2),
    )
    obj = bpy.context.active_object
    obj.name = name

    mat = bpy.data.materials.new(f"Mat_{name}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.4
    obj.data.materials.append(mat)

    if collection:
        _move_to_collection(obj, collection)

    return obj


def create_reference_pole(
    name: str,
    position: tuple,
    height: float = 1.0,
    radius: float = 0.05,
    color: tuple = (0.9, 0.1, 0.1, 1.0),
    collection: "bpy.types.Collection | None" = None,
) -> bpy.types.Object:
    """
    创建垂直参考立杆。

    参数:
        name: 物体名称
        position: (x, y) 底部中心位置
        height: 高度 (m)
        radius: 半径 (m)
        color: RGBA 颜色（默认红色）
        collection: 目标 Collection
    """
    x, y = position[0], position[1]

    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius,
        depth=height,
        location=(x, y, height / 2),
    )
    obj = bpy.context.active_object
    obj.name = name

    mat = bpy.data.materials.new(f"Mat_{name}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.4
    obj.data.materials.append(mat)

    if collection:
        _move_to_collection(obj, collection)

    return obj


def create_landmark_cube(
    name: str,
    position: tuple,
    size: float = 1.0,
    color: tuple = (0.5, 0.5, 0.5, 1.0),
    collection: "bpy.types.Collection | None" = None,
) -> bpy.types.Object:
    """
    创建地标方块（大型彩色立方体，便于远距离辨识）。

    参数:
        name: 物体名称
        position: (x, y) 底部中心位置
        size: 边长 (m)
        color: RGBA 颜色
        collection: 目标 Collection
    """
    x, y = position[0], position[1]

    bpy.ops.mesh.primitive_cube_add(size=size, location=(x, y, size / 2))
    obj = bpy.context.active_object
    obj.name = name

    mat = bpy.data.materials.new(f"Mat_{name}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.5
    obj.data.materials.append(mat)

    if collection:
        _move_to_collection(obj, collection)

    return obj


def _move_to_collection(obj, collection):
    for col in obj.users_collection:
        col.objects.unlink(obj)
    collection.objects.link(obj)
