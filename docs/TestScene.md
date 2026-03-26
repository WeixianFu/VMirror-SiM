# 测试场景搭建规范（外部环境）

> 本文档定义用于后视镜视野仿真的标准化测试场景，包含道路系统、车道标线、参考标记物等。场景不包含车辆和后视镜（分别由 `VehicleModels.md` 和 `MirrorDesign.md` 负责）。
>
> **参数配置**：`config/test_scene.yaml`

---

## 一、场景设计原则

1. **真实比例**：所有尺寸以米为单位，符合真实道路几何参数
2. **参数化**：道路宽度、车道数、标线间距等均为可调参数
3. **功能导向**：场景元素服务于视野仿真分析，不追求视觉华丽
4. **轻量化**：几何体尽量简洁，避免不必要的面数影响渲染性能
5. **坐标系一致**：沿用项目统一坐标系（X=横向, Y=纵向/车头方向, Z=垂直向上，原点=前轴中心地面投影）

---

### 二、坐标系与空间范围

#### 2.1 坐标系约定（与 MirrorDesign.md 一致）

```python
# ========== 坐标系映射常量 ==========
FORWARD = "+Y"    # 车头方向
REAR    = "-Y"    # 车尾方向
LEFT    = "-X"    # 驾驶员侧（左舵车）
RIGHT   = "+X"    # 副驾驶侧（左舵车）
UP      = "+Z"    # 向上
DOWN    = "-Z"    # 向下
```

#### 2.2 场景空间范围

```python
SCENE_BOUNDS = {
    'x_range': (-15, 15),    # 横向：左右各15m（覆盖多车道 + 路肩）
    'y_range': (-80, 30),    # 纵向：车前方30m，车后方80m（拖车+后方视野范围）
    'z_range': (0, 5),       # 垂直：地面到5m（覆盖房车高度+参考柱）
}
```

> **设计依据：** 后视镜主要观察车辆后方/侧后方，因此 -Y 方向（REAR）需要更大范围。UN R46 法规要求后视镜覆盖车后 20m 范围内的可视区域，加上大型房车长度约 8m + 连接杆 ~2m，总计后方约 30m 范围是关键区域。额外延伸到 80m 用于远方消失点视觉效果。

---

### 三、道路系统

#### 3.1 道路参数定义

```python
ROAD_PARAMS = {
    # --- 车道参数（参考欧洲/中国标准）---
    'lane_width': 3.75,           # 单车道宽度(m)，高速公路标准
    'num_lanes': 2,               # 单向车道数（双向共4车道）
    'median_width': 1.5,          # 中央分隔带宽度(m)
    'shoulder_width': 3.0,        # 路肩宽度(m)
    'road_length': 110,           # 道路总长度(m)，覆盖 y_range

    # --- 标线参数 ---
    'line_width': 0.15,           # 标线宽度(m)
    'dash_length': 6.0,           # 虚线段长度(m)
    'dash_gap': 9.0,              # 虚线间隔(m)
    'edge_line_width': 0.20,      # 边缘线宽度(m)

    # --- 路面参数 ---
    'road_surface_color': (0.15, 0.15, 0.15, 1.0),  # 深灰沥青色
    'shoulder_color': (0.25, 0.25, 0.22, 1.0),       # 略浅灰（路肩）
    'line_color_white': (0.95, 0.95, 0.95, 1.0),     # 白色标线
    'line_color_yellow': (0.95, 0.85, 0.15, 1.0),    # 黄色标线（中央线）
}
```

#### 3.2 道路几何创建

