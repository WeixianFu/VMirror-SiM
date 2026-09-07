# Changelog

All notable changes to VMirror-SiM. Follows [Keep a Changelog][kac]; dates
are ISO-8601 (local). "Unreleased" collects work not yet tagged.

[kac]: https://keepachangelog.com/en/1.1.0/

---

## [Unreleased]

### Fixed — model configuration and complete mirror framing

- Notebook defaults now come from the Python API; model dimensions remain the
  source of truth, with no real-vehicle rescaling or unsupported P50 claim.
- Select `node_0.001` for large2 rather than the duplicate large mesh.
- Towing mirrors start at 0.65 m extension and fit the actual vehicle/trailer
  side envelope with 50 mm clearance. Towing/electric assemblies include lower
  auxiliary glasses with separated vertical positions; glass geometry is unchanged.
- Camera framing fits all side-glass vertices with 5% image margins, including
  when the render aspect changes. Report actual lenses and image bounds.
- Apply YAML World on every render/preview and scene YAML Sun during assembly.
- Parent caravan/mirrors to the vehicle; use transformed eyes for reflection
  orientation and vehicle-local coordinates for main/auxiliary mirror export.
- Add `scripts/check_geometry.py` for actual-asset bilateral renders, clearance,
  environment, nonzero pose and export/reload checks. See `docs/configuration.md`.


### Added

**macOS / Linux development**
- Shared AUTO device selection for rendering and GUI previews: Metal on macOS,
  OptiX → CUDA → HIP → oneAPI on Linux, explicit CPU fallback on discovery failure.
- Device reports, strict GPU mode, CPU override, modern MetalRT support and
  backward-compatible legacy `apple_silicon` profiles.
- `VMIRROR_BLENDER_EXE` for machine-local Blender paths; early Linux desktop
  checks and GUI process-exit diagnostics.
- Hardware-independent device/launch regression tests, `scripts/check_platform.py`
  for real left/right renders and optional preview, and dual-platform setup guide.
- Default/wide profiles use a shared `device` block and CPU OIDN for consistent
  final/preview denoising settings; notebook displays the selected device.


**Pipeline — subprocess-based 7-step loader**
- `src/scene_builder.py` — `SceneBuilder` class (steps 1–4: scene / vehicle /
  caravan / mirrors).
- `src/camera_rig.py` — `CameraRig` class (step 5 + ego ray visibility).
- `src/renderer.py` — `Renderer` class (step 6c world + step 7 render profile;
  optional PNG render).
- `src/pipeline.py` — `SimulationPipeline` one-shot convenience that chains
  the three.
- `src/_common.py` — shared utilities (Blender auto-detect, yaml loader,
  subprocess runner, bpy prelude, `_project_mkdtemp`, `apply_timestamp`).
- Notebook-friendly: no Blender addon required, each stage spawns its own
  Blender subprocess.

**Mirror selection — per-side variants + explicit paths**
- `SceneBuilder(mirror_L=…, mirror_R=…)` for heterogeneous L/R classes
  (e.g. L = standard_convex, R = towing_wide_angle).
- `SceneBuilder(mirror_path_L=…, mirror_path_R=…)` for explicit yaml paths
  (used to re-consume `ConfigExporter` output).
- Resolution priority: `mirror_path_{side} > mirror_{side} > mirror (uniform)`.
- Aliases: `standard→standard_convex`, `towing→towing_main`,
  `electric→electric_main` (per-side accepted too).

**Mirror orientation policies**
- `orientation.policy: dynamic_reflection` (default) — runtime reflection
  law using `eye + mirror_target`.
- `orientation.policy: explicit` — verbatim bake of `rotation_euler_deg`.
- All 12 mirror yamls now ship both `policy` and a passat-referenced
  `rotation_euler_deg` so users can switch modes without re-deriving
  values.

**Camera variants + path-based selection**
- `CameraRig(camera="wide")` picks `cameras/driver_camera_wide_{side}.yaml`
  (150 mm, paired with `configs/render/wide.yaml` 2560 × 1440).
- `CameraRig(camera_path=…)` loads any yaml by absolute path.
- Full-name forms accepted: `"driver_camera_wide"` or
  `"driver_camera_wide_L"` (side suffix must match).
- `CameraRig(side="both")` places both L and R cameras in a single
  subprocess, enabling `Renderer.preview(layout="triple")`.
