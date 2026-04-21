# 后视镜精确建模与定位规范

> 本文档定义后视镜系统在 Blender 中的建模规范，涵盖坐标系约定、安装基准点、镜面几何、法向量计算、材质设置和验证流程。
>
> **参数配置**：`config/mirrors.yaml`、`config/vehicles.yaml`（安装基准点）

---

## 一、设计要点

后视镜建模需要解决以下核心问题：

1. **坐标系对齐**：Blender 原生坐标系（X右/Y前/Z上）与 SAE 汽车工程坐标系（X前/Y右/Z下）的轴向映射
2. **工程锚点定位**：后视镜位置基于 A柱、窗框线、车身宽度等几何参考点推导
3. **镜面法向量**：基于反射定律精确计算，而非硬编码角度
4. **真实形状**：使用圆角多边形/圆形而非简单矩形
5. **简化总成结构**：仅建模安装锚点（Empty）和反射镜面（Glass），不建模镜壳和镜臂

> **设计决策——简化模型：** 本项目的目标是视野覆盖仿真（Cycles 光线追踪），只有镜面参与反射计算。镜壳和镜臂对 FOV 仿真无贡献，且与 AI 生成的车辆模型容易产生穿模。因此采用简化模型：Empty（安装锚点）+ Mirror_Glass（反射镜面），镜面全面积参与反射，无边框遮挡。
>
> **实现状态（2026-03-28）：** 9 种镜面类型已通过 `src/mirror_builder.py` 实现参数化生成。`create_both_mirrors()` 可一键为指定车型创建左右镜面总成。安装点坐标经 Blender 视觉验证，准确落在 A 柱/车门三角窗区域。

---

## 二、坐标系统约定

> 完整坐标系规范详见 [`coordinates.md`](coordinates.md)。以下为快速参考。

- **坐标系**：Blender 原生（X=右, Y=前, Z=上）
- **原点**：前轴中心地面投影 (0, 0, 0)
- **方向常量**：`FORWARD=+Y, REAR=-Y, LEFT=-X, RIGHT=+X, UP=+Z, DOWN=-Z`
- **强制要求**：代码中移动对象时必须用方向常量注释方向含义

---

### 三、后视镜安装基准点定义

#### 3.1 安装基准点的工程含义

后视镜**安装基准点（Mirror Mount Point）**是镜臂与车门/A柱的连接点，是整个后视镜总成的空间定位锚点。所有镜面位置、角度都从此点推导。

#### 3.2 安装基准点坐标公式

```python
def get_mirror_mount_point(vehicle_params, side='left'):
    """
    计算后视镜安装基准点坐标。

    参数:
        vehicle_params: 车辆参数字典，必须包含：
            - 'body_width': 车身宽度(m)
            - 'a_pillar_setback': A柱相对前轴的后退量(m)
            - 'window_sill_height': 窗框下沿离地高度(m)
        side: 'left'（驾驶员侧）或 'right'（副驾驶侧）

    返回:
        (x, y, z) 安装基准点世界坐标
    """
    # --- X 横向位置 ---
    # 安装在车身侧面，略内缩于车身最宽处
    half_width = vehicle_params['body_width'] / 2
    x_offset = half_width - 0.02  # 内缩约2cm（安装在门板/A柱上）

    if side == 'left':
        x = -x_offset   # 驾驶员侧 = LEFT = 负X方向
    else:
        x = +x_offset   # 副驾驶侧 = RIGHT = 正X方向

    # --- Y 纵向位置 ---
    # 位于A柱区域，在前轴后方（REAR方向 = 负Y）
    y = -(vehicle_params['a_pillar_setback'])

    # --- Z 垂直位置 ---
    # 窗框下沿高度
    z = vehicle_params['window_sill_height']

    return (x, y, z)
```

#### 3.3 各车型安装基准点参考值