```python
import bpy
import bmesh

def create_road_system(params=None):
    """
    创建完整的道路系统，包含路面、车道线、路肩。

    道路沿 Y 轴铺设（FORWARD/REAR 方向），车辆行驶方向为 +Y。
    道路中心线对齐 X=0（车辆初始位置在右侧车道中央）。
    """
    if params is None:
        params = ROAD_PARAMS

    lw = params['lane_width']
    nl = params['num_lanes']
    mw = params['median_width']
    sw = params['shoulder_width']
    road_len = params['road_length']

    # 计算道路总宽度
    carriageway_width = nl * lw  # 单侧车行道宽度
    total_width = 2 * carriageway_width + mw + 2 * sw

    # --- 1) 路面主体 ---
    # 车辆在右侧车道（+X 侧），道路中心线 X=0
    road_collection = create_collection("Road_System")

    # 主路面（两侧车行道 + 中央分隔带）
    road_width = 2 * carriageway_width + mw
    create_road_plane(
        name="Road_Surface",
        width=road_width,
        length=road_len,
        center_y=-road_len/2 + 30,  # 前方30m，后方80m
        color=params['road_surface_color'],
        collection=road_collection
    )

    # 左路肩
    create_road_plane(
        name="Shoulder_Left",
        width=sw,
        length=road_len,
        center_x=-(road_width/2 + sw/2),
        center_y=-road_len/2 + 30,
        color=params['shoulder_color'],
        collection=road_collection
    )

    # 右路肩
    create_road_plane(
        name="Shoulder_Right",
        width=sw,
        length=road_len,
        center_x=(road_width/2 + sw/2),
        center_y=-road_len/2 + 30,
        color=params['shoulder_color'],
        collection=road_collection
    )

    # --- 2) 车道标线 ---
    create_lane_markings(params, road_collection)

    return road_collection


def create_road_plane(name, width, length, center_x=0, center_y=0,
                      color=(0.15, 0.15, 0.15, 1.0), collection=None):
    """创建一个道路平面。"""
    bpy.ops.mesh.primitive_plane_add(size=1, location=(center_x, center_y, 0.001))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (width, length, 1)
    bpy.ops.object.transform_apply(scale=True)

    # 路面材质
    mat = bpy.data.materials.new(f"Mat_{name}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = 0.85  # 粗糙沥青
    obj.data.materials.append(mat)

    if collection:
        move_to_collection(obj, collection)

    return obj
```

#### 3.3 车道标线创建

```python
def create_lane_markings(params, collection):
    """
    创建所有车道标线。

    标线布局（X轴方向，从左到右）:
    |路肩|边缘线|车道2|车道线|车道1|边缘线|中央线==中央线|边缘线|车道1|车道线|车道2|边缘线|路肩|
          ↑实线         ↑虚线        ↑双黄实线         ↑虚线        ↑实线
    """
    lw = params['lane_width']
    nl = params['num_lanes']
    mw = params['median_width']
    road_len = params['road_length']
    y_offset = -road_len/2 + 30

    # 中央分隔线（双黄实线）
    create_solid_line(
        name="CenterLine_Left",
        x_pos=-(mw/2 - 0.10),
        y_start=y_offset - road_len/2,
        y_end=y_offset + road_len/2,
        width=params['line_width'],
        color=params['line_color_yellow'],
        collection=collection
    )
    create_solid_line(
        name="CenterLine_Right",
        x_pos=(mw/2 - 0.10),
        y_start=y_offset - road_len/2,
        y_end=y_offset + road_len/2,
        width=params['line_width'],
        color=params['line_color_yellow'],
        collection=collection
    )

    # 车道分隔线（白色虚线）— 各车道之间
    for i in range(1, nl):
        for side_sign in [-1, +1]:  # 左侧(-X)和右侧(+X)
            x_pos = side_sign * (mw/2 + i * lw)
            create_dashed_line(
                name=f"LaneLine_{'L' if side_sign<0 else 'R'}_{i}",
                x_pos=x_pos,
                y_start=y_offset - road_len/2,
                y_end=y_offset + road_len/2,
                width=params['line_width'],
                dash_len=params['dash_length'],
                gap_len=params['dash_gap'],
                color=params['line_color_white'],
                collection=collection
            )

    # 边缘线（白色实线）— 车行道与路肩分界
    for side_sign in [-1, +1]:
        x_pos = side_sign * (mw/2 + nl * lw)
        create_solid_line(
            name=f"EdgeLine_{'L' if side_sign<0 else 'R'}",
            x_pos=x_pos,
            y_start=y_offset - road_len/2,
            y_end=y_offset + road_len/2,
            width=params['edge_line_width'],
            color=params['line_color_white'],
            collection=collection
        )


def create_solid_line(name, x_pos, y_start, y_end, width, color, collection):
    """创建一条实线标线。"""
    length = abs(y_end - y_start)
    y_center = (y_start + y_end) / 2
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x_pos, y_center, 0.002))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (width, length, 1)
    bpy.ops.object.transform_apply(scale=True)

    mat = bpy.data.materials.new(f"Mat_{name}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = 0.5  # 标线比路面光滑
    obj.data.materials.append(mat)

    if collection:
        move_to_collection(obj, collection)
    return obj


def create_dashed_line(name, x_pos, y_start, y_end, width,
                       dash_len, gap_len, color, collection):
    """创建一条虚线标线（由多个小矩形段组成）。"""
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

        mat = bpy.data.materials.new(f"Mat_{name}")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.5
        obj.data.materials.append(mat)

        if collection:
            move_to_collection(obj, collection)

        y += cycle_len
        idx += 1
```

