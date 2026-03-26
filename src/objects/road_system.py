"""
道路系统构建模块

从 docs/TestScene.md 重构的道路创建代码，支持多种道路预设。
包含路面、车道标线、路肩、地面、光照等基础场景元素。
"""

import math
import pathlib

import yaml

import bpy

_CONFIG_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "config"


def _load_road_preset(preset_name: str) -> dict:
    """
    加载道路预设参数。优先从 scenarios.yaml 的 road_presets 中查找，
    然后从 test_scene.yaml 的 presets 中查找。
    """
    # 从 scenarios.yaml
    with open(_CONFIG_DIR / "scenarios.yaml", encoding="utf-8") as f:
        scenarios_cfg = yaml.safe_load(f)
    road_presets = scenarios_cfg.get("road_presets", {})
    if preset_name in road_presets:
        return road_presets[preset_name]

    # 从 test_scene.yaml
    with open(_CONFIG_DIR / "test_scene.yaml", encoding="utf-8") as f:
        scene_cfg = yaml.safe_load(f)
    presets = scene_cfg.get("presets", {})
    if preset_name in presets:
        preset = dict(presets[preset_name])
        # 补全默认值
        preset.setdefault("road_length", scene_cfg["road"]["road_length"])
        return preset

    raise ValueError(f"Unknown road preset: {preset_name}")


def _load_scene_defaults() -> dict:
    """加载 test_scene.yaml 中的默认参数（标线、颜色等）。"""
    with open(_CONFIG_DIR / "test_scene.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ========== 辅助函数 ==========


def create_collection(name: str) -> bpy.types.Collection:
    """创建一个新的 Blender Collection。"""
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection):
    """将对象移动到指定 Collection。"""
    for col in obj.users_collection:
        col.objects.unlink(obj)
    collection.objects.link(obj)


