# VMirror-SiM

**Vehicle Mirror Simulation** — 拖车后视镜视野仿真系统

基于 Blender Cycles 光线追踪的参数化后视镜视野分析工具，用于评估车辆拖曳房车时不同后视镜配置下的驾驶员可视区域。

## 项目目标

提出一种**跨平台通用的拖车后视镜视野分析方法论**，系统性地分析不同车型、镜型、房车尺寸组合下的后视镜视野覆盖情况。

## 仿真矩阵

- **车型**：皮卡 (Hilux) · SUV (CR-V) · 旅行车 (Passat) · A级小车 (TBD)
- **后视镜类型**：平面镜 · 吸附式凸面镜 · 外套式外壳镜 · 电动升降高端镜
- **房车尺寸**：紧凑型 S · 中型 M · 大型 L · 大型 L2
- **眼点位置**：P5 / P50 / P95（基于 SAE J941）

## 目录结构

```
VMirror-SiM/
├── docs/                      # 项目文档与 AI 提示词
├── src/                       # Python 脚本 & Jupyter Notebooks
├── assets/
│   ├── reference-images/      # AI 生成 3D 模型时的参考图
│   └── models/                # 3D 模型文件 (.gitignore)
├── config/                    # 参数配置 (JSON/YAML)
├── renders/                   # 渲染输出
└── results/                   # 分析结果 (CSV)
```

> **注意**：`assets/models/` 目录包含大型 3D 模型文件（~1GB），已通过 `.gitignore` 排除。请从项目共享存储单独获取。

## 技术栈

- **Blender** + Cycles 渲染引擎（Metal GPU）
- **Python** (bpy API / Raysect 光学库)
- **Jupyter Notebook** 仿真分析

## License

Apache-2.0
