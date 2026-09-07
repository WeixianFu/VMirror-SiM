# 配置与模型约定

Python API 是默认值的唯一依据。notebook 从 `SimulationPipeline` 签名读取初始值：
`lane_change / passat / 无房车 / standard / L / 默认相机与渲染配置`。
notebook 选择 `both` 时使用三视口；默认单侧使用双视口。

车辆名称是资产标识，不表示对应真实车型的标定尺寸。尺寸以导入网格为准；
不按厂商尺寸缩放车辆。眼点是模型内的左舵参考点，不声称是测量得到的 P50。

## 哪些配置生效

| 内容 | 使用方式 |
|---|---|
| 车辆 origin、眼点、镜面安装点、牵引点 | 驱动放置，安装点／眼点／牵引点以车辆局部坐标表示 |
| 房车 source_object | 指定导入对象；默认 node_0，large2 为 node_0.001 |
| 镜面 offset.vector、orientation | 驱动局部位置和姿态 |
| 镜面 installation、auxiliary | 驱动外伸余量和主副镜组合 |
| 相机 lens、framing | 驱动内参和完整取景 |
| 场景 sun_light | SceneBuilder 应用位置、角度、energy、color |
| render world | Renderer 每次渲染／预览重新应用颜色与强度，覆盖已有 World |
| 车辆／房车 dimensions、镜片 glass_size、道路布局 | 描述已制作的资产，不会自动重建或缩放网格 |

房车源文件对象可能有偏移，`bounds` 应理解为网格局部范围。
large2 文件同时包含两个模型，`node_0.001` 才是约 6.945×2.500×2.625 m 的目标网格。
流程选择正确对象即可，无须覆盖大型资产文件。

## 后视镜安装

`standard` 保持现有单镜片；`towing` 自动加载 towing_main 与 towing_wide_angle；
`electric` 自动加载 electric_main 与 electric_sub。主镜名称仍是
`<vehicle>_Mirror_L/R`，副镜为 `<vehicle>_Mirror_L/R_Aux`。

| 组合 | 基础外伸 | 主镜上移 | 副镜下移 |
|---|---|---|---|
| towing | 0.65 m | +0.05 m | −0.11 m |
| electric | 0.25 m | +0.05 m | −0.10 m |

所有镜面仍在安装点后方 0.10 m。镜片宽、高、曲率不变。
拖挂主镜 YAML 的 `installation.outboard_clearance_m: 0.05` 会以实际导入的
车身／房车网格横向外边界为准，必要时继续向外平移整组玻璃，直到整组玻璃的
内侧边缘也比模型侧边更外侧至少 50 mm。改变模型、镜面朝向后会重新计算。
这是一条几何安装约束，不代表完整镜壳、支架或机械强度设计。

主镜 YAML 使用 `auxiliary: {mirror: towing_wide_angle}` 指定副镜；删除／设为空
可关闭。也可用 `auxiliary.path` 指定自定义副镜 YAML 的绝对路径。副镜配置仍可
单独作为一侧镜片使用；它不会再递归加载其他副镜。

车辆、房车、玻璃和相机保持父子关系。玻璃 `explicit` 角度与偏移都以车辆坐标
表示；零姿态下与旧世界角度相同。旧的非零姿态世界角度配置需要重新导出。
`dynamic_reflection` 在构建时用变换后的眼点计算世界法线，再换回车辆坐标。
之后在 GUI 移动车辆会带动子对象，但不会持续自动重新瞄准固定世界目标。

`mirror_target=(0,-20,0.5)` 是**世界坐标中的朝向参考点**，不是安装点、接头或
必须无遮挡的检测点。它只参与法线计算，不执行无遮挡优化。允许被车身或房车
遮住；镜中出现遮挡物是正常结果。本次保留该默认值。

## 双侧完整取景

所有自带相机 YAML 启用：

```yaml
framing:
  enabled: true
  margin: 0.05
```

200 mm／150 mm 是请求的最大焦距。CameraRig 根据实际网格顶点、眼点、相机方向
和画幅缩短焦距，保留四边至少 5% 余量；主副镜一起纳入检查。眼点不移动。
Renderer 在应用实际输出比例后再次检查两侧，因此换横／竖／方形输出时仍有效。
报告的 `framing` 包含实际焦距、对象列表和归一化投影边界。
裁剪距离排除镜片或焦距无法满足时返回错误，而不是悄悄裁切。

手工固定焦距时可设置 `framing.enabled: false`；在已保存 blend 中设置相机
`vmirror_framing` 为 `{"enabled": false}`。启用时渲染会重新适配，GUI 改焦距
不会覆盖配置的请求焦距。主镜仍是 Track-To 目标，因此副镜较低时会留更多上方
空间。左右镜像素大小可以不同，不能直接以图像占比比较可见环境面积。

`CameraRig(side="both")` 建立两台相机；`Renderer.render(camera_name=...)` 每次输出
其中一台。`SimulationPipeline(camera_side="both")` 的单次渲染仍使用主相机 L；
需要两张图时分别指定侧别运行，或复用双相机场景调用 Renderer 两次。

## 环境、导出与限制

`configs/scenes/*.yaml` 的 `sun_light` 在构建时应用；改后应重建场景。
`configs/render/*.yaml` 的 `world` 在每次渲染和预览时应用。`sky_background`
表示恒定颜色背景，并非物理天空。若自定义渲染配置省略 `world`，保留输入环境。

ConfigExporter 导出主副镜的实际车辆局部位置与 explicit 角度，主镜引用导出的
副镜文件。explicit 模式不会再次自动外伸，便于复现手动调整。
副镜引用是绝对路径，跨机器搬迁导出包时须更新路径。相机导出仍只包含选定的
主相机配置；房车 applied_world_location 仍只作记录，不能视为完整场景往返。

眼点、球心 0.42 m 高度仍是模型参考值，尚未校验球窝实体接触；不新增人体标定、
真实驾驶舱遮挡、转弯扫掠或法规合格判断。相机继续允许穿透车身。

## 实际模型验证

```bash
python scripts/check_geometry.py
```

使用 API 构建默认 Passat、四车拖挂组合和 electric 组合，分别渲染 L/R（32 samples、
40% 分辨率），检查 large2 网格、主副镜垂向间隔、拖挂外侧余量、相机边界、YAML
环境覆盖、非零车辆姿态及主副镜导出重载。图和 JSON 放 `output/geometry-check/`，
blend 放 `tmp/`；不修改资产或基准配置。此检查需要本地完整模型资产和 Blender。
