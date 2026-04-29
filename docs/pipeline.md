# SimulationPipeline — Usage Guide

End-to-end workflow for building, previewing, rendering, and tuning a
VMirror-SiM scene from a Jupyter notebook or plain Python.

Classes (each in its own `src/*.py`):
- `SceneBuilder` — steps 1–4 (scene + vehicle + caravan + mirrors)
- `CameraRig` — step 5 + ego ray-visibility
- `Renderer` — step 7 (render profile + optional PNG) and `preview()`
- `SimulationPipeline` — one-shot chain of the three
- `ConfigExporter` — snapshot a tweaked `.blend` back into a drop-in yaml bundle

No `blender-mcp` (or any other Blender addon) is required. Each stage spawns
its own Blender subprocess and Blender exits (headless) or stays open
(`open_gui=True`) when it finishes.

---

## 1. Prerequisites

| Component        | Version / path                                      |
| ---------------- | ---------------------------------------------------- |
| Blender          | auto-detected at `/Applications/Blender.app/Contents/MacOS/Blender`, or the first `blender` on `PATH` |
| Python (notebook)| 3.9+ with `pyyaml` (the builder itself imports nothing else) |
| GPU (optional)   | Apple-Silicon Metal is auto-enabled from `configs/render/default.yaml` |

Install notebook-side deps:

```bash
pip install pyyaml jupyterlab
```

Blender's own Python is not involved on the notebook side; it only runs
inside the subprocesses the builder spawns.

---

## 2. Directory layout touched at runtime

```
VMirror-SiM/
├── assets/           (geometry .blend — never written to by the pipeline)
├── configs/          (yaml parameters — read-only at runtime)
├── src/
│   ├── scene_builder.py     class SceneBuilder
│   ├── camera_rig.py        class CameraRig
│   ├── renderer.py          class Renderer (render + preview)
│   ├── pipeline.py          class SimulationPipeline
│   ├── config_exporter.py   class ConfigExporter
│   └── _common.py           shared utilities (subprocess runner, yaml loader…)
├── tmp/              (intermediate .blend files — gitignored, safe to nuke)
└── output/
    ├── render-results/   (timestamped PNGs — your results live here)
    └── tuned-configs/    (ConfigExporter sessions — drop-in yaml bundles)
```

`tmp/` and `output/` are created on first use; both are listed in `.gitignore`.

---

## 3. The three stages

Each stage is a standalone step with a single input + single output. The
`.blend` file on disk is the hand-off between stages.

### 3.1 `SceneBuilder` — steps 1–4 of `docs/model_import.md`

Reads: `scenes/*.yaml`, `vehicles/*.yaml`, `caravans/*.yaml` (optional),
`mirrors/*_{L,R}.yaml`.
Writes: an output `.blend` containing the scene + ego vehicle + optional
caravan + both mirrors, with metadata stored on `scene["vmirror_*"]` custom
properties so downstream stages know which vehicle/mirror was used.

```python
from src import SceneBuilder
SceneBuilder(
    scene="lane_change",       # configs/scenes/<name>.yaml
    vehicle="hilux",           # configs/vehicles/<name>.yaml
    caravan="large2",          # optional; None → no caravan
    mirror="standard",         # uniform L+R; aliases: standard→standard_convex,
                               #                        towing  →towing_main,
                               #                        electric→electric_main
    mirror_target=(0, -20, 0.5),
).build(
    output="tmp/step1_scene.blend",
    open_gui=False,            # True → keep Blender window open after build
)
```

Heterogeneous mirrors (per-side override, path-based, or both):

```python
# Per-side variant names (aliases also work for each side)
SceneBuilder(mirror_L="standard", mirror_R="towing_wide_angle", ...).build(...)

# Per-side absolute yaml path (wins over mirror_L / mirror)
SceneBuilder(mirror_path_L="configs/_tuned/session1/mirrors/standard_convex_L.yaml",
             mirror_path_R="configs/_tuned/session1/mirrors/towing_wide_angle_R.yaml",
             ...).build(...)
```