| 参数 | 皮卡 (Hilux) | SUV (CR-V) | 旅行车 (Passat) | A级小车 (Polo) |
|------|:---:|:---:|:---:|:---:|
| 参考车型 | Hilux 2024 | CR-V 2024 | Passat Variant 2024 | Polo 2024 |
| 全长 overall_length (m) | 5.325 | 4.704 | 4.917 | 4.074 |
| 车身宽度 body_width (m) | 1.855 | 1.866 | 1.849 | 1.751 |
| 车高 overall_height (m) | 1.815 | 1.685 | 1.497 | 1.446 |
| 轴距 wheelbase (m) | 3.085 | 2.700 | 2.841 | 2.564 |
| A柱后退量 a_pillar_setback (m) | 0.50 | 0.45 | 0.40 | 0.35 |
| 窗框高度 window_sill_height (m) | 1.35 | 1.25 | 1.05 | 1.00 |
| **左镜安装点 (x, y, z)** | **(-0.908, -0.50, 1.35)** | **(-0.913, -0.45, 1.25)** | **(-0.905, -0.40, 1.05)** | **(-0.856, -0.35, 1.00)** |
| **右镜安装点 (x, y, z)** | **(+0.908, -0.50, 1.35)** | **(+0.913, -0.45, 1.25)** | **(+0.905, -0.40, 1.05)** | **(+0.856, -0.35, 1.00)** |

---

### 四、后视镜几何结构（层级模型）

#### 4.1 总成层级（父子关系）

后视镜采用简化两层结构：

```
Mirror_Assembly_L (Empty, 位于安装基准点，是整个总成的控制点/车身连接锚点)
└── Mirror_Glass_L (Mesh, 反射镜面，全面积参与反射)

Mirror_Assembly_R (Empty, 位于安装基准点)
└── Mirror_Glass_R (Mesh, 反射镜面)
```

> **关键：** `Mirror_Assembly` 是一个 Empty 对象，放在安装基准点，作为车身连接锚点。`Mirror_Glass` 使用**局部坐标**相对于此 Empty 定位。移动/旋转整个后视镜只需操作这个 Empty。切换镜面类型（standard/towing 等）时只需替换 Glass 子对象及其偏移参数，Empty 锚点不变。

#### 4.2 从安装点到镜面中心的偏移

```python
# 镜面中心相对于安装基准点的局部坐标偏移（单位：米）
MIRROR_OFFSETS = {
    'standard': {
        'arm_length': 0.15,     # 镜臂向车外侧伸出长度
        'arm_forward': 0.02,    # 镜臂略微前倾
        'glass_height': 0.05,   # 镜面中心比安装点高
    },
    'towing': {
        'arm_length': 0.25,     # 拖车镜臂更长
        'arm_forward': 0.03,
        'glass_height': 0.08,
    }
}
```

#### 4.3 镜面玻璃中心的世界坐标计算

```python
def get_mirror_glass_center(mount_point, offsets, side='left'):
    """
    从安装基准点计算镜面玻璃中心的世界坐标。
    """
    mx, my, mz = mount_point

    # 镜臂向车外侧伸出（LEFT侧更负X，RIGHT侧更正X）
    lateral_sign = -1 if side == 'left' else +1
    glass_x = mx + lateral_sign * offsets['arm_length']
    glass_y = my + offsets['arm_forward']   # 略向FORWARD
    glass_z = mz + offsets['glass_height']  # 略向UP

    return (glass_x, glass_y, glass_z)
```

---

### 五、后视镜镜面形状（多边形建模）

#### 5.1 为什么不能用简单矩形

真实后视镜镜面是**圆角多边形**，常见形状为"倒D形"或"圆角梯形"。用纯矩形会导致：
- 反射区域计算不准确（角部多出的面积）
- 视觉上不真实，影响论文图片质量
- 凸面镜贴附位置没有参考

#### 5.2 镜面形状生成方法