#### 3.4 车辆初始位置定义

```python
# 车辆放置在右侧（+X侧）第一车道中央
# 车辆原点=前轴中心地面投影=(0,0,0)
# 因此道路需要适配：车辆横向位于右侧第一车道
VEHICLE_LANE_POSITION = {
    'x': ROAD_PARAMS['median_width']/2 + ROAD_PARAMS['lane_width']/2,
    # = 0.75 + 1.875 = 2.625m（道路中心线右侧2.625m处）
    'y': 0,   # 前轴在原点
    'z': 0,   # 地面
}
```

> **注意：** 车辆模型原点在 (0,0,0)。如果需要将车辆放在特定车道，应移动车辆到 `VEHICLE_LANE_POSITION`，或者保持车辆在原点并相应偏移道路中心线。**推荐后者**：将道路系统整体沿 -X 偏移，使车辆自然位于右侧第一车道中央。

```python
def get_road_offset_for_vehicle():
    """
    计算道路系统的 X 偏移量，使车辆原点(0,0,0)正好在右侧第一车道中央。
    """
    lane_center_from_road_center = (
        ROAD_PARAMS['median_width']/2 + ROAD_PARAMS['lane_width']/2
    )
    return -lane_center_from_road_center
    # 道路整体向 LEFT 偏移，车辆就在右侧车道中央了
```

---

### 四、地面与环境

#### 4.1 周围地面

```python
def create_ground_plane():
    """
    创建道路周围的地面（草地/泥地效果）。
    尺寸远大于道路，提供地平线背景。
    """
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, -25, 0))
    obj = bpy.context.active_object
    obj.name = "Ground_Plane"

    mat = bpy.data.materials.new("Mat_Ground")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (0.25, 0.35, 0.15, 1.0)  # 草地绿
    bsdf.inputs['Roughness'].default_value = 0.95
    obj.data.materials.append(mat)

    return obj
```

> **Z-fighting 防护：** 道路面 Z=0.001，标线 Z=0.002，地面 Z=0。确保渲染时不会出现闪烁。

#### 4.2 天空与光照

```python
def setup_scene_lighting():
    """
    设置测试场景的光照环境。
    使用 HDRI 天空或 Sun light 模拟户外日光条件。
    """
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'

    # --- 方案 A：Sun Light（轻量，推荐仿真用）---
    bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))
    sun = bpy.context.active_object
    sun.name = "Sun_Light"
    sun.data.energy = 5.0
    # 太阳角度：模拟上午10点，从右前方照射
    sun.rotation_euler = (
        math.radians(45),    # 仰角 45°
        math.radians(0),
        math.radians(-30),   # 方位角（略偏右前方）
    )

    # --- 世界背景 ---
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (0.52, 0.67, 0.85, 1.0)  # 浅蓝天空
    bg.inputs['Strength'].default_value = 1.0

    # --- 方案 B：PolyHaven HDRI（可选，更真实）---
    # 如需更真实的天空反射（后视镜中能看到天空环境），
    # 使用 download_polyhaven_asset 下载 HDRI：
    # search_polyhaven_assets(query="road", category="hdris")
    # 推荐：kloofendal_48d_partly_cloudy / rural_asphalt_road

    return sun
```

---

### 五、可视区域参考标记系统

#### 5.1 设计目的

在车辆后方/侧后方布置一系列标记物，用于：
1. **渲染验证**：通过后视镜观察哪些标记物可见/不可见
2. **量化分析**：标记物的可见性直接映射为可视区域边界
3. **法规校验**：与 UN R46 / FMVSS 111 要求的可视区域对比

#### 5.2 地面网格标记（Ground Grid Markers）

