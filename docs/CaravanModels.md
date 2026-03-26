# 房车模型：AI 3D 生成 Prompt 与校准规范

> 本文档包含 3 种尺寸房车的 AI 3D 模型生成 Prompt、连接几何定义及宽度遮挡分析。
>
> **参数配置**：`config/caravans.yaml`

---

## 通用风格指令（所有房车共享前缀）

```
STYLE PREFIX (prepend to each caravan prompt):

Stylized low-poly 3D model. Clean geometric facets with defined edges.
Flat-shaded surfaces, no complex textures. Soft global illumination on
a neutral light-blue background. Proportions are slightly chibi/compact
(~85% realistic proportions) for visual appeal while maintaining
recognizable caravan silhouette. Clean 3/4 rear view showing the
tow-coupling / A-frame side.
IMPORTANT: The caravan body width is critical for mirror visibility
simulation. Ensure the body sidewalls are clearly defined flat planes
with accurate width representation. The A-frame drawbar and tow
coupling must be visible and correctly proportioned.
```

---

## 房车尺寸 S：紧凑型（Eriba Touring / Knaus Sport 级别）

### Prompt

```
A stylized low-poly 3D model of a compact European touring caravan
(travel trailer), similar in size to an Eriba Touring 310 or Knaus
Sport 400. Single-axle design.

BODY: Clean white body with a fresh mint-green accent stripe running
horizontally along the mid-section. Chibi/compact proportions (~85%
of real-world ratio) maintaining the recognizable small caravan form —
a boxy but gently rounded shell sitting on a single-axle chassis.
The body is composed of flat geometric planes with visible but smooth
facets. Overall shape is a simplified rectangular box with rounded
vertical edges (corner radius ~100mm scale).

FRONT (hitch side): A visible A-frame drawbar extending forward from
the body, tapering to a simplified 50mm ball coupling at the tip.
The A-frame is two converging geometric bars in dark gray / steel
color, meeting at a triangular coupling head. A small jockey wheel
(retracted position) visible near the coupling. Front body panel is
a simple flat surface with a small gas bottle locker hatch detail.

SIDES: Flat geometric sidewalls — the most important surfaces for
mirror simulation. One entry door on the left side (road-side in
LHD countries) rendered as a recessed geometric panel with a
simplified grab handle. One or two small geometric windows with
darkened glass and simplified frames. A thin awning rail line running
along the top edge of the sidewall. The body extends slightly beyond
the wheel arches.

REAR: Simple flat rear panel. Two small geometric taillights
(red rectangles). A rear bumper step. A simplified rear window or
vent detail.

ROOF: Gently curved or flat roof panel with one simplified roof vent
/ skylight (white geometric box). Clean roofline with minimal details.

UNDERCARRIAGE: Single axle with two wheels (one per side), positioned
slightly behind the body center. Simplified leaf-spring suspension
detail. The chassis frame is a simplified dark gray rectangular rail
running the length of the body.

WHEELS: Two compact road tires (one per side) with simplified 5-bolt
steel wheel covers in silver-white. Tire size noticeably smaller than
the tow vehicle.

RENDERING: Clean flat geometric colors, no complex textures. Soft
global illumination. Defined geometric facets. Light-blue studio
background. Subtle soft ground shadow. 3/4 rear isometric view angle
(showing the A-frame/coupling side and one full sidewall).
```

### 生成后校准要点
- 整体长度（含牵引杆）：约 5.0m；车身长度（不含牵引杆）：约 3.8m
- 车身宽度：约 2.08m（含外饰凸出约 2.15m）— **宽度精度直接影响后视镜遮挡仿真**
- 车身高度：约 2.50m（离地至车顶）
- 牵引杆（A-frame）长度：约 1.2m（车身前壁到球头）
- 牵引点高度：约 0.42m（标准 50mm 球头挂接高度）
- 轮轴位置：车身前壁后约 2.3m（略偏后于车身中心）
- 单轴设计，左右各一轮
- 总重（满载）：约 750~1000kg

---

## 房车尺寸 M：中型（Hobby De Luxe / Fendt Bianco 级别）

### Prompt