Resolution per side: `mirror_path_{side} > mirror_{side} > mirror (uniform)`.
Mirror class name may be short (`"standard"`), the class stem
(`"standard_convex"`), or the full side-tagged name
(`"standard_convex_L"`, side must match).

**Mirror orientation policies** — each mirror yaml carries
`orientation.policy` plus a baked `rotation_euler_deg`:

| policy                | behaviour                                                              |
| --------------------- | ---------------------------------------------------------------------- |
| `dynamic_reflection`  | SceneBuilder recomputes rotation at runtime from eye + mirror_target. The `rotation_euler_deg` field is a **passat reference value** — used only when you switch to `explicit`. |
| `explicit`            | SceneBuilder skips the reflection law and uses `rotation_euler_deg` verbatim. Produced by `ConfigExporter` after a manual tweak. |

Typical wall time: **~1 s** headless.

### 3.2 `CameraRig` — step 5 + 6a

Reads: a camera yaml under `configs/cameras/` and `vehicles/<name>.yaml`
(only `eye_point`).
Writes: same `.blend` with `{vehicle}_DriverCam_{side}` added per chosen side
(parented to ego at `vehicle.eye_point`, Track-To constraint pointing at
`{vehicle}_Mirror_{side}`). Also applies `ego_ray_visibility` from the camera
yaml so the driver camera shoots through the cabin (`visible_camera=False`)
while the cabin still appears in the mirror reflection (`visible_glossy=True`).

```python
from src import CameraRig
CameraRig(
    side="L",                  # "L" / "R" / "both"
    vehicle="hilux",           # only used for eye_point lookup
    camera=None,               # variant name; None → driver_camera_{side}
    camera_path=None,          # explicit yaml path; wins over camera/side defaults
).build(
    input="tmp/step1_scene.blend",
    output="tmp/step2_camera.blend",
    open_gui=False,
)
```

**Camera variant selection** — three knobs, priority
`camera_path > camera > default`:

| call                                                 | loaded yaml                                |
| ---------------------------------------------------- | ------------------------------------------ |
| `CameraRig(side="L")`                                | `cameras/driver_camera_L.yaml`             |
| `CameraRig(side="L", camera="wide")`                 | `cameras/driver_camera_wide_L.yaml`        |
| `CameraRig(side="L", camera="driver_camera_wide")`   | same as above (full prefix)                |
| `CameraRig(side="L", camera="driver_camera_wide_L")` | same; side suffix must match               |
| `CameraRig(side="R", camera_path="/a/b.yaml")`       | `/a/b.yaml` (absolute; side still affects mirror target) |

**`side="both"`** places both `{veh}_DriverCam_L` and `{veh}_DriverCam_R` in
one subprocess — required for `Renderer.preview(layout="triple")`. The
`camera` argument is shared across sides (both L and R get the same variant);
`camera_path` is not allowed with `side="both"` (pick variant name instead).

Running `CameraRig(side="L")` then `CameraRig(side="R")` in sequence produces
an equivalent blend.

Typical wall time: **~1 s** headless for one side, ~1 s for both.

### 3.3 `Renderer` — step 6c + 7

Reads: a render profile yaml (default `configs/render/default.yaml`;
override via `render_profile=...`).
Writes: a PNG (if `output=` is passed) and/or the rendered-configured
`.blend` (if `output_blend=` is passed).

When called via `SimulationPipeline`, the render profile auto-picks up from
the camera yaml's `render_profile:` field — pairing `camera="wide"` with
`configs/render/wide.yaml` (2560 × 1440) without extra config.

The world/environment shader now lives in the render yaml (`world:` block).
It is only applied when the loaded blend has no world shader — scene blends
typically ship with their own, in which case the render-yaml world is a
documented default that is not touched.