```python
def create_ground_grid_markers(collection=None):
    """
    在车辆后方地面上创建网格标记点，用于标注可视区域。

    网格布局：
    - 横向(X)：从 -15m 到 +15m，间距 2.5m
    - 纵向(Y)：从 -5m 到 -40m（车后方），间距 5m
    - 每个标记点是一个扁平的圆盘 + 数字标签

    颜色编码（后续渲染后可自动判断可见性）：
    - 奇数行：红色圆盘
    - 偶数行：蓝色圆盘
    """
    grid_collection = create_collection("Ground_Grid_Markers")

    x_positions = [x * 2.5 for x in range(-6, 7)]   # -15m 到 +15m
    y_positions = [y * -5 for y in range(1, 9)]       # -5m 到 -40m

    marker_radius = 0.3  # 标记圆盘半径(m)

    for yi, y in enumerate(y_positions):
        for xi, x in enumerate(x_positions):
            color = (0.9, 0.15, 0.15, 1.0) if yi % 2 == 0 else (0.15, 0.15, 0.9, 1.0)

            bpy.ops.mesh.primitive_cylinder_add(
                radius=marker_radius,
                depth=0.01,
                location=(x, y, 0.003)
            )
            marker = bpy.context.active_object
            marker.name = f"GridMarker_X{x:+.1f}_Y{y:+.1f}"

            mat = bpy.data.materials.new(f"Mat_Marker_{xi}_{yi}")
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get('Principled BSDF')
            bsdf.inputs['Base Color'].default_value = color
            bsdf.inputs['Roughness'].default_value = 0.3  # 略反光，便于镜中识别
            marker.data.materials.append(mat)

            if grid_collection:
                move_to_collection(marker, grid_collection)

    return grid_collection
```

#### 5.3 垂直参考柱（Vertical Reference Poles）

```python
def create_reference_poles(collection=None):
    """
    在关键位置放置垂直参考柱，模拟行人/路桩/交通锥。

    参考柱用途：
    - 高于地面的标记物在后视镜中更容易辨识
    - 可用于验证不同高度的可视性
    - 模拟真实场景中的行人或障碍物

    布局：沿车后方两侧关键位置放置
    """
    pole_collection = create_collection("Reference_Poles")

    # 参考柱位置列表：(x, y, height, color_name)
    pole_positions = [
        # --- UN R46 关键视野点 ---
        # 驾驶员侧后方 10m 处（外侧车道边缘）
        (-3.75, -10, 1.0, "pole_red"),
        # 驾驶员侧后方 20m 处
        (-3.75, -20, 1.0, "pole_red"),
        # 副驾驶侧后方 10m 处
        (+3.75, -10, 1.0, "pole_blue"),
        # 副驾驶侧后方 20m 处
        (+3.75, -20, 1.0, "pole_blue"),

        # --- 近侧盲区测试点 ---
        # 车身紧邻位置（测试近侧盲区）
        (-1.5, -3, 1.0, "pole_yellow"),
        (+1.5, -3, 1.0, "pole_yellow"),

        # --- 房车遮挡后方参考 ---
        # 车后方 15m（中型房车尾部附近）
        (0, -15, 1.0, "pole_green"),
        # 车后方 25m（大型房车尾部后方）
        (0, -25, 1.0, "pole_green"),

        # --- 车道两侧远方参考 ---
        (-7.5, -30, 1.5, "pole_white"),
        (+7.5, -30, 1.5, "pole_white"),
    ]

    POLE_COLORS = {
        'pole_red':    (0.9, 0.1, 0.1, 1.0),
        'pole_blue':   (0.1, 0.1, 0.9, 1.0),
        'pole_yellow': (0.95, 0.85, 0.1, 1.0),
        'pole_green':  (0.1, 0.8, 0.2, 1.0),
        'pole_white':  (0.9, 0.9, 0.9, 1.0),
    }

    pole_radius = 0.05  # 柱子半径 5cm

    for x, y, h, color_name in pole_positions:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=pole_radius,
            depth=h,
            location=(x, y, h/2)  # 底部在地面
        )
        pole = bpy.context.active_object
        pole.name = f"Pole_X{x:+.1f}_Y{y:+.1f}"

        mat = bpy.data.materials.new(f"Mat_{pole.name}")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = POLE_COLORS[color_name]
        bsdf.inputs['Roughness'].default_value = 0.4
        pole.data.materials.append(mat)

        if pole_collection:
            move_to_collection(pole, pole_collection)

    return pole_collection
```

#### 5.4 距离刻度标尺（Distance Scale Rulers）