```
A stylized low-poly 3D model of a mid-size European touring caravan
(travel trailer), similar in size to a Hobby De Luxe 495 or Fendt
Bianco 465. Single-axle design.

BODY: Clean white body with a warm sand-beige accent stripe and
subtle champagne-gold decorative line along the window sill level.
Chibi/compact proportions maintaining the recognizable mid-size
caravan form — a more spacious and elongated shell compared to
compact models, but still on a single-axle chassis. The body is
composed of flat geometric planes with visible but smooth facets.
Slightly taller and wider than the compact type.

FRONT (hitch side): A sturdy A-frame drawbar extending forward,
with two converging geometric bars in dark metallic gray, meeting
at a simplified 50mm ball coupling. A jockey wheel in retracted
position. Front gas bottle locker with a simplified geometric hatch.
A front storage boot / locker visible below the front window.

SIDES: Flat geometric sidewalls — wider than the compact model.
An entry door on the left side as a recessed geometric panel with
grab handle. Two to three geometric windows with darkened glass,
including one larger panoramic window section. A horizontal awning
rail along the upper sidewall edge. Visible wheel arch bulge with
clean geometric lines.

REAR: Flat rear panel with a large geometric rear window (darkened).
Two rectangular geometric taillights. Rear bumper with integrated
step. A simplified rear fog light detail.

ROOF: Slightly curved roof profile, higher than the compact model.
One or two simplified roof vents / skylights (white geometric boxes).
An optional simplified air conditioning unit box on the rear roof
section.

UNDERCARRIAGE: Single axle with two wheels, positioned behind the
body center. Heavier-duty simplified leaf-spring suspension. Dark
gray chassis rails visible beneath the body.

WHEELS: Two standard road tires with simplified alloy-style wheel
covers in silver. Tire size slightly larger than the compact model.

RENDERING: Clean flat geometric colors, no complex textures. Soft
global illumination. Defined geometric facets. Light-blue studio
background. Subtle soft ground shadow. 3/4 rear isometric view angle.
```

### 生成后校准要点
- 整体长度（含牵引杆）：约 6.5m；车身长度（不含牵引杆）：约 5.3m
- 车身宽度：约 2.30m（含外饰凸出约 2.38m）— **中型房车宽度已显著超出大部分牵引车车身宽度**
- 车身高度：约 2.65m（离地至车顶）
- 牵引杆（A-frame）长度：约 1.2m
- 牵引点高度：约 0.42m
- 轮轴位置：车身前壁后约 3.5m
- 单轴设计，左右各一轮
- 总重（满载）：约 1200~1500kg

---

## 房车尺寸 L：大型（Hobby Prestige / Fendt Tendenza 级别）

### Prompt

```
A stylized low-poly 3D model of a large European touring caravan
(travel trailer), similar in size to a Hobby Prestige 720 or Fendt
Tendenza 650. Twin-axle (tandem) design — the defining feature of
large caravans.

BODY: Clean white body with a deep slate-blue accent band running
the full length at mid-height, and a thin silver pinstripe above it.
Chibi/compact proportions maintaining the recognizable large caravan
form — a commanding, elongated and tall shell on a twin-axle chassis.
The body is composed of flat geometric planes with visible but smooth
facets. Noticeably longer and taller than the mid-size model.

FRONT (hitch side): A heavy-duty A-frame drawbar extending forward,
thicker bars than smaller models, converging at a reinforced 50mm
ball coupling with a stabilizer hitch detail. A robust jockey wheel.
Front panel includes a large gas bottle locker and a front storage
boot with simplified geometric hatch. A small front window above the
storage area.

SIDES: Wide flat geometric sidewalls — the widest of all three sizes.
A full-size entry door on the left side with geometric grab rail and
step. Three to four geometric windows — including at least one large
panoramic window section and a smaller bathroom window. Horizontal
awning rail along the full length. Two visible wheel arch bulges
(twin axle), evenly spaced toward the rear half of the body.

REAR: Large flat rear panel. A wide geometric rear window (darkened).
Two prominent rectangular taillights. Rear bumper with integrated
step. A high-level brake light detail. Rear corner steadies
(stabilizer legs) visible in lowered position.

ROOF: Gently curved roof, the highest point of all three sizes. Two
to three simplified roof vents / skylights. A simplified air
conditioning unit on the roof (geometric box). Optional satellite
dish dome (simplified half-sphere).

UNDERCARRIAGE: Twin axle (tandem) — two axles with four wheels total,
the rear-most defining feature of a large caravan. Heavy-duty chassis
rails. Both axles have simplified leaf-spring suspension details.
The twin axles are spaced approximately 1.0m apart.

WHEELS: Four road tires (two per side on tandem axles) with
simplified alloy-style wheel covers in silver-gray. Matched tire
size, larger than the compact model's wheels.

RENDERING: Clean flat geometric colors, no complex textures. Soft
global illumination. Defined geometric facets. Light-blue studio
background. Subtle soft ground shadow. 3/4 rear isometric view angle.
```

