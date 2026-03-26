"""
后视镜构建模块（简化模型）

简化模型结构：
    Mirror_Assembly (Empty, 安装锚点) → Mirror_Glass (Mesh, 反射镜面)

仅建模安装锚点和反射镜面，不含壳体/镜臂。
镜面全面积参与反射，无边框遮挡。

使用方法（在 Blender 中运行）：
    import sys
    sys.path.insert(0, '/path/to/VMirror-SiM/src')
    from mirror_builder import create_mirror_assembly

    # 为 CR-V 创建左侧标准凸面镜
    assembly, glass = create_mirror_assembly(
        vehicle_key='suv',
        mirror_type_key='standard_convex',
        side='left',
    )
"""

import math
import pathlib

import yaml

try:
    import bpy
    import mathutils
except ImportError:
    raise ImportError("此模块必须在 Blender Python 环境中运行")

# ========== 坐标系映射常量 ==========
# 所有位置均以米为单位
# 原点 = 前轴中心地面投影
FORWARD = "+Y"  # 车头方向
REAR = "-Y"  # 车尾方向
LEFT = "-X"  # 驾驶员侧（左舵车）
RIGHT = "+X"  # 副驾驶侧（左舵车）
UP = "+Z"  # 向上
DOWN = "-Z"  # 向下

# ========== 配置加载 ==========

_CONFIG_DIR = pathlib.Path(__file__).resolve().parent.parent / "config"