**推荐方案：使用 Plane + Bevel + Subdivision + Cast 修改器链**

```python
import bpy
import math

def create_mirror_glass(
    width=0.17,           # 镜面宽度（米）
    height=0.11,          # 镜面高度（米）
    corner_radius=0.025,  # 圆角半径（米）
    bevel_segments=8,     # 每个圆角的分段数
    curvature_radius=0,   # 曲率半径(m)，0=平面镜，>0=凸面镜
    name="Mirror_Glass"
):
    """
    生成真实形状的后视镜镜面。

    步骤：
    1. 创建平面 → 缩放到目标尺寸
    2. Bevel 修改器 → 圆角
    3. (凸面镜) Subdivision → Cast 修改器 → 球面化
    """
    # Step 1: 创建基础平面
    bpy.ops.mesh.primitive_plane_add(size=1)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (width, height, 1)
    bpy.ops.object.transform_apply(scale=True)

    # Step 2: 添加圆角
    bevel = obj.modifiers.new('Bevel', 'BEVEL')
    bevel.width = corner_radius
    bevel.segments = bevel_segments
    bevel.affect = 'VERTICES'
    bpy.ops.object.modifier_apply(modifier='Bevel')

    # Step 3: 凸面镜处理
    if curvature_radius > 0:
        # 细分以获得足够的顶点支持曲面
        subdiv = obj.modifiers.new('Subdiv', 'SUBSURF')
        subdiv.levels = 3
        bpy.ops.object.modifier_apply(modifier='Subdiv')

        # 球面化 — factor 控制凸出程度
        cast = obj.modifiers.new('Spherize', 'CAST')
        cast.cast_type = 'SPHERE'
        cast.factor = max(width, height) / (2 * curvature_radius)
        cast.size = max(width, height)
        cast.use_radius_as_size = True
        bpy.ops.object.modifier_apply(modifier='Spherize')

    return obj
```

#### 5.3 各类型镜面尺寸参考

| 镜面类型 | 宽度 (mm) | 高度 (mm) | 圆角 (mm) | 曲率半径 (mm) | 形状特征 |
|---------|:---------:|:---------:|:---------:|:------------:|---------|
| 标准平面镜 | 170 | 110 | 25 | ∞ (平面) | 圆角矩形 |
| 标准凸面镜 | 170 | 110 | 25 | 1000~1400 | 圆角矩形，外凸 |
| 吸附式小凸面镜 | Ø60~75 | (圆形) | — | 400~600 | 正圆形 |
| 拖车加长镜（主镜） | 200 | 140 | 20 | 1000~1200 | 偏大圆角矩形 |
| 拖车加长镜（广角副镜） | 200 | 80 | 15 | 400~600 | 扁长圆角矩形 |
| 电动升降镜（主镜） | 190 | 130 | 20 | 1200 | 圆角矩形 |
| 电动升降镜（副镜） | 190 | 70 | 15 | 500 | 扁长，可上下移动 |

> **法规参考：** FMVSS 111 要求凸面镜曲率半径 889~1651mm；最小反光面积 ≥126cm²；欧洲 UN R46 对拖车镜有额外视野覆盖要求。

---

### 六、后视镜角度与法向量

#### 6.1 镜面法向量的工程含义

镜面的**法向量（Normal）**必须指向"能照到驾驶员眼睛的方向"。这不是简单的"朝向车内"，而是需要基于反射定律精确计算。

#### 6.2 Blender 平面默认法向量朝上（关键注意事项）

**这是之前最大的坑：** `bpy.ops.mesh.primitive_plane_add()` 创建的平面默认法向量是 **+Z（朝上）**。如果不旋转就当镜面，镜子会"朝天花板照"。

#### 6.3 镜面朝向的计算方法（基于反射定律）