### 生成后校准要点
- 整体长度（含牵引杆）：约 8.0m；车身长度（不含牵引杆）：约 6.8m
- 车身宽度：约 2.50m（含外饰凸出约 2.55m）— **大型房车宽度远超所有牵引车，后视镜盲区问题最严重**
- 车身高度：约 2.80m（离地至车顶）
- 牵引杆（A-frame）长度：约 1.2~1.5m
- 牵引点高度：约 0.42m
- 前轴位置：车身前壁后约 4.5m
- 后轴位置：车身前壁后约 5.5m（双轴间距约 1.0m）
- **双轴设计**，左右各两轮（共 4 轮）— 必须在模型中明确表达
- 总重（满载）：约 1800~2500kg

---

## 仿真关键：房车与牵引车的空间关系

### 连接几何

```
                牵引车                          房车
         ┌──────────────┐              ┌─────────────────────────────┐
         │              │  牵引杆 1.2m  │                             │
         │   Vehicle    ├──────────────┤        Caravan Body          │
         │              │  (A-frame)   │                             │
         └──────────────┘              └─────────────────────────────┘
              后保险杠 ←→ 球头 ←→ 车身前壁
                ~0.3m    ~1.2m

   球头高度 ≈ 0.42m（标准欧洲 50mm 球头）
```

### 坐标系对齐（与 MirrorDesign.md 坐标系一致）

```python
# 房车在 Blender 场景中的定位
# 以牵引车前轴为世界原点 (0, 0, 0)

def get_caravan_position(vehicle_params, caravan_params):
    """
    计算房车车身前壁在世界坐标系中的位置。

    参数:
        vehicle_params: 牵引车参数字典
            - 'overall_length': 牵引车全长 (m)
            - 'front_overhang': 前悬 (m)
            - 'rear_bumper_to_hitch': 后保险杠到球头距离 (m), 通常 ~0.3m
        caravan_params: 房车参数字典
            - 'drawbar_length': 牵引杆长度 (m), 通常 1.0~1.5m
            - 'body_length': 车身长度 (m)
            - 'body_width': 车身宽度 (m)
            - 'body_height': 车身高度 (m)

    返回:
        caravan_front_wall_y: 房车前壁的 Y 坐标（REAR 方向，负值）
    """
    # 牵引车后端 Y 坐标（相对前轴原点）
    rear_end_y = -(vehicle_params['overall_length'] - vehicle_params['front_overhang'])

    # 球头位置
    hitch_y = rear_end_y - vehicle_params['rear_bumper_to_hitch']

    # 房车前壁位置 = 球头位置 - 牵引杆长度
    caravan_front_wall_y = hitch_y - caravan_params['drawbar_length']

    return caravan_front_wall_y


# === 各车型-房车组合的前壁 Y 坐标参考 ===
# （负值越大 = 离驾驶员越远 = 后视镜覆盖难度越高）

CARAVAN_POSITIONS = {
    # 皮卡 Hilux (overall_length=5.325m, front_overhang=0.99m)
    'pickup': {
        'S': -5.84,   # 紧凑型房车前壁
        'M': -5.84,
        'L': -5.99,   # 大型房车牵引杆略长 (1.35m)
    },
    # SUV CR-V (overall_length=4.704m, front_overhang=0.895m)
    'suv': {
        'S': -5.31,
        'M': -5.31,
        'L': -5.46,
    },
    # 旅行车 Passat (overall_length=4.917m, front_overhang=0.90m)
    'wagon': {
        'S': -5.52,
        'M': -5.52,
        'L': -5.67,
    },
    # A级小车 Polo (overall_length=4.074m, front_overhang=0.76m)
    'hatchback': {
        'S': -4.81,
        'M': -4.81,
        'L': -4.96,
    },
}
```

### 宽度对比（后视镜遮挡的根因）

