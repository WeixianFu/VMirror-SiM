# Python API 日常使用（macOS / Linux）

日常使用直接调用 Python API；Notebook 只是可选的交互入口。
两台电脑共用以下代码：MacBook 自动使用 Metal，Linux 的 RTX 5070 Ti
优先使用 OptiX，其次 CUDA。GPU 检测失败时默认回退到 CPU，实际设备见返回报告。

## 1. 准备环境

两台电脑安装相同版本的 Blender 5.x，并在项目根目录运行：

```bash
conda env create -f environment.yml  # 首次使用时创建
conda activate vmirror-sim
```

Linux 上确保 `blender` 在 PATH 中；也可设置 `VMIRROR_BLENDER_EXE`
为本机 Blender 可执行文件的完整路径。Mac 默认查找 `/Applications/Blender.app`。
车辆和房车模型不在 Git 中，需要单独补齐 `assets/blender-vehicle/` 和
`assets/blender-caravan/`，保持目录和文件名一致。

## 2. 构建场景并打开预览

将下面代码保存为项目根目录的 `tmp/preview_scene.py`（先创建 `tmp/`），
从项目根目录执行 `PYTHONPATH=. python tmp/preview_scene.py`。
也可以在项目根目录启动 Python 交互会话，直接执行这些代码。

```python
from src import SceneBuilder, CameraRig, Renderer

scene_report = SceneBuilder(
    scene="lane_change",
    vehicle="hilux",
    caravan="large2",
    mirror="standard",
).build(output="tmp/scene.blend")
if scene_report["status"] != "success":
    raise RuntimeError(scene_report)

camera_report = CameraRig(
    side="both",
    vehicle="hilux",
    camera="wide",
).build(
    input="tmp/scene.blend",
    output="tmp/camera.blend",
)
if camera_report["status"] != "success":
    raise RuntimeError(camera_report)

renderer = Renderer(render_profile="configs/render/wide.yaml")
preview_report = renderer.preview(
    input="tmp/camera.blend",
    layout="triple",
)
if preview_report["status"] != "success":
    raise RuntimeError(preview_report)
print("渲染设备：", preview_report["render"])
```

Blender 打开后三窗格分别显示左镜、右镜和场景操作视图。
可以在界面中调整镜子等对象，**调整完成后先保存到 `tmp/camera.blend`**。
`preview()` 返回表示启动脚本完成，窗口保持打开；布局稍后由 Blender 建立。
Linux 图形预览需要桌面会话；只有 SSH 的无桌面环境使用后台渲染。

## 3. 保存调整后，渲染左右镜

下面代码独立运行即可，不需要保留上一个 Python 会话。
保存为 `tmp/render_saved.py` 后，从项目根目录执行
`PYTHONPATH=. python tmp/render_saved.py`。

```python
from src import Renderer

renderer = Renderer(render_profile="configs/render/wide.yaml")

for side in ("L", "R"):
    report = renderer.render(
        input="tmp/camera.blend",
        output=f"output/render-results/hilux_{side}.png",
        camera_name=f"hilux_DriverCam_{side}",
    )
    if report["status"] != "success":
        raise RuntimeError(report)
    print("渲染设备：", report["render"])
    print("图片路径：", report["output_png"])
```

输出文件默认带时间戳，以返回的 `output_png` 为准。
这一步直接读取已保存的场景；不要再次运行第 2 节的构建代码，否则会覆盖
`tmp/camera.blend` 中的手动调整。需要长期保留时，可另存 `.blend`，并把
`input` 改为对应路径。跨电脑打开时通过 `Renderer.preview()` 或 `render()`
重新选择本机 GPU；双击 `.blend` 不会执行项目的自动设备配置。

## 4. 不需要手动调整时，一次性后台出图

```python
from src import SimulationPipeline

report = SimulationPipeline(
    scene="lane_change",
    vehicle="hilux",
    caravan="large2",
    mirror="standard",
    camera="wide",
    camera_side="L",
    output_png="output/render-results/hilux_L.png",
).run()

for stage in ("scene", "camera", "render"):
    if report[stage]["status"] != "success":
        raise RuntimeError(report[stage])
print(report["render"]["output_png"])
```

该流程从配置重新构建场景，不读取第 2 节手动保存的场景。
渲染另一侧时将 `camera_side` 改为 `R`，同时修改输出文件名。

## 5. 台式机首次验收

```bash
python scripts/check_platform.py --backend OPTIX --require-gpu --preview
```

检查报告中的设备为 RTX 5070 Ti，核对左右镜图片和三窗格预览。
这条命令用于环境验证；日常使用以上 Python API。
两种 GPU 后端的图像不保证逐像素完全一致。

完整参数、设备覆盖和报告字段见 [pipeline.md](pipeline.md)。
