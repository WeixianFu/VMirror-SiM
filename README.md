# VMirror-SiM

车辆拖拽后视镜视野仿真。

![Triple-pane preview: left-top driver camera L, left-bottom driver camera R, right free-orbit view](docs/images/cover.jpg)

## Quick start

```bash
# Python env (conda, single source of truth)
conda env create -f environment.yml && conda activate vmirror-sim

# Install the same Blender 5.x release on macOS and Linux.
# macOS: /Applications/Blender.app; Linux: blender on PATH.
# Optional custom location: export VMIRROR_BLENDER_EXE=/path/to/blender
# Copy the gitignored vehicle/caravan assets to the other computer first.

# Render a scene end-to-end
python3 -c "
from src import SimulationPipeline
SimulationPipeline(
    scene='lane_change', vehicle='hilux', caravan='large2',
    mirror='standard', camera_side='L',
    output_png='output/render-results/hilux.png',
).run()
"
```

See [docs/pipeline.md](docs/pipeline.md) for the full guide and
[CHANGELOG.md](CHANGELOG.md) for capabilities.

## macOS + Linux

Use the same environment, configs and `notebooks/vmirror_explorer.ipynb` on
both computers. Start `jupyter lab` from the project root after activating
`vmirror-sim`. Blender must be installed separately on each machine.

The default and wide profiles automatically select Metal on a Mac and
OptiX on an NVIDIA Linux desktop (CUDA is the next choice). If no GPU can
be initialized, rendering explicitly falls back to CPU and reports why.
The notebook displays the selected backend/device for preview and rendering.
Preview needs a desktop session; background rendering also works without one.

For setup, device overrides and verification, see
[the cross-platform guide](docs/pipeline.md#9-macos-and-linux-development).
