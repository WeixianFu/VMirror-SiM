"""
UN ECE R46 法规验证标记物

用于在地面标记 R46 Class III 后视镜法规要求的可视区域，
以及在区域边界放置测试柱。
"""

import bpy


def create_r46_zone(
    name: str,
    x_start: float,
    x_end: float,
    y_start: float,
    y_end: float,
    color: tuple = (0.2, 0.8, 0.2, 0.3),
    collection: "bpy.types.Collection | None" = None,
) -> bpy.types.Object:
    """
    创建 R46 法规可视区域的地面矩形标记（半透明）。

    参数:
        name: 物体名称
        x_start, x_end: X 方向范围
        y_start, y_end: Y 方向范围
        color: RGBA 颜色（alpha 控制透明度）
        collection: 目标 Collection

    Z 高度固定为 0.005，避免与其他地面标记 z-fighting。
    """
    cx = (x_start + x_end) / 2
    cy = (y_start + y_end) / 2
    w = abs(x_end - x_start)
    l = abs(y_end - y_start)

    bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, cy, 0.005))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (w, l, 1)
    bpy.ops.object.transform_apply(scale=True)

    # 半透明材质
    mat = bpy.data.materials.new(f"Mat_{name}")
    mat.use_nodes = True
    mat.use_backface_culling = False

    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Alpha"].default_value = color[3]
    bsdf.inputs["Roughness"].default_value = 0.3

    # Cycles/EEVEE 透明支持
    mat.surface_render_method = "BLENDED"
    obj.data.materials.append(mat)

    if collection:
        _move_to_collection(obj, collection)

    return obj


def create_r46_boundary_line(
    name: str,
    x_pos: float,
    y_start: float,
    y_end: float,
    width: float = 0.10,
    color: tuple = (1.0, 0.5, 0.0, 1.0),
    collection: "bpy.types.Collection | None" = None,
) -> bpy.types.Object:
    """
    创建 R46 最外侧平面标线（标记车辆/房车最宽处）。

    参数:
        name: 物体名称
        x_pos: X 位置（最外侧点）
        y_start, y_end: Y 方向范围
        width: 线宽 (m)
        color: RGBA 颜色
        collection: 目标 Collection
    """
    length = abs(y_end - y_start)
    cy = (y_start + y_end) / 2

    bpy.ops.mesh.primitive_plane_add(size=1, location=(x_pos, cy, 0.006))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (width, length, 1)
    bpy.ops.object.transform_apply(scale=True)

    mat = bpy.data.materials.new(f"Mat_{name}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.3
    obj.data.materials.append(mat)

    if collection:
        _move_to_collection(obj, collection)

    return obj


def create_r46_test_pole(
    name: str,
    position: tuple,
    height: float = 1.0,
    radius: float = 0.05,
    color: tuple = (0.95, 0.95, 0.95, 1.0),
    collection: "bpy.types.Collection | None" = None,
) -> bpy.types.Object:
    """
    创建 R46 法规测试柱（放在可视区域边界关键位置）。

    参数:
        name: 物体名称
        position: (x, y) 底部中心位置
        height: 高度 (m)
        radius: 半径 (m)
        color: RGBA 颜色（默认白色）
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
    bsdf.inputs["Roughness"].default_value = 0.3
    obj.data.materials.append(mat)

    if collection:
        _move_to_collection(obj, collection)

    return obj


def _move_to_collection(obj, collection):
    for col in obj.users_collection:
        col.objects.unlink(obj)
    collection.objects.link(obj)