```python
from src import Renderer
Renderer(
    render_profile=None,       # None → configs/render/default.yaml
).render(
    input="tmp/step2_camera.blend",
    output="output/render-results/hilux_large2_L.png",
    timestamp=True,            # inserts _MMDD_HHMM before .png (default True)
    output_blend=None,         # set to persist the render-configured scene
    open_gui=False,
)
```

The file actually written becomes
`output/render-results/hilux_large2_L_MMDD_HHMM.png`.

Typical wall time: **8–15 s** on M3 Max (CYCLES 512 spp, 1920 × 1080, OIDN).

### 3.4 `Renderer.preview()` — live viewport preview (no PNG)

Opens the blend in a GUI Blender, applies the render profile, and sets up a
live viewport preview. M3 Max with Metal + OIDN converges from turn-jitter
to a clean image in under a second, so you can rotate mirrors, drag objects,
tweak lights, etc. and see the reflected image update live.

```python
from src import Renderer
handle = Renderer().preview(
    input="tmp/step2_camera.blend",
    layout="split",    # default; see below. "single" for one full viewport.
)
# Close the window when done, or:
import os, signal
os.kill(handle["_pid"], signal.SIGTERM)
```

**`layout="split"`** (default, professional workflow):
- The 3D viewport is split vertically in the startup workspace.
- **Left half** — camera view + Rendered shading: your live "monitor" of what
  the driver camera sees through the mirror. Do not orbit in this half; it
  is meant to stay locked on the camera.
- **Right half** — free-orbit perspective + Solid shading: where you operate.
  Select `hilux_Mirror_L`, press `R` to rotate, drag — the **left half updates
  the reflection live** while you work.

This split happens ~1 s after the window appears (scheduled via
`bpy.app.timers`; `area_split` needs a live event loop). Before the split
fires, both halves share the single camera+Rendered view — it is never
visually "wrong", only rearranged.

**`layout="triple"`** (three-pane, needs both L+R cameras in the blend):
- The 3D viewport is split into **three panes**.
- **Left-top** — L mirror view (binds `{vehicle}_DriverCam_L` via
  ``use_local_camera``), Rendered shading.
- **Left-bottom** — R mirror view (`{vehicle}_DriverCam_R`), Rendered shading.
- **Right** — Solid shading manipulation pane; starting view controlled by
  ``right_view`` (see below).
- Requires both cameras present in the blend. Build them with
  ``CameraRig(side="both")`` in one call, or two ``CameraRig`` calls (L
  then R). Missing a camera → Renderer logs a warning and falls back to
  2-pane ``split`` layout (with the same ``right_view``).

**`right_view`** (honored for ``"split"`` and ``"triple"``; ignored for ``"single"``):

| value     | result                                                                             |
| --------- | ---------------------------------------------------------------------------------- |
| ``"top"`` | orthographic top-down centered between ego and caravan (default; best for moving objects on the ground) |
| ``"front"`` | orthographic front view (looking +Y)                                             |
| ``"side"``  | orthographic right-side view                                                     |
| ``"free"``  | Blender's default User Perspective (free orbit)                                  |

You can always change views interactively in Blender — hover the right pane
and press Numpad 7/1/3 (top/front/side) or 5 to toggle ortho/persp. On
MacBooks without a numeric keypad, enable **Edit → Preferences → Input →
Emulate Numpad** so the main number row substitutes for the missing keys.

**`layout="single"`**:
- Every 3D viewport area (including non-Layout workspaces) is set to camera
  view + Rendered. No splitting. You can still select and operate on objects
  inside this view; only middle-click-drag orbit kicks you out of camera
  view (press `Numpad 0` to return).

Other notes:

- Preview uses `scene.cycles.preview_samples` (128 by default) with adaptive
  sampling; final `render()` uses `scene.cycles.samples` (512).
- `Ctrl+S` to save tweaks back to the blend you loaded — the next `render()`
  will pick them up.
- Preview writes no PNG and does not modify the blend on disk unless you
  save manually.