- `SimulationPipeline` auto-picks the render profile the camera yaml's
  `render_profile:` field points at — `camera="wide"` → `render/wide.yaml`
  (2560 × 1440) with no extra config.

**`Renderer.preview()` — live GUI viewport preview**
- Applies the render profile then flips the 3D viewport into a live
  preview. No PNG, no blend mutation unless the user `Ctrl+S`.
- `layout="single"` — every V3D area = camera + Rendered.
- `layout="split"` (default) — vertical split: left locked to camera
  (Rendered), right free-orbit (Solid). Uses a deferred
  `bpy.app.timers` callback; pre-split fallback so the window is never
  visually broken.
- `layout="triple"` — three panes (state-machine across two ticks to let
  Blender finalize each `area_split`): left-top binds L camera via
  `use_local_camera`, left-bottom binds R camera, right is the manipulation
  pane (Solid shading). Both camera panes use `view_camera_zoom = 18` so
  the frame fills ~70 % of the pane. Missing a camera → falls back to
  `split`.
- `right_view` parameter (split + triple) — start the manipulation pane in
  `top` (default, ortho top-down centered between ego and caravan), `front`,
  `side`, or `free` perspective. Implemented via
  `bpy.ops.view3d.view_axis` with a quaternion fallback if the operator
  rejects context.
- In GUI mode Blender stdout/stderr is captured to
  `tmp/vmirror_sim_*/blender_stdout.log`; the path comes back in the
  report dict as `_log_path` for debugging deferred callbacks.

**`ConfigExporter` — snapshot tuned blend → drop-in yaml bundle**
- `src/config_exporter.py` — probes the blend, reads current transforms
  + ray-visibility flags + camera intrinsics, writes yamls that mirror
  the top-level `configs/` layout under
  `output/tuned-configs/<vehicle>_<caravan>_side<L|R>_MMDD_HHMM/`.
- `mirror_mode="explicit"` (default and only mode so far) converts
  tweaked mirror rotations into `orientation.policy=explicit` +
  `rotation_euler_deg` that SceneBuilder consumes verbatim.
- Per-yaml baselines resolved from `scene["vmirror_*"]` metadata so
  heterogeneous mirror sources (e.g. L from tuning session, R from
  official config) are preserved.
- Round-trip verified: manual +10° tweak → export → re-consume via
  `mirror_path_L/R` reproduces the rotation to < 1 µ°.

**Output conventions**
- Renders go to `output/render-results/` with default
  `timestamp=True` → `_MMDD_HHMM` suffix before the extension.
- Intermediate `.blend` files live in `tmp/` (gitignored). `tmp/` is
  auto-created per run and cleaned up on headless completion.

### Changed

- Render profile split out from `cameras/driver_camera_*.yaml` into
  `configs/render/*.yaml`; camera yaml now points at it via
  `render_profile:` instead of carrying `engine` / `cycles` /
  `apple_silicon` inline. `world:` block also moved from camera yaml to
  render yaml.
- Mirror orientation convention changed from `z_axis = −outward_n`
  (mesh convex side = local −Z, relied on `Geometry.Backfacing` mix)
  to `z_axis = +outward_n` (mesh convex side = local +Z, Glossy on
  front). Mirror yamls' `rotation_euler_deg` reflects this convention.

### Configuration

- 4 vehicles (crv, hilux, passat, polo) — identical schema.
- 4 caravans (compact, middle, large, large2) — identical schema.
- 12 mirrors (6 classes × L/R) — identical schema, all carry
  `policy` + `rotation_euler_deg`.
- 4 cameras (driver_camera / driver_camera_wide × L/R) — identical
  schema, wide pair pairs with `render/wide.yaml`.
- 2 render profiles (default.yaml, wide.yaml) — identical schema.
- 4 scenes (highway, lane_change, parking, regulatory) — schema
  intentionally differs per scene (prop types specific to each).

### Documentation

- `docs/pipeline.md` — full usage guide for the four classes (8 sections).
- `docs/model_import.md` — authoritative 7-step loading procedure with
  yaml field tables.
- `docs/coordinates.md` — project-wide coordinate convention.

---

## Earlier

Pre-changelog era — see `git log` for the migration from monolithic
`simulation_builder.py` to the four-class pipeline documented above.