```python
import mathutils
import math

def calculate_mirror_orientation(glass_center, eye_point, target_point):
    """
    计算后视镜的朝向旋转角，使其能将 target_point 的像反射到 eye_point。

    原理：反射定律 → 入射角 = 反射角
          镜面法向量 = normalize(到眼点方向 + 到目标方向)

    参数:
        glass_center: 镜面中心世界坐标 (x,y,z)
        eye_point:    驾驶员眼点世界坐标 (x,y,z)
        target_point: 希望在镜中看到的目标点 (x,y,z)
                      通常取车正后方 20m、地面高度 0.5m 处
    返回:
        Blender 欧拉角 (XYZ)
    """
    glass  = mathutils.Vector(glass_center)
    eye    = mathutils.Vector(eye_point)
    target = mathutils.Vector(target_point)

    # 从镜面中心指向眼点和目标的单位向量
    to_eye    = (eye - glass).normalized()
    to_target = (target - glass).normalized()

    # 镜面法向量 = 两个方向的角平分线
    mirror_normal = (to_eye + to_target).normalized()

    # Blender 平面默认法向量是 +Z
    # 计算从 +Z 旋转到 mirror_normal 所需的旋转
    default_normal = mathutils.Vector((0, 0, 1))
    rotation = default_normal.rotation_difference(mirror_normal)
    euler = rotation.to_euler('XYZ')

    return euler


# === 使用示例（皮卡，左镜）===
# 眼点：驾驶员头部位置（LEFT侧、略低于镜面、略前）
eye   = (-0.35, -0.10, 1.20)
# 镜面中心：安装点 + 镜臂偏移
glass = (-1.05, -0.48, 1.40)
# 目标：车正后方 20m、道路中心、离地0.5m
target = (0, -20, 0.5)

euler = calculate_mirror_orientation(glass, eye, target)
# 将 euler 赋值给镜面对象的 rotation_euler
```

> **强制要求：** 不要硬编码角度！始终使用此函数根据眼点和目标点动态计算。硬编码角度在更换车型或眼点时会完全失效。

---

### 七、镜面材质设置

```python
def create_mirror_material(name="Mirror_Material"):
    """创建完美镜面反射材质（Cycles 专用）。"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()

    output = nodes.new('ShaderNodeOutputMaterial')
    glossy = nodes.new('ShaderNodeBsdfGlossy')

    glossy.inputs['Roughness'].default_value = 0.0       # 完美镜面
    glossy.inputs['Color'].default_value = (0.9, 0.9, 0.92, 1.0)  # 略蓝，模拟真实镜面

    links.new(glossy.outputs['BSDF'], output.inputs['Surface'])
    return mat
```

**材质赋予注意：**
- 反射材质仅赋予 `Mirror_Glass` 对象（简化模型中唯一的 Mesh）
- 反射面必须是**法向量朝外的那一面**（Blender: Mesh > Normals > Recalculate Outside）

**Cycles 渲染关键设置：**
```python
bpy.context.scene.cycles.glossy_bounces = 8   # 反射弹射次数（默认值太低会导致镜中画面变黑）
bpy.context.scene.cycles.max_bounces = 12
```

---

### 八、后视镜参考模型（用于校验）

构建前，建议从 Sketchfab 搜索并下载免费参考模型：

```python
# 推荐搜索关键词
reference_searches = [
    "car side mirror",
    "vehicle rearview mirror",
    "truck towing mirror",
    "car wing mirror low poly"
]
# 下载后保存到 models/reference_mirrors/
# 用途：测量参考尺寸（镜面宽高、镜臂长度）与上文第四节参考表对比校验
```

> **注意导入模型的单位：** Sketchfab 模型可能使用厘米或英寸。正常汽车长约 4~5m，如果导入后只有 0.04m，需要 ×100 缩放。

---

### 九、验证检查清单

#### 9.1 位置验证