```python
def create_distance_rulers(collection=None):
    """
    在道路边缘创建距离标尺，每 5m 一个刻度板。
    便于俯视图和第一人称视角中快速判断距离。
    """
    ruler_collection = create_collection("Distance_Rulers")

    # 在道路右侧边缘放置距离牌
    edge_x = ROAD_PARAMS['median_width']/2 + \
             ROAD_PARAMS['num_lanes'] * ROAD_PARAMS['lane_width'] + \
             ROAD_PARAMS['shoulder_width'] + 0.5  # 路肩外 0.5m

    for dist in range(5, 45, 5):
        y = -dist  # 车后方

        # 距离标牌（竖立的薄板）
        bpy.ops.mesh.primitive_plane_add(
            size=1,
            location=(edge_x, y, 0.75)
        )
        board = bpy.context.active_object
        board.name = f"DistBoard_{dist}m"
        board.scale = (0.8, 0.01, 0.5)  # 宽0.8m, 薄, 高0.5m
        board.rotation_euler = (math.radians(90), 0, 0)  # 竖立面向道路
        bpy.ops.object.transform_apply(scale=True)

        # 交替黑白色便于辨识
        color = (0.1, 0.1, 0.1, 1.0) if dist % 10 == 0 else (0.95, 0.95, 0.95, 1.0)
        mat = bpy.data.materials.new(f"Mat_Dist_{dist}m")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = color
        board.data.materials.append(mat)

        if ruler_collection:
            move_to_collection(board, ruler_collection)

    return ruler_collection
```

---

### 六、辅助工具函数

```python
def create_collection(name):
    """创建一个新的 Blender Collection（场景分组）。"""
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def move_to_collection(obj, collection):
    """将对象移动到指定 Collection。"""
    # 从所有当前集合中移除
    for col in obj.users_collection:
        col.objects.unlink(obj)
    # 添加到目标集合
    collection.objects.link(obj)
```

---

### 七、场景层级结构

```
Scene Collection
├── Road_System
│   ├── Road_Surface          (Mesh, 主路面)
│   ├── Shoulder_Left         (Mesh, 左路肩)
│   ├── Shoulder_Right        (Mesh, 右路肩)
│   ├── CenterLine_Left       (Mesh, 中央线左)
│   ├── CenterLine_Right      (Mesh, 中央线右)
│   ├── LaneLine_L_1          (Mesh, 左侧车道虚线)
│   ├── LaneLine_R_1          (Mesh, 右侧车道虚线)
│   ├── EdgeLine_L            (Mesh, 左边缘实线)
│   └── EdgeLine_R            (Mesh, 右边缘实线)
├── Ground_Grid_Markers
│   └── GridMarker_X+0.0_Y-5.0 ... (Mesh, 地面圆盘标记 ×104个)
├── Reference_Poles
│   └── Pole_X-3.8_Y-10.0 ... (Mesh, 参考柱 ×10个)
├── Distance_Rulers
│   └── DistBoard_5m ... (Mesh, 距离标牌 ×8个)
├── Ground_Plane              (Mesh, 地面)
├── Sun_Light                 (Light, 太阳光)
├── [Vehicle_*]               (← 由 VehicleModels.md 创建，不在本 prompt 范围)
├── [Caravan_*]               (← 由总体框架 prompt 创建)
└── [Mirror_Assembly_*]       (← 由 MirrorDesign.md 创建)
```

---

### 八、主控函数：一键创建完整测试场景

```python
import bpy
import math

def build_test_scene(params=None):
    """
    一键创建完整的测试场景。

    调用后场景中将包含：道路系统、地面、光照、参考标记。
    车辆原点 (0,0,0) 位于右侧第一车道中央。
    """
    if params is None:
        params = ROAD_PARAMS

    # 0) 清理场景中的默认对象（保留已有的车辆/镜子）
    for obj in bpy.data.objects:
        if obj.name in ['Cube', 'Light', 'Camera']:
            bpy.data.objects.remove(obj, do_unlink=True)

    # 1) 计算道路偏移使车辆在右侧车道中央
    road_x_offset = get_road_offset_for_vehicle()

    # 2) 创建道路系统
    road = create_road_system(params)
    # 整体偏移道路
    for obj in road.objects:
        obj.location.x += road_x_offset

    # 3) 创建地面
    ground = create_ground_plane()
    ground.location.x += road_x_offset

    # 4) 创建参考标记
    grid = create_ground_grid_markers()
    poles = create_reference_poles()
    rulers = create_distance_rulers()

    # 5) 设置光照
    setup_scene_lighting()

    # 6) 渲染设置
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.cycles.samples = 128
    scene.cycles.glossy_bounces = 8   # 镜面反射弹射次数
    scene.cycles.max_bounces = 12

    print("=" * 50)
    print("测试场景创建完成!")
    print(f"  道路: {params['num_lanes']}×2 车道, 车道宽 {params['lane_width']}m")
    print(f"  车辆位置: 右侧第一车道中央 (0, 0, 0)")
    print(f"  场景范围: Y = -80m ~ +30m")
    print(f"  参考标记: 地面网格 + 垂直柱 + 距离标牌")
    print("=" * 50)


# === 执行 ===
build_test_scene()
```