| 组合 | 牵引车宽度 (m) | 房车宽度 (m) | 单侧超出量 (m) | 遮挡严重度 |
|------|:---:|:---:|:---:|:---:|
| 任意车型 + 紧凑型 S | 1.75~1.87 | 2.08 | 0.11~0.17 | 轻微 |
| 任意车型 + 中型 M | 1.75~1.87 | 2.30 | 0.22~0.28 | 中等 |
| 任意车型 + 大型 L | 1.75~1.87 | 2.50 | 0.32~0.38 | 严重 |
| **Polo + 大型 L** | **1.751** | **2.50** | **0.37** | **最严重** |

> **仿真核心洞察：** 房车每侧超出牵引车车身的量，直接决定了后视镜需要覆盖的"盲区宽度"。当单侧超出量 >0.25m 时，标准后视镜几乎无法看到房车后方来车，必须使用拖车加长镜或电动升降镜。

---

## 各型号参数汇总表

| 参数 | 紧凑型 S | 中型 M | 大型 L | 单位 |
|------|:---:|:---:|:---:|:---:|
| 车身长度（不含牵引杆） | 3.8 | 5.3 | 6.8 | m |
| 总长度（含牵引杆） | 5.0 | 6.5 | 8.0 | m |
| 车身宽度 | 2.08 | 2.30 | 2.50 | m |
| 车身高度 | 2.50 | 2.65 | 2.80 | m |
| 牵引杆长度 | 1.2 | 1.2 | 1.2~1.5 | m |
| 球头挂接高度 | 0.42 | 0.42 | 0.42 | m |
| 轴数 | 单轴 | 单轴 | **双轴** | — |
| 轮轴距车身前壁 | 2.3 | 3.5 | 4.5/5.5 | m |
| 满载总重 | 750~1000 | 1200~1500 | 1800~2500 | kg |
| 主色调 | 白+薄荷绿 | 白+沙米色 | 白+石板蓝 | — |

---

## 优化说明：与 VehicleModels.md 的设计一致性

| 方面 | 设计决策 | 理由 |
|------|---------|------|
| **结构** | 按 BODY/FRONT/SIDES/REAR/ROOF/UNDERCARRIAGE/WHEELS/RENDERING 分区 | 与 VehicleModels.md 分区逻辑一致，AI 逐特征生成 |
| **视角** | 3/4 后方视角（而非前方） | 房车的"工作面"是 A-frame 牵引杆侧，且后视镜仿真关注的是从驾驶员角度看房车的侧面/后方 |
| **比例** | ~85%（略高于车辆的 80%） | 房车本身造型较方正，过度压缩会丢失比例感 |
| **色彩区分** | 3 种尺寸用 3 种强调色（薄荷绿/沙米色/石板蓝） | 白色主体反映真实房车市场主流配色，强调色用于论文中视觉区分 |
| **牵引杆** | 所有尺寸必须显示 A-frame + 球头 | 连接几何是仿真定位的关键，不可省略 |
| **侧壁强调** | 明确要求"flat geometric sidewalls"作为最重要表面 | 侧壁宽度直接决定后视镜遮挡范围，是仿真核心参数 |
| **双轴标识** | 大型房车明确要求"twin-axle (tandem)"标识 | 双轴是大型房车的关键视觉标识，也影响拖曳几何 |
| **工程锚点** | 每种尺寸附带详细校准要点 + 连接几何公式 | 确保生成模型能在 Blender 中精确定位 |

---

## 使用建议

1. **优先用文本生成**：`generate_hyper3d_model_via_text`，使用上方 prompt（记得加通用风格前缀）
2. **辅助用图片生成**：如有满意的 AI 渲染图，可用 `generate_hyper3d_model_via_images` 以图生模
3. **生成后必做**：
   - 在 Blender 中按"校准要点"缩放到真实尺寸
   - **务必校验车身宽度**（最关键仿真参数）
   - 确认牵引杆 / A-frame 几何正确（长度、高度、收敛角度）
   - 设置原点为**球头挂接点** `(0, 0, 0.42)`，便于与牵引车拖钩位置对齐
   - 统一命名规范（`Caravan_S`、`Caravan_M`、`Caravan_L`）
4. **与牵引车组装**：
   - 牵引车原点 = 前轴中心地面投影 `(0,0,0)`
   - 房车球头位置 = 牵引车后拖钩位置（参考 `get_caravan_position()` 函数）
   - 房车中心线与牵引车中心线对齐（X=0，直线行驶状态）
   - 球头高度统一为 0.42m