### 3.5 `ConfigExporter` — snapshot a tuned blend back to yaml

After you manually rotate a mirror / move a caravan / tweak the driver
camera in the GUI and `Ctrl+S` the blend, `ConfigExporter` reads the saved
blend and writes a drop-in yaml bundle. Output is
`output/tuned-configs/<session>/` mirroring the top-level `configs/` layout
so the bundle can be referenced via per-side paths (§3.1) or copied over
the official configs.

```python
from src import ConfigExporter
exp = ConfigExporter().export(
    blend="tmp/step2_camera.blend",
    tag=None,                  # None → auto name: <vehicle>_<caravan>_side<L|R>_MMDD_HHMM
    mirror_mode="explicit",    # only mode currently supported
    include=("vehicle", "mirror", "caravan", "camera"),
    out_root="output/tuned-configs",
)
# exp["session_dir"] = output/tuned-configs/hilux_large2_sideL_0423_1600
# exp["files"] = [vehicles/hilux.yaml, mirrors/standard_convex_L.yaml, ...]
```

What gets re-computed vs pass-through:

| yaml family  | field(s) re-computed from the blend                                       |
| ------------ | ------------------------------------------------------------------------- |
| `vehicles/`  | `origin.position` / `origin.rotation`, `eye_point` (from camera local)    |
| `caravans/`  | `ray_visibility` (six Cycles flags), `applied_world_location` (doc-only)  |
| `mirrors/`   | `glass_center_offset.vector` (mirror_world − mount), `orientation.policy="explicit"`, `orientation.rotation_euler_deg` |
| `cameras/`   | `lens.{focal_length_mm, sensor_width_mm, clip_start_m, clip_end_m}`       |

All other fields are copied verbatim from the baseline yaml (identified via
`vmirror_*` metadata the upstream classes wrote into `scene["vmirror_*"]`).

Round-trip: feed the produced mirror yamls back via `mirror_path_L/R` and
SceneBuilder reproduces the tweaked rotation to < 1 µ° (verified).

---

## 4. Two ways to run the pipeline

### 4.1 Step-by-step (recommended for tuning)

Good when you want to inspect / hand-edit intermediate `.blend` files between
stages. Pass `open_gui=True` to each step to have Blender stay open; modify
in the GUI, `File → Save` over the intermediate file, then run the next
stage.

```python
from src import SceneBuilder, CameraRig, Renderer

SceneBuilder(scene="lane_change", vehicle="hilux",
             caravan="large2", mirror="standard").build(
    output="tmp/step1_scene.blend", open_gui=True,
)
# ← manually rotate a mirror in the window, File → Save

CameraRig(side="L", vehicle="hilux").build(
    input="tmp/step1_scene.blend",
    output="tmp/step2_camera.blend", open_gui=True,
)
# ← verify camera framing, File → Save

Renderer().render(
    input="tmp/step2_camera.blend",
    output="output/render-results/hilux.png",
)
```

### 4.2 One-shot `SimulationPipeline`

Good for batch runs where no manual tweaking is needed.

```python
from src import SimulationPipeline
SimulationPipeline(
    scene="lane_change",
    vehicle="hilux",
    caravan="large2",
    mirror="standard",
    camera_side="L",
    output_png="output/render-results/hilux.png",
    timestamp=True,            # default
).run()
```

`SimulationPipeline` forwards every per-side and per-variant knob:

```python
SimulationPipeline(
    ...,
    mirror_L="standard", mirror_R="towing_wide_angle",    # heterogeneous mirrors
    mirror_path_L=None,  mirror_path_R=None,              # or explicit yaml paths
    camera="wide",                                        # 150 mm variant → auto
    render_profile=None,                                  #   render/wide.yaml
    camera_path=None,                                     # or absolute camera yaml
).run()
```

Intermediate `.blend` files go to a temp subdirectory inside `tmp/` and are
wiped after the run unless `keep_intermediates=True`.

---