---

### 九、验证检查清单

#### 9.1 空间验证

```python
def validate_test_scene():
    """验证测试场景的关键指标。"""
    checks = []

    # 检查1：道路面存在
    checks.append(("Road_Surface 存在",
                    "Road_Surface" in bpy.data.objects))

    # 检查2：车辆位置在车道内（X方向）
    road_surface = bpy.data.objects.get("Road_Surface")
    if road_surface:
        # 原点 (0,0,0) 应在路面 X 范围内
        rs_x = road_surface.location.x
        rs_w = road_surface.dimensions.x / 2
        checks.append(("车辆原点在路面范围内",
                        rs_x - rs_w < 0 < rs_x + rs_w))

    # 检查3：标记物存在
    grid_markers = [o for o in bpy.data.objects if o.name.startswith("GridMarker_")]
    checks.append((f"地面标记 ≥50个 (实际{len(grid_markers)})",
                    len(grid_markers) >= 50))

    poles = [o for o in bpy.data.objects if o.name.startswith("Pole_")]
    checks.append((f"参考柱 ≥8个 (实际{len(poles)})",
                    len(poles) >= 8))

    # 检查4：光照存在
    sun = bpy.data.objects.get("Sun_Light")
    checks.append(("Sun_Light 存在", sun is not None))

    # 检查5：Z-fighting 防护
    if road_surface:
        checks.append(("路面高于地面 (Z>0)",
                        road_surface.location.z > 0))

    for desc, result in checks:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {desc}")

    return all(r for _, r in checks)

validate_test_scene()
```

#### 9.2 视觉快速验证

执行完 `build_test_scene()` 后，建议：

1. 按 `Numpad 7`（俯视图）确认道路布局和标记物分布
2. 将摄像机放在 `(0, 0, 50)` 朝下渲染一帧俯视图，确认车道线、标记物正确
3. 将摄像机放在驾驶员眼点位置 `(-0.35, -0.10, 1.20)` 朝前方渲染，确认道路透视效果

---

### 十、预设场景变体

```python
SCENE_PRESETS = {
    'highway': {
        **ROAD_PARAMS,
        'lane_width': 3.75,
        'num_lanes': 2,
        'shoulder_width': 3.0,
        'description': '标准高速公路，适合长途拖车场景'
    },
    'urban': {
        **ROAD_PARAMS,
        'lane_width': 3.25,
        'num_lanes': 2,
        'shoulder_width': 1.5,
        'median_width': 0.5,
        'description': '城市道路，较窄车道和路肩'
    },
    'country_road': {
        **ROAD_PARAMS,
        'lane_width': 3.50,
        'num_lanes': 1,
        'shoulder_width': 1.0,
        'median_width': 0,
        'description': '乡村双向两车道公路，欧洲常见拖车路线'
    },
}

# 使用示例：
# build_test_scene(SCENE_PRESETS['highway'])
# build_test_scene(SCENE_PRESETS['country_road'])
```

---

### 十一、与其他模块的接口约定

| 接口 | 本模块（TestScene）提供 | 其他模块使用 |
|------|----------------------|------------|
| 车辆放置位置 | 保证原点 (0,0,0) 在右侧第一车道中央 | VehicleModels: 车辆原点 = 前轴中心地面投影 = (0,0,0) |
| 路面 Z 高度 | Z = 0.001 | MirrorDesign: 地面参考高度 ≈ 0 |
| 后方范围 | Y = -80m ~ 0 | MirrorDesign: `target_point` 通常取 `(0, -20, 0.5)` |
| 标记物颜色 | 红/蓝/黄/绿/白 | 渲染后分析：通过颜色识别可见标记物 |
| 场景集合命名 | `Road_System`, `Ground_Grid_Markers`, `Reference_Poles`, `Distance_Rulers` | 批量渲染脚本可按集合控制显示/隐藏 |

---