```python
def validate_mirror_position(mirror_obj, vehicle_params, side='left'):
    """验证后视镜位置是否合理。"""
    loc = mirror_obj.location
    half_w = vehicle_params['body_width'] / 2

    checks = []

    # 检查1：镜面必须在车身外侧
    if side == 'left':
        checks.append(("镜面在车身左侧外", loc.x < -half_w))
    else:
        checks.append(("镜面在车身右侧外", loc.x > half_w))

    # 检查2：镜面高度在合理范围（0.8m ~ 1.8m）
    checks.append(("镜面高度合理 (0.8~1.8m)", 0.8 < loc.z < 1.8))

    # 检查3：纵向位置在A柱附近（前轴后方0~1m）
    checks.append(("镜面纵向位置合理 (Y: -1.0~0.2)", -1.0 < loc.y < 0.2))

    for desc, result in checks:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {desc}  (x={loc.x:.3f}, y={loc.y:.3f}, z={loc.z:.3f})")

    return all(r for _, r in checks)
```

#### 9.2 朝向验证

```python
def validate_mirror_orientation(mirror_obj, eye_point):
    """验证镜面法向量大致朝向驾驶员眼点。"""
    local_normal = mathutils.Vector((0, 0, 1))
    world_normal = mirror_obj.matrix_world.to_3x3() @ local_normal

    to_eye = (mathutils.Vector(eye_point) - mirror_obj.location).normalized()
    angle = math.degrees(world_normal.angle(to_eye))

    ok = angle < 60
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] 镜面朝向眼点 (夹角={angle:.1f}°, 要求<60°)")
    return ok
```

#### 9.3 渲染快速验证（反射功能性测试）

构建完成后，执行一次简单渲染验证：
1. 将摄像机放在驾驶员眼点，朝向后视镜
2. 在镜面后方放一个红色球体（车后方 5m 处）
3. 渲染一帧，确认红球的像出现在镜面中
4. 如果镜中看不到红球 → 法向量方向错误或角度计算有误

---

### 十、补充注意事项

#### 10.1 左右镜不是简单镜像
- 很多市场：驾驶员侧 = 平面镜，副驾驶侧 = 凸面镜
- 欧洲市场可能使用非球面镜（内侧平面 + 外侧渐变曲率）
- 拖车加长镜通常外挂，不替换原厂镜面

#### 10.2 凸面镜的网格细分精度
- 平面镜：最少 4×4 细分即可
- 凸面镜：最少 16×16 细分（否则反射图像出现棱面感/锯齿）
- Cycles 光线追踪在几何精度不足时产生失真

#### 10.3 凸面镜的视野放大效果
```
有效FOV ≈ 2 × arctan(mirror_size / (2 × curvature_radius)) × 放大系数
```
曲率半径越小 → 视野越宽 → 物体越小 → 失真越大。凸面镜的像是**虚像**，在镜面后方，比实物小。

#### 10.4 单位一致性
Blender 默认单位是**米**，与汽车工程完美匹配。但导入外部模型时务必检查缩放比例。

---

### 十一、完整构建流程

```
Step 1:  定义车辆参数（车身宽度、A柱位置、窗框高度）
Step 2:  用 get_mirror_mount_point() 计算安装基准点
Step 3:  创建 Empty 对象 Mirror_Assembly，放置在安装基准点（车身连接锚点）
Step 4:  用 create_mirror_glass() 生成真实形状镜面（圆角多边形/圆形），设为 Assembly 子对象
Step 5:  用局部坐标偏移定位镜面（MIRROR_OFFSETS）
Step 6:  用 calculate_mirror_orientation() 计算并设置镜面旋转（动态计算，不存储）
Step 7:  赋予 create_mirror_material() 反射材质
Step 8:  运行 validate_mirror_position() + validate_mirror_orientation()
Step 9:  对称创建另一侧后视镜
Step 10: 放置测试球体 + 快速渲染验证反射效果
```

> **重要提醒：** 不要跳过任何步骤。按工程逻辑分步定位和验证。简化模型无需创建镜壳和镜臂。