## 5. Headless vs GUI mode

| `open_gui` | What happens                                                                  | Wall time |
| ---------- | ----------------------------------------------------------------------------- | --------- |
| `False` (default) | `blender --background --python <script>.py`; Blender exits on completion. Report returned synchronously. | Step 1 ≈ 1 s / Step 2 ≈ 1 s / Step 3 ≈ 8–15 s (default 1920×1080 profile) or 12–20 s (wide 2560×1440); `Renderer.preview()` ≈ 1 s to window-ready |
| `True`            | `blender --python <script>.py` (GUI). The script runs during Blender startup, writes its report, and leaves the window open. `build()` / `render()` returns immediately once the report file appears. | +~3–5 s for window draw |

In GUI mode each call's `report["_pid"]` is the Blender PID; close the window
manually when done (or `os.kill(pid, signal.SIGTERM)`). Windows from
different stages can coexist — you can keep Step 1's window open as a
reference while Step 2's window is live. The return dict also carries
`report["_log_path"]` pointing at a `blender_stdout.log` under
`tmp/vmirror_sim_*/` — handy for debugging deferred-timer failures (e.g.
`layout="triple"` split issues), since the GUI Blender's stdout/stderr is
redirected there.

---

## 6. File naming convention

- **Intermediates** (`tmp/step{N}_{stage}.blend`) are transient. They are
  *not* auto-timestamped because you typically overwrite them every iteration.
  `tmp/` is gitignored.
- **Render results** (`output/render-results/<name>.png`) get a
  `_MMDD_HHMM` suffix by default via `timestamp=True`. Set `timestamp=False`
  if you want a fixed filename (latest render overwrites the previous one).

Example names the default convention produces:

```
output/render-results/hilux_large2_L_0423_1410.png
output/render-results/passat_standard_R_0423_1522.png
```

---

## 7. Common mirror / vehicle / scene / camera names

| Category          | Valid names                                                                     |
| ----------------- | ------------------------------------------------------------------------------- |
| `scene`           | `highway`, `lane_change`, `parking`, `regulatory`                               |
| `vehicle`         | `crv`, `hilux`, `passat`, `polo`                                                |
| `caravan`         | `compact`, `middle`, `large`, `large2`, or `None`                               |
| `mirror`          | `standard` (= `standard_convex`), `towing` (= `towing_main`), `electric` (= `electric_main`), `electric_sub`, `towing_wide_angle`, `clip_on_blind_spot` |
| `side` / `camera_side` | `L`, `R`, or `both` (CameraRig; `SimulationPipeline` takes `camera_side`)    |
| `camera` (variant)| unset (default 200 mm), `wide` (150 mm, auto-pairs with `render/wide.yaml`)     |
| `render_profile`  | `configs/render/default.yaml`, `configs/render/wide.yaml`                       |

All configs are under `configs/{scenes,vehicles,caravans,mirrors,cameras,render}/`.
Adding a new asset = dropping a new yaml + blend; the pipeline discovers it
by name.

---

## 8. Debugging tips

- **Where are my files?** `SceneBuilder.build()` / `CameraRig.build()` /
  `Renderer.render()` all return dicts with the absolute paths they wrote
  (`output_blend`, `output_png`).
- **Something failed inside Blender.** Status is `"error"` and the report
  carries `"error"` + `"traceback"` strings. Re-run with `open_gui=True` and
  open Blender's System Console to follow along live.
- **Metal GPU didn't engage.** Check
  `report["render"]["apple_silicon_error"]`. Most common cause is running
  on an Intel Mac — edit `apple_silicon.enabled: false` in
  `configs/render/default.yaml`.
- **Intermediate `.blend` files take ~100 MB each.** The scene blend packs
  all appended assets. Wipe `tmp/` when you're done iterating.
- **`tmp/` or `output/` accidentally committed?** Both are listed in
  `.gitignore`; if git is tracking them, `git rm -r --cached tmp output`.