def _load_yaml(name: str) -> dict:
    with open(_CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_vehicles_config() -> dict:
    return _load_yaml("vehicles.yaml")


def load_mirrors_config() -> dict:
    return _load_yaml("mirrors.yaml")


# ========== 安装基准点 ==========


def get_mirror_mount_point(vehicle_config: dict, side: str = "left") -> tuple:
    """
    从车辆配置中获取后视镜安装基准点坐标。

    参数:
        vehicle_config: vehicles.yaml 中某车型的完整配置
        side: 'left'（驾驶员侧, LEFT=-X）或 'right'（副驾驶侧, RIGHT=+X）

    返回:
        (x, y, z) 安装基准点世界坐标
    """
    mount = vehicle_config["mirror_mount"][side]
    return tuple(mount)


# ========== 镜面中心偏移 ==========


def get_mirror_glass_center(
    mount_point: tuple, offsets: dict, side: str = "left"
) -> tuple:
    """
    从安装基准点计算镜面玻璃中心的世界坐标。

    偏移方向：
        arm_length → 向车外侧（LEFT 侧更负 X，RIGHT 侧更正 X）
        arm_forward → 略向 FORWARD (+Y)
        glass_height → 略向 UP (+Z)
    """
    mx, my, mz = mount_point

    lateral_sign = -1 if side == "left" else +1  # LEFT=-X, RIGHT=+X
    glass_x = mx + lateral_sign * offsets["arm_length"]
    glass_y = my + offsets["arm_forward"]  # 略向 FORWARD
    glass_z = mz + offsets["glass_height"]  # 略向 UP

    return (glass_x, glass_y, glass_z)


# ========== 镜面几何生成 ==========


def _get_offset_category(mirror_type_key: str) -> str:
    """根据镜面类型确定使用哪组偏移参数（standard 或 towing）。"""
    if mirror_type_key.startswith("towing") or mirror_type_key.startswith("electric"):
        return "towing"
    return "standard"


def create_mirror_glass(
    width: float = 0.17,
    height: float = 0.11,
    corner_radius: float = 0.025,
    bevel_segments: int = 8,
    curvature_radius: float = 0,
    is_circular: bool = False,
    diameter: float = 0.065,
    name: str = "Mirror_Glass",
) -> "bpy.types.Object":
    """
    生成真实形状的后视镜镜面。

    支持两种形状：
    - 圆角矩形（大部分镜面类型）：Plane → Bevel → [Subdivision + Cast]
    - 圆形（吸附式盲点镜）：Circle → [Subdivision + Cast]

    参数:
        width: 镜面宽度（米），圆角矩形用
        height: 镜面高度（米），圆角矩形用
        corner_radius: 圆角半径（米）
        bevel_segments: 每个圆角的分段数
        curvature_radius: 曲率半径(m)，0=平面镜，>0=凸面镜
        is_circular: True 则创建圆形镜面（忽略 width/height）
        diameter: 圆形镜面直径（米），仅 is_circular=True 时有效
        name: Blender 对象名称

    返回:
        Blender 对象
    """
    if is_circular:
        # 圆形镜面（吸附式盲点镜）
        bpy.ops.mesh.primitive_circle_add(
            vertices=32, radius=diameter / 2, fill_type="NGON"
        )
        obj = bpy.context.active_object
        obj.name = name
        characteristic_size = diameter
    else:
        # 圆角矩形镜面
        bpy.ops.mesh.primitive_plane_add(size=1)
        obj = bpy.context.active_object
        obj.name = name
        obj.scale = (width, height, 1)
        bpy.ops.object.transform_apply(scale=True)

        # 添加圆角
        bevel = obj.modifiers.new("Bevel", "BEVEL")
        bevel.width = corner_radius
        bevel.segments = bevel_segments
        bevel.affect = "VERTICES"
        bpy.ops.object.modifier_apply(modifier="Bevel")

        characteristic_size = max(width, height)

    # 凸面镜处理：细分 + 球面化
    if curvature_radius > 0:
        # 细分以获得足够的顶点（最少 16×16）
        subdiv = obj.modifiers.new("Subdiv", "SUBSURF")
        subdiv.levels = 4  # 2^4 = 16 subdivisions per edge
        bpy.ops.object.modifier_apply(modifier="Subdiv")

        # 球面化
        cast = obj.modifiers.new("Spherize", "CAST")
        cast.cast_type = "SPHERE"
        cast.factor = characteristic_size / (2 * curvature_radius)
        cast.size = characteristic_size
        cast.use_radius_as_size = True
        bpy.ops.object.modifier_apply(modifier="Spherize")

    return obj


def _parse_mirror_type_params(mirror_type_config: dict) -> dict:
    """
    从 mirrors.yaml 的镜面类型配置中提取 create_mirror_glass() 所需的参数。

    处理范围值（取中值）和圆形/矩形形状差异。
    """
    params = {}

    # 判断是否为圆形镜面
    if "diameter_mm" in mirror_type_config:
        params["is_circular"] = True
        d = mirror_type_config["diameter_mm"]
        params["diameter"] = (
            (d[0] + d[1]) / 2 / 1000 if isinstance(d, list) else d / 1000
        )
    else:
        params["is_circular"] = False
        params["width"] = mirror_type_config["width_mm"] / 1000
        params["height"] = mirror_type_config["height_mm"] / 1000
        params["corner_radius"] = mirror_type_config.get("corner_radius_mm", 25) / 1000

    # 曲率半径
    cr = mirror_type_config.get("curvature_radius_mm")
    if cr is None:
        params["curvature_radius"] = 0  # 平面镜
    elif isinstance(cr, list):
        params["curvature_radius"] = (cr[0] + cr[1]) / 2 / 1000  # 范围取中值
    else:
        params["curvature_radius"] = cr / 1000

    return params


# ========== 法向量计算 ==========


def calculate_mirror_orientation(
    glass_center: tuple, eye_point: tuple, target_point: tuple
) -> "mathutils.Euler":
    """
    计算后视镜的朝向旋转角，使其能将 target_point 的像反射到 eye_point。

    原理：反射定律 → 镜面法向量 = normalize(到眼点方向 + 到目标方向)

    参数:
        glass_center: 镜面中心世界坐标 (x,y,z)
        eye_point: 驾驶员眼点世界坐标 (x,y,z)
        target_point: 希望在镜中看到的目标点 (x,y,z)

    返回:
        Blender 欧拉角 (XYZ)
    """
    glass = mathutils.Vector(glass_center)
    eye = mathutils.Vector(eye_point)
    target = mathutils.Vector(target_point)

    to_eye = (eye - glass).normalized()
    to_target = (target - glass).normalized()

    # 镜面法向量 = 两个方向的角平分线
    mirror_normal = (to_eye + to_target).normalized()

    # Blender 平面默认法向量是 +Z（朝上）
    # 计算从 +Z 旋转到 mirror_normal 所需的旋转
    default_normal = mathutils.Vector((0, 0, 1))
    rotation = default_normal.rotation_difference(mirror_normal)
    euler = rotation.to_euler("XYZ")

    return euler


# ========== 材质 ==========


def create_mirror_material(
    name: str = "Mirror_Material",
    color: tuple = (0.9, 0.9, 0.92, 1.0),
    roughness: float = 0.0,
) -> "bpy.types.Material":
    """创建完美镜面反射材质（Cycles 专用）。"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    glossy = nodes.new("ShaderNodeBsdfGlossy")

    glossy.inputs["Roughness"].default_value = roughness
    glossy.inputs["Color"].default_value = color

    links.new(glossy.outputs["BSDF"], output.inputs["Surface"])
    return mat


# ========== 验证 ==========


def validate_mirror_position(
    mirror_obj: "bpy.types.Object", vehicle_config: dict, side: str = "left"
) -> bool:
    """验证后视镜位置是否合理。"""
    loc = mirror_obj.location
    half_w = vehicle_config["dimensions"]["body_width"] / 2

    checks = []

    # 检查1：镜面必须在车身外侧
    if side == "left":
        checks.append(("镜面在车身左侧外 (LEFT)", loc.x < -half_w))
    else:
        checks.append(("镜面在车身右侧外 (RIGHT)", loc.x > half_w))

    # 检查2：镜面高度在合理范围
    checks.append(("镜面高度合理 (0.8~1.8m)", 0.8 < loc.z < 1.8))

    # 检查3：纵向位置在A柱附近
    checks.append(("镜面纵向位置合理 (Y: -1.0~0.2)", -1.0 < loc.y < 0.2))

    all_pass = True
    for desc, result in checks:
        status = "PASS" if result else "FAIL"
        if not result:
            all_pass = False
        print(f"  [{status}] {desc}  (x={loc.x:.3f}, y={loc.y:.3f}, z={loc.z:.3f})")

    return all_pass


def validate_mirror_orientation(
    mirror_obj: "bpy.types.Object", eye_point: tuple
) -> bool:
    """验证镜面法向量大致朝向驾驶员眼点。"""
    local_normal = mathutils.Vector((0, 0, 1))
    world_normal = mirror_obj.matrix_world.to_3x3() @ local_normal

    to_eye = (mathutils.Vector(eye_point) - mirror_obj.location).normalized()
    angle = math.degrees(world_normal.angle(to_eye))

    ok = angle < 60
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] 镜面朝向眼点 (夹角={angle:.1f}°, 要求<60°)")
    return ok


# ========== 主入口：创建完整后视镜总成 ==========


def create_mirror_assembly(
    vehicle_key: str = "suv",
    mirror_type_key: str = "standard_convex",
    side: str = "left",
    eye_point: tuple | None = None,
    target_point: tuple = (0, -20, 0.5),
    vehicles_config: dict | None = None,
    mirrors_config: dict | None = None,
) -> tuple:
    """
    创建简化后视镜总成：Empty（安装锚点）+ Mirror_Glass（反射镜面）。

    参数:
        vehicle_key: vehicles.yaml 中的车型键名（如 'suv', 'pickup'）
        mirror_type_key: mirrors.yaml 中的镜面类型键名（如 'standard_convex'）
        side: 'left' 或 'right'
        eye_point: 驾驶员眼点，None 则从 vehicles.yaml 读取
        target_point: 目标点，默认车正后方 20m 离地 0.5m
        vehicles_config: 可选，预加载的车辆配置
        mirrors_config: 可选，预加载的镜面配置

    返回:
        (assembly_empty, glass_obj) 元组
    """
    # 加载配置
    if vehicles_config is None:
        vehicles_config = load_vehicles_config()
    if mirrors_config is None:
        mirrors_config = load_mirrors_config()

    vehicle = vehicles_config["vehicles"][vehicle_key]
    mirror_type = mirrors_config["mirror_types"][mirror_type_key]
    offsets = mirrors_config["mirror_offsets"][_get_offset_category(mirror_type_key)]

    side_label = "L" if side == "left" else "R"

    # --- Step 1: 安装基准点 ---
    mount_point = get_mirror_mount_point(vehicle, side)

    # --- Step 2: 创建 Empty 锚点 ---
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=mount_point)
    assembly = bpy.context.active_object
    assembly.name = f"Mirror_Assembly_{side_label}"
    assembly.empty_display_size = 0.05

    # --- Step 3: 创建镜面 ---
    glass_params = _parse_mirror_type_params(mirror_type)
    glass = create_mirror_glass(
        name=f"Mirror_Glass_{side_label}",
        **glass_params,
    )

    # --- Step 4: 设置父子关系并局部偏移 ---
    glass.parent = assembly

    lateral_sign = -1 if side == "left" else +1  # LEFT=-X, RIGHT=+X
    glass.location = (
        lateral_sign * offsets["arm_length"],  # 向车外侧
        offsets["arm_forward"],  # 略向 FORWARD (+Y)
        offsets["glass_height"],  # 略向 UP (+Z)
    )

    # --- Step 5: 计算并设置法向量朝向 ---
    glass_world_center = get_mirror_glass_center(mount_point, offsets, side)

    if eye_point is None:
        eye_point = tuple(vehicle["eye_point"]["reference"])

    euler = calculate_mirror_orientation(glass_world_center, eye_point, target_point)
    glass.rotation_euler = euler

    # --- Step 6: 赋予反射材质 ---
    mat_config = mirrors_config.get("material", {})
    mat = create_mirror_material(
        name=f"Mirror_Material_{side_label}",
        color=tuple(mat_config.get("glossy_color", [0.9, 0.9, 0.92, 1.0])),
        roughness=mat_config.get("roughness", 0.0),
    )
    glass.data.materials.append(mat)

    # --- Step 7: 确保法向量朝外 ---
    bpy.context.view_layer.objects.active = glass
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")

    # --- Step 8: 验证 ---
    print(f"\n=== 验证 Mirror_{side_label} ({vehicle_key}, {mirror_type_key}) ===")
    validate_mirror_position(glass, vehicle, side)
    validate_mirror_orientation(glass, eye_point)

    return assembly, glass


def setup_cycles_for_mirrors(mirrors_config: dict | None = None):
    """设置 Cycles 渲染参数以支持镜面反射。"""
    if mirrors_config is None:
        mirrors_config = load_mirrors_config()

    cycles = mirrors_config.get("cycles_settings", {})
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.glossy_bounces = cycles.get("glossy_bounces", 8)
    scene.cycles.max_bounces = cycles.get("max_bounces", 12)
    print(
        f"Cycles 设置完成: glossy_bounces={scene.cycles.glossy_bounces}, "
        f"max_bounces={scene.cycles.max_bounces}"
    )


# ========== 便捷函数 ==========


def create_both_mirrors(
    vehicle_key: str = "suv",
    mirror_type_key: str = "standard_convex",
    target_point: tuple = (0, -20, 0.5),
) -> dict:
    """
    为指定车型创建左右两侧后视镜。

    返回:
        {
            'left': (assembly_empty, glass_obj),
            'right': (assembly_empty, glass_obj),
        }
    """
    vehicles_config = load_vehicles_config()
    mirrors_config = load_mirrors_config()

    result = {}
    for side in ("left", "right"):
        result[side] = create_mirror_assembly(
            vehicle_key=vehicle_key,
            mirror_type_key=mirror_type_key,
            side=side,
            target_point=target_point,
            vehicles_config=vehicles_config,
            mirrors_config=mirrors_config,
        )

    setup_cycles_for_mirrors(mirrors_config)
    return result
