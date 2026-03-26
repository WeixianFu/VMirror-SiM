# Prompt #3：AI 3D 车辆模型生成 Prompt 集

---

## 通用风格指令（所有车型共享前缀）

```
STYLE PREFIX (prepend to each vehicle prompt):

Stylized low-poly 3D model. Clean geometric facets with defined edges.
Flat-shaded surfaces, no complex textures. Soft global illumination on
a neutral light-blue background. Proportions are slightly chibi/compact
(~80% realistic proportions) for visual appeal while maintaining
recognizable vehicle silhouette. Clean 3/4 front view.
IMPORTANT: Do NOT include side mirrors on the vehicle body. The mirror
mounting area at the A-pillar base should be a clean, flat surface with
no protrusions. Side mirrors will be added separately as independent
parametric components.
```

---

## 车型 A：中型 SUV（CR-V 级别）

### Prompt（优化版）

```
A stylized low-poly 3D model of a modern compact SUV, similar in shape
to a Honda CR-V or Toyota RAV4.

BODY: Bright orange body with clean white roof panel. Slightly
chibi/compact proportions (~80% of real-world ratio) but maintaining
the recognizable tall SUV stance — high ground clearance, upright
D-pillar, and a gently sloping roofline. The body is composed of
flat geometric planes with visible but smooth facets.

FRONT: Simplified modern grille with horizontal slats. Angular LED
headlights rendered as glowing geometric strips (not round). A subtle
lower bumper intake in dark gray.

SIDE: Darkened geometric window glass with visible A/B/C/D pillars.
Minimalist flush door handles. Clean wheel arches with slight flare.
No side mirrors — the A-pillar base / front door corner area should
be a clean flat surface (mirrors will be added as separate components).

REAR: Simple geometric taillight bars. Flat rear hatch panel.

ROOF: A simplified tubular metal roof rack with cross bars, mounted
on the white roof section.

WHEELS: Four large, blocky off-road style tires with visible geometric
tread pattern. Simplified 5-spoke alloy wheels in silver-gray.

RENDERING: Clean flat geometric colors, no complex textures. Soft
global illumination. Defined geometric facets. Light-blue studio
background. Subtle soft ground shadow. 3/4 front isometric view angle.
```

### 生成后校准要点
- 整体长宽高比例：约 4.6m × 1.85m × 1.7m（缩放到 Blender 实际尺寸）
- 后视镜安装位置：A 柱底部/前车门前缘，离地约 1.25m
- 窗框下沿高度：约 1.25m
- 前轴位置：车头后约 0.9m

---

## 车型 B：皮卡（Ranger / Hilux 级别）

### Prompt

```
A stylized low-poly 3D model of a mid-size pickup truck, similar in
shape to a Ford Ranger or Toyota Hilux double cab.

BODY: Matte dark blue body with a contrasting silver-gray front bumper
and rear bumper. Chibi/compact proportions maintaining the pickup truck
silhouette — long hood, upright cab, open cargo bed with visible bed
walls. Flat geometric surfaces with defined facets.

FRONT: Bold simplified grille with thick horizontal bars. Rectangular
geometric LED headlights. High-mounted front bumper with a simplified
skid plate detail in dark gray.

SIDE: Tall ride height and prominent wheel arches. Four-door cab with
darkened geometric windows. Clean B-pillar separating front and rear
doors. No side mirrors — the A-pillar base area should be clean and
flat (mirrors will be added as separate components). Behind the cab,
an open cargo bed with low geometric sidewalls.

REAR: Flat tailgate panel. Simple rectangular taillights. Step bumper
with a visible tow hitch/receiver below the tailgate (important for
towing context).

WHEELS: Four large, rugged off-road tires with aggressive blocky tread.
Simplified 6-spoke alloy wheels in dark gray. Noticeably larger wheel-
to-body ratio than a sedan.

RENDERING: Clean flat geometric colors, no complex textures. Soft
global illumination. Defined geometric facets. Light-blue studio
background. Subtle soft ground shadow. 3/4 front isometric view angle.
```

### 生成后校准要点
- 整体长宽高比例：约 5.3m × 1.85m × 1.8m
- 后视镜安装位置：A 柱底部，离地约 1.35m（高于 SUV）
- 窗框下沿高度：约 1.35m
- 货箱长度：约 1.5m
- 后拖钩位置：后保险杠中央下方

---

## 车型 C：旅行车（Passat Variant 级别）

### Prompt

```
A stylized low-poly 3D model of a European-style station wagon / estate
car, similar in shape to a VW Passat Variant or Skoda Superb Combi.

BODY: Elegant dark silver / gunmetal gray body. Chibi/compact proportions
maintaining the estate car silhouette — long and low body, extended
roofline stretching all the way to the rear, and a gently sloping rear
window. Flat geometric surfaces with defined facets.

FRONT: Sleek simplified grille with thin horizontal lines. Narrow angular
LED headlights as geometric strips. Low front bumper with wide air
intake detail.

SIDE: Low and elongated body profile. Darkened geometric windows —
notably the rear side windows extend far back, a key wagon identifier.
Visible A/B/C/D pillars with a thin chrome-like strip along the window
line. No side mirrors — the A-pillar base area should be clean and flat
(mirrors will be added as separate components). Clean flush door handles.
Subtle lower body crease line running the length of the car.

REAR: Vertical or L-shaped geometric taillights. Flat rear hatch/tailgate
that is taller than a sedan's trunk (station wagon form). Integrated
rear bumper with a simplified diffuser element. A small tow bar visible
beneath the rear bumper.

WHEELS: Four moderately sized road tires (less aggressive than SUV).
Simplified multi-spoke alloy wheels in polished silver. Lower ride
height than the SUV, giving a planted stance.

RENDERING: Clean flat geometric colors, no complex textures. Soft
global illumination. Defined geometric facets. Light-blue studio
background. Subtle soft ground shadow. 3/4 front isometric view angle.
```