def _create_material(name: str, color: tuple, roughness: float = 0.85) -> bpy.types.Material:
    """创建简单的 Principled BSDF 材质。"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


# ========== 道路系统 ==========


def create_road_system(
    preset_name: str = "highway",
    vehicle_lane: int = 1,
    collection_name: str = "Road_System",
) -> tuple:
    """
    创建完整的道路系统。

    参数:
        preset_name: 道路预设名称（highway, urban, country_road, highway_3lane）
        vehicle_lane: 车辆所在车道编号（从中央分隔带起算，1-indexed）
        collection_name: Blender Collection 名称

    返回:
        (collection, road_offset_x) 元组
        road_offset_x: 道路 X 偏移量，使车辆原点位于指定车道中央
    """
    params = _load_road_preset(preset_name)
    defaults = _load_scene_defaults()

    lw = params["lane_width"]
    nl = params["num_lanes"]
    mw = params["median_width"]
    sw = params["shoulder_width"]
    road_len = params.get("road_length", 110)

    # 计算道路偏移，使车辆原点 (0,0,0) 位于指定车道中央
    lane_center_from_road_center = mw / 2 + (vehicle_lane - 1) * lw + lw / 2
    road_offset_x = -lane_center_from_road_center

    # 路面宽度
    carriageway_width = nl * lw
    road_width = 2 * carriageway_width + mw

    road_collection = create_collection(collection_name)

    # 道路颜色（从 test_scene.yaml 读取）
    road_colors = defaults.get("road", {}).get("colors", {})
    road_surface_color = tuple(road_colors.get("road_surface", [0.15, 0.15, 0.15, 1.0]))
    shoulder_color = tuple(road_colors.get("shoulder", [0.25, 0.25, 0.22, 1.0]))
    line_white = tuple(road_colors.get("line_white", [0.95, 0.95, 0.95, 1.0]))
    line_yellow = tuple(road_colors.get("line_yellow", [0.95, 0.85, 0.15, 1.0]))

    marking_params = defaults.get("road", {}).get("markings", {})
    line_width = marking_params.get("line_width", 0.15)
    dash_length = marking_params.get("dash_length", 6.0)
    dash_gap = marking_params.get("dash_gap", 9.0)
    edge_line_width = marking_params.get("edge_line_width", 0.20)

    y_center = -road_len / 2 + 30  # 前方30m, 后方80m

    # --- 主路面 ---
    _create_road_plane(
        "Road_Surface", road_width, road_len,
        center_x=road_offset_x, center_y=y_center,
        color=road_surface_color, collection=road_collection,
    )

    # --- 路肩 ---
    for side_name, side_sign in [("Left", -1), ("Right", +1)]:
        sx = road_offset_x + side_sign * (road_width / 2 + sw / 2)
        _create_road_plane(
            f"Shoulder_{side_name}", sw, road_len,
            center_x=sx, center_y=y_center,
            color=shoulder_color, collection=road_collection,
        )

    # --- 中央分隔线（双黄实线）---
    for side_name, offset in [("Left", -0.10), ("Right", +0.10)]:
        x = road_offset_x + (mw / 2 - 0.10) * (1 if side_name == "Right" else -1)
        _create_solid_line(
            f"CenterLine_{side_name}", x,
            y_center - road_len / 2, y_center + road_len / 2,
            width=line_width, color=line_yellow, collection=road_collection,
        )

    # --- 车道分隔线（白色虚线）---
    for i in range(1, nl):
        for side_name, side_sign in [("L", -1), ("R", +1)]:
            x = road_offset_x + side_sign * (mw / 2 + i * lw)
            _create_dashed_line(
                f"LaneLine_{side_name}_{i}", x,
                y_center - road_len / 2, y_center + road_len / 2,
                width=line_width, dash_len=dash_length, gap_len=dash_gap,
                color=line_white, collection=road_collection,
            )

    # --- 边缘线（白色实线）---
    for side_name, side_sign in [("L", -1), ("R", +1)]:
        x = road_offset_x + side_sign * (mw / 2 + nl * lw)
        _create_solid_line(
            f"EdgeLine_{side_name}", x,
            y_center - road_len / 2, y_center + road_len / 2,
            width=edge_line_width, color=line_white, collection=road_collection,
        )

    return road_collection, road_offset_x


def _create_road_plane(
    name, width, length, center_x=0, center_y=0,
    color=(0.15, 0.15, 0.15, 1.0), collection=None,
):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(center_x, center_y, 0.001))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (width, length, 1)
    bpy.ops.object.transform_apply(scale=True)

    mat = _create_material(f"Mat_{name}", color, roughness=0.85)
    obj.data.materials.append(mat)

    if collection:
        move_to_collection(obj, collection)
    return obj


def _create_solid_line(name, x_pos, y_start, y_end, width, color, collection):
    length = abs(y_end - y_start)
    y_center = (y_start + y_end) / 2

    bpy.ops.mesh.primitive_plane_add(size=1, location=(x_pos, y_center, 0.002))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (width, length, 1)
    bpy.ops.object.transform_apply(scale=True)

    mat = _create_material(f"Mat_{name}", color, roughness=0.5)
    obj.data.materials.append(mat)

    if collection:
        move_to_collection(obj, collection)
    return obj


def _create_dashed_line(name, x_pos, y_start, y_end, width, dash_len, gap_len, color, collection):
    cycle_len = dash_len + gap_len
    y = y_start
    idx = 0

    while y < y_end:
        seg_end = min(y + dash_len, y_end)
        seg_center_y = (y + seg_end) / 2
        seg_length = seg_end - y

        bpy.ops.mesh.primitive_plane_add(size=1, location=(x_pos, seg_center_y, 0.002))
        obj = bpy.context.active_object
        obj.name = f"{name}_seg{idx}"
        obj.scale = (width, seg_length, 1)
        bpy.ops.object.transform_apply(scale=True)

        mat = _create_material(f"Mat_{name}_{idx}", color, roughness=0.5)
        obj.data.materials.append(mat)

        if collection:
            move_to_collection(obj, collection)

        y += cycle_len
        idx += 1


# ========== 地面 ==========


def create_ground_plane(
    size: float = 200,
    color: tuple = (0.25, 0.35, 0.15, 1.0),
    center_y: float = -25,
) -> bpy.types.Object:
    """创建道路周围的地面（草地效果）。"""
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, center_y, 0))
    obj = bpy.context.active_object
    obj.name = "Ground_Plane"

    mat = _create_material("Mat_Ground", color, roughness=0.95)
    obj.data.materials.append(mat)

    return obj


def create_parking_surface(
    width: float = 40,
    length: float = 60,
    center_y: float = -20,
    color: tuple = (0.30, 0.30, 0.30, 1.0),
) -> bpy.types.Object:
    """创建停车场地面（灰色沥青）。"""
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, center_y, 0.001))
    obj = bpy.context.active_object
    obj.name = "Parking_Surface"
    obj.scale = (width, length, 1)
    bpy.ops.object.transform_apply(scale=True)

    mat = _create_material("Mat_Parking_Surface", color, roughness=0.85)
    obj.data.materials.append(mat)

    return obj


# ========== 光照 ==========


def setup_lighting() -> bpy.types.Object:
    """
    设置场景光照：Sun Light + 天空背景。
    从 test_scene.yaml 读取光照参数。
    """
    defaults = _load_scene_defaults()
    light_cfg = defaults.get("lighting", {})
    sun_cfg = light_cfg.get("sun", {})

    # Sun Light
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 10))
    sun = bpy.context.active_object
    sun.name = "Sun_Light"
    sun.data.energy = sun_cfg.get("energy", 5.0)
    sun.rotation_euler = (
        math.radians(sun_cfg.get("elevation_deg", 45)),
        math.radians(0),
        math.radians(sun_cfg.get("azimuth_deg", -30)),
    )

    # 世界背景
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    sky_color = tuple(light_cfg.get("sky_color", [0.52, 0.67, 0.85, 1.0]))
    bg.inputs["Color"].default_value = sky_color
    bg.inputs["Strength"].default_value = light_cfg.get("sky_strength", 1.0)

    return sun


# ========== 渲染设置 ==========


def setup_render_settings():
    """设置 Cycles 渲染参数。"""
    defaults = _load_scene_defaults()
    render_cfg = defaults.get("render", {})

    scene = bpy.context.scene
    scene.render.engine = render_cfg.get("engine", "CYCLES")
    scene.cycles.device = render_cfg.get("device", "GPU")

    resolution = render_cfg.get("resolution", [1920, 1080])
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]

    scene.cycles.samples = render_cfg.get("samples", 128)

    # 镜面反射需要足够的弹射次数
    scene.cycles.glossy_bounces = 8
    scene.cycles.max_bounces = 12


# ========== 护栏 ==========


def create_guardrail(
    name: str,
    x_pos: float,
    y_start: float = -80,
    y_end: float = 30,
    height: float = 0.8,
    width: float = 0.12,
    color: tuple = (0.6, 0.6, 0.6, 1.0),
    collection: "bpy.types.Collection | None" = None,
) -> bpy.types.Object:
    """创建公路护栏（薄长方体）。"""
    length = abs(y_end - y_start)
    cy = (y_start + y_end) / 2

    bpy.ops.mesh.primitive_cube_add(size=1, location=(x_pos, cy, height / 2))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (width / 2, length / 2, height / 2)
    bpy.ops.object.transform_apply(scale=True)

    mat = _create_material(f"Mat_{name}", color, roughness=0.5)
    mat.node_tree.nodes.get("Principled BSDF").inputs["Metallic"].default_value = 0.8
    obj.data.materials.append(mat)

    if collection:
        move_to_collection(obj, collection)

    return obj