### 生成后校准要点
- 整体长宽高比例：约 4.8m × 1.83m × 1.5m（低于 SUV）
- 后视镜安装位置：A 柱底部，离地约 1.05m
- 窗框下沿高度：约 1.05m
- 车身较长较低，拖房车时后视野遮挡更显著

---

## 车型 D：A 级小车（Polo / Yaris 级别）

### Prompt

```
A stylized low-poly 3D model of a European-style supermini / B-segment
hatchback, similar in shape to a VW Polo or Toyota Yaris.

BODY: Vivid red body with a black roof panel. Chibi/compact proportions
accentuating the small, nimble character — short overhangs, compact
overall length, and a relatively tall greenhouse (window area) compared
to body length. Flat geometric surfaces with defined facets.

FRONT: Friendly simplified grille, smaller and less aggressive than the
SUV. Round-ish but still geometric LED headlights. Compact front bumper
with minimal lower intake.

SIDE: Short and tall body profile — a hallmark of supermini proportions.
Five-door hatchback with darkened geometric windows. The rear window
sweeps down steeply to a short rear overhang. No side mirrors — the
A-pillar base area should be clean and flat (mirrors will be added as
separate components). Short hood, long cabin — the "cab-forward"
proportion.

REAR: Wide geometric taillights spanning part of the tailgate. Short
rear overhang. Steep rear hatch angle. A small tow coupling point
barely visible below the rear bumper (many small cars in Europe do
tow small caravans).

WHEELS: Four compact road tires. Simplified 5-spoke alloy wheels in
dark silver. Small wheel diameter relative to body (14-16 inch scale),
lower and smaller than the SUV.

RENDERING: Clean flat geometric colors, no complex textures. Soft
global illumination. Defined geometric facets. Light-blue studio
background. Subtle soft ground shadow. 3/4 front isometric view angle.
```

### 生成后校准要点
- 整体长宽高比例：约 4.0m × 1.75m × 1.47m
- 后视镜安装位置：A 柱底部，离地约 1.00m
- 窗框下沿高度：约 1.00m
- 车身最小，拖房车时盲区问题最为突出

---

## 优化说明：相比 Gemini 原始 Prompt 的改进

| 方面 | 原始 Prompt | 优化后 |
|------|-----------|--------|
| **结构** | 单段长文本，信息层次不清 | 按 BODY/FRONT/SIDE/REAR/ROOF/WHEELS/RENDERING 分区，AI 更容易逐特征生成 |
| **后视镜** | 仅提及"minimalist side mirrors" | 明确排除后视镜生成——车身 A 柱底部保持干净平面，后视镜作为独立参数化组件单独建模（见 `MirrorDesign.md`），避免几何冲突 |
| **拖钩** | 未提及 | 皮卡/旅行车/小车均提及拖钩/拖杆，呼应拖房车仿真主题 |
| **比例描述** | "slightly cute (chibi-like)" 模糊 | 明确"~80% realistic proportions"，给出数值参考感 |
| **车型覆盖** | 仅 SUV 一种 | 覆盖项目所需全部 4 种车型（SUV / 皮卡 / 旅行车 / A级小车） |
| **色彩区分** | 全部橙色 | 4 种车型用 4 种颜色（橙/蓝/银/红），便于论文中视觉区分 |
| **工程锚点** | 无 | 每种车型附带"生成后校准要点"，标注关键尺寸供 Blender 中校准 |
| **头灯描述** | "softly glowing geometric LED headlights (not round)" | 各车型差异化头灯风格（SUV 锐利/皮卡粗犷/旅行车窄长/小车友善） |
| **渲染指令** | 混在造型描述中 | 抽离为独立 RENDERING 段落 + 通用 STYLE PREFIX，减少重复 |

---

## 使用建议

1. **优先用文本生成**：`generate_hyper3d_model_via_text`，使用上方 prompt
2. **辅助用图片生成**：如果有满意的 AI 渲染图（如 Gemini 生成的那张 SUV），可用 `generate_hyper3d_model_via_images` 以图生模
3. **生成后必做**：
   - 在 Blender 中按"校准要点"缩放到真实尺寸
   - 确认车身无自带后视镜几何体（如有残留需删除），后视镜按 `MirrorDesign.md` 单独建模后挂载到 A 柱安装点
   - 设置前轴原点为 `(0,0,0)`
   - 统一命名规范（`Vehicle_SUV`、`Vehicle_Pickup` 等）

---

**备注：** （待执行后补充生成效果评价）
