# Model Import Guide

End-to-end loading procedure for VMirror-SiM scenes. Each section lists the
asset and the yaml fields it consumes.

---

## 1. Coordinate convention (project-wide)

All assets and configs share one frame:

| Axis | Direction              | Notes                                |
| ---- | ---------------------- | ------------------------------------ |
| +X   | right (passenger side) | LHD vehicles                          |
| +Y   | forward (vehicle nose) | scene Y > 0 ahead of ego              |
| +Z   | up                     | ground plane at Z = 0                 |

Origin (0, 0, 0) = vehicle front-axle ground projection = scene global origin.

Units: meters (linear), degrees (angles) — unless a field says otherwise.

---

## 2. Asset and config layout

```
assets/
  blender-scenes/   scene_highway.blend  scene_lane_change.blend
                    scene_parking.blend  scene_regulatory.blend
  blender-vehicle/  crv.blend  hilux.blend  passat.blend  polo.blend
  blender-caravan/  compact_caravan.blend  middle_caravan.blend
                    large_caravan.blend    large2_caravan.blend
  blender-mirror/   standard_convex_{L,R}.blend
                    towing_main_{L,R}.blend
                    electric_main_{L,R}.blend
                    electric_sub.blend          (shared L/R)
                    towing_wide_angle.blend     (shared L/R)
                    clip_on_blind_spot.blend    (shared L/R)
  blender-camera/   driver_camera.blend         (shared L/R)

configs/
  scenes/    {highway,lane_change,parking,regulatory}.yaml
  vehicles/  {crv,hilux,passat,polo}.yaml
  caravans/  {compact,middle,large,large2}.yaml
  mirrors/   12 yamls — one per side (L/R) for each of 6 mirror classes
  cameras/   driver_camera_{L,R}.yaml            (200 mm close-up, pairs with default.yaml)
             driver_camera_wide_{L,R}.yaml       (150 mm wide, pairs with wide.yaml)
  render/    default.yaml                        (1920 × 1080, for 200 mm close-up)
             wide.yaml                           (2560 × 1440, for 150 mm wide)
```

Each blend stores geometry/materials only; world placement and runtime
behaviour come from yaml.

---

## 3. Loading dependency graph

```
Scene  ──→  Vehicle  ──→  Caravan
                  │
                  ├──→  Mirror_L  ──┐
                  ├──→  Mirror_R  ──┤
                  │                 │
                  └──→  Camera_L/R ─┘  (Track-To → Mirror_{L|R})
                            │
                            └──→  Render setup (engine / world / ray vis)
```

Strict order:

1. **Scene** — establishes the world (Z = 0 ground, road geometry).
2. **Vehicle** — positioned at world origin; fixes mount points and eye.
3. **Caravan** — positioned at the vehicle's hitch ground projection.
4. **Mirrors** — positioned relative to vehicle's mount points.
5. **Camera** — parented to the vehicle, oriented to a side mirror.
6. **Scene setup** — world background, ego ray visibility, mirror smooth
   shading (from camera yaml's `scene_setup`).
7. **Render profile** — engine, sampling, output resolution, GPU
   acceleration (from `render/<profile>.yaml` referenced by the camera).

Steps 1–5 are `append` operations from the corresponding `.blend`. Steps
6–7 configure the scene/render engine and do not load assets.

---

## 4. Step-by-step procedure

### 4.1 Scene

Append all objects + collections from the chosen scene blend, with identity
transform.

| Asset (any of)        | yaml                     | Fields actually used                     |
| --------------------- | ------------------------ | ---------------------------------------- |
| `scene_highway.blend` | `scenes/highway.yaml`    | `source_blend` (only)                    |
| `scene_lane_change.blend` | `scenes/lane_change.yaml` | `source_blend`                       |
| `scene_parking.blend` | `scenes/parking.yaml`    | `source_blend`                           |
| `scene_regulatory.blend` | `scenes/regulatory.yaml` | `source_blend`                       |

The other yaml fields (`bounds`, `lanes`, `marking_x_centers`,
`approaching_vehicles`, etc.) are *informational* — they document what the
blend already contains. Loaders may use them for validation but no transform
is applied based on them.

Scene blends ship without a World shader; one must be added at scene-setup
time (see §4.6).

### 4.2 Vehicle (ego)

Append the single mesh `node_0` from the vehicle blend at the scene origin.

| yaml field              | Purpose                                          |
| ----------------------- | ------------------------------------------------ |
| `source_blend`          | path to vehicle .blend (`assets/blender-vehicle/<name>.blend`) |
| `origin.position`       | world placement, always `(0, 0, 0)`              |
| `origin.rotation`       | world rotation, always `(0, 0, 0)`               |
| `mirror_mount.left`     | local point on driver-side A-pillar (used by mirrors) |
| `mirror_mount.right`    | local point on passenger-side A-pillar               |
| `eye_point`             | driver eye position (used by camera and reflection law) |
| `hitch_ground_projection` | ground point under tow ball (used by caravan)   |

`bounds` and `dimensions` are informational.

### 4.3 Caravan

Append `node_0` from the caravan blend. Set `object.location` =
`vehicle.hitch_ground_projection`. The caravan's own origin is its
coupler's ground projection (Z = 0), so the alignment puts the trailer onto
the same ground plane as the vehicle.

| yaml field        | Purpose                                         |
| ----------------- | ----------------------------------------------- |
| `source_blend`    | path to caravan .blend                          |
| `coupler.ground_projection` | always `[0, 0, 0]` (= caravan origin) |
| `coupler.ball_height`       | `0.420` m (ISO 50 mm ball; reference) |
| `bounds.y` / `dimensions`   | informational                       |

The caravan mesh has its drawbar tip ~0.10 m forward of its origin (intentional
overlap with vehicle hitch to close the gap to ~0.10–0.20 m).

### 4.4 Mirrors

For each side `{L, R}`, load the corresponding mirror yaml. Two assets exist:
six classes have separate `*_L.blend` / `*_R.blend`; three classes share one
`.blend` (electric_sub, towing_wide_angle, clip_on_blind_spot).

| Mirror yaml field           | Purpose                                       |
| --------------------------- | --------------------------------------------- |
| `source_blend`              | path to mirror .blend                         |
| `source_object`             | mesh name inside the blend (e.g. `Mirror_Glass_StandardConvex_L`) |
| `glass_size.{width,height,bump}` | glass dimensions (informational)         |
| `geometry.shape`            | always `analytical_sphere`                    |
| `geometry.sphere_radius`    | derived from bump and half-diagonal (informational) |
| `geometry.mesh_resolution`  | `[256, 256]` (informational)                  |
| `glass_center_offset.vector` | `[dx, dy, dz]` from mount to glass center, in vehicle-aligned axes |
| `glass_center_offset.{lateral, forward, rise}` | scalar form of `vector` (sign embedded in `vector`) |
| `orientation.policy`        | `dynamic_reflection` (runtime reflection law) or `explicit` (baked `rotation_euler_deg`) |
| `orientation.rotation_euler_deg` | `[rx, ry, rz]` in degrees — used verbatim when `policy=explicit`; when `policy=dynamic_reflection` it is a **passat-referenced** snapshot (informational) |
| `placement.strategy`        | `object_at_glass_world_position` (DO NOT shift mesh) |
| `material.*`                | informational; baked into the blend           |

**Placement** (per side):
```
glass_world = vehicle.mirror_mount.<side> + glass_center_offset.vector
object.location       = glass_world
if policy == "explicit":
    object.rotation_euler = radians(rotation_euler_deg)          # verbatim bake
else:   # dynamic_reflection
    object.rotation_euler = mirror_orientation(glass_world,
                                               vehicle.eye_point, target)
```

`target` is the world point the mirror should aim at (default
`(0, -20, 0.5)` for both sides; can be customized per scenario).

Use `explicit` when you have manually adjusted a mirror in the GUI and want
that exact rotation preserved regardless of eye/target — `ConfigExporter`
emits this mode automatically after a manual tweak. `dynamic_reflection`
remains the default for fresh scenes; in that mode the `rotation_euler_deg`
field is documentation only (records the reflection-law answer at the
canonical passat pose).

**`mirror_orientation` (reflection law)**:
```
to_eye    = normalize(eye    − glass_world)
to_target = normalize(target − glass_world)
outward_n = normalize(to_eye + to_target)        # outward reflection normal

# Mesh convention: the analytical-sphere mesh is a single-sided dome whose
# bulge points local +Z (center at Z = bump, rim at Z = 0). Face normals
# also point local +Z — i.e., outward from the convex/reflective face.
# The rotation aligns local +Z with the outward reflection normal so the
# convex side faces the driver and the camera sees the front face.
z_axis = +outward_n                              # local +Z direction in world
x_axis = normalize(world_up × z_axis)
y_axis = z_axis × x_axis
rotation_matrix = [x_axis | y_axis | z_axis]
```

**Why this exact procedure** — every part is load-bearing:
- The mesh ships at the object origin; `placement.strategy` requires
  *no* mesh translation. Translating the mesh would couple the offset to
  the rotation and place the glass somewhere unintended.
- The mesh is a 256×256 analytical-sphere grid (single-sided dome, bulge
  toward local +Z; Z = bump at center, Z = 0 at rim). Face normals point
  +Z (outward from the convex side). Earlier low-poly mirrors produced
  visible facet stripes through curved reflection; the dense analytical
  mesh provides a near-continuous normal field so `glossy_roughness = 0`
  works cleanly.
- The mirror material uses
  `Mix Shader(factor = Geometry.Backfacing)` to route shaders:
  - front face (normal points toward camera; the convex side)
    → **Glossy** (reflective mirror)
  - back face (normal points away; inside of the shell)
    → **Diffuse** (dark back shell)

  Combined with `z_axis = +outward_n`, the camera always lands on the
  front-face/convex side, so it sees the Glossy reflection with convex
  wide-angle optics (surface curves toward the viewer, center closest,
  rim further — compressed FOV, wide field of view).

### 4.5 Camera

Append `DriverCam` from `assets/blender-camera/driver_camera.blend`. Parent
to the ego, place at the eye point, attach a Track-To constraint to the
desired side mirror.

| Camera yaml field                | Purpose                                  |
| -------------------------------- | ---------------------------------------- |
| `source_blend`, `source_object`  | the shared 200 mm telephoto camera asset |
| `render_profile`                 | path to the render-profile yaml (e.g. `configs/render/default.yaml`) — engine/sampling/output/GPU settings live there |
| `placement.strategy`             | `parent_to_vehicle_at_eye`               |
| `placement.local_position_source`| `vehicle.eye_point` (read from vehicle yaml) |
| `placement.local_rotation_euler_deg` | always `[0, 0, 0]` — superseded by Track-To |
| `track_to.target_object_name_pattern` | `{vehicle_prefix}_Mirror_{L\|R}` — the runtime mirror object name |
| `track_to.track_axis`            | `NEG_Z`                                  |
| `track_to.up_axis`               | `Y`                                      |
| `lens.focal_length_mm`           | `200` (camera intrinsic — kept here)     |
| `lens.sensor_width_mm`           | `36.0`                                   |
| `lens.clip_start_m`/`clip_end_m` | `0.10` / `500.0`                         |

The camera yaml intentionally carries **no** render-engine settings — those
come from the referenced render profile (§4.7).

Pseudocode:
```python
cam = append(camera_yaml.source_blend, camera_yaml.source_object, name="DriverCam_L")
cam.parent          = ego
cam.location        = vehicle_yaml.eye_point
cam.rotation_euler  = (0, 0, 0)
con                 = cam.constraints.new('TRACK_TO')
con.target          = bpy.data.objects[f"{prefix}_Mirror_L"]
con.track_axis      = 'TRACK_NEGATIVE_Z'
con.up_axis         = 'UP_Y'
scene.camera        = cam
```

### 4.6 Scene-state setup (from camera yaml)

The camera yaml's `scene_setup` block lists **scene state** that must be
applied at render time (they are *not* baked into any asset). Engine /
sampling / world settings are NOT here — they live in the render profile
(§4.7).

| `scene_setup` field             | Required value          | Why                                       |
| ------------------------------- | ----------------------- | ----------------------------------------- |
| `ego_ray_visibility.visible_camera`     | `false`         | camera at driver's eye looks through the cabin to the side mirror without the body blocking |
| `ego_ray_visibility.visible_glossy`     | `true`          | the body still appears in the mirror's reflection |
| `ego_ray_visibility.visible_shadow`     | `true`          | the body still casts ground shadows       |
| `mirror_shading.use_smooth`             | `true`          | safety against any flat-shade regression |

Apply with:
```python
ego.visible_camera   = False
# (other ray flags already default to True; set explicitly for clarity)
for m in (mirror_L, mirror_R):
    for p in m.data.polygons: p.use_smooth = True
```

### 4.7 Render profile

The camera's `render_profile` field points at a yaml under `configs/render/`
(default: `default.yaml`). One render profile is shared by all cameras so
that engine / sampling / GPU settings can be tuned project-wide.

| Render yaml field               | Purpose                                    |
| ------------------------------- | ------------------------------------------ |
| `engine`                        | **must be `CYCLES`** — EEVEE cannot render the convex-mirror reflections |
| `output.{resolution_x, resolution_y, resolution_percentage}` | `1920 × 1080 × 100%` (default) / `2560 × 1440 × 100%` (wide) |
| `cycles.samples` / `preview_samples`  | `512` / `128`                         |
| `cycles.max_bounces`            | `12`                                       |
| `cycles.glossy_bounces`         | `6` (supports mirror-in-mirror reflections)|
| `cycles.transmission_bounces`   | `4`                                        |
| `cycles.adaptive_sampling.{enabled, threshold, min_samples}` | `true` / `0.01` / `0` |
| `cycles.use_denoising`          | `true`                                     |
| `cycles.denoiser`               | `OPENIMAGEDENOISE`                         |
| `cycles.denoising_use_gpu`      | `true` (OIDN 2.0+ on Metal; Blender 4.1+)  |
| `cycles.pixel_filter_type`      | `BLACKMAN_HARRIS`                          |
| `cycles.filter_width`           | `1.5`                                      |
| `apple_silicon.enabled`         | `true` — turn the Metal/RT block on/off    |
| `apple_silicon.compute_device_type` | `METAL`                                |
| `apple_silicon.use_metalrt`     | `true` — M3-series hardware ray tracing (M1/M2 ignore) |
| `apple_silicon.cycles_device`   | `GPU`                                      |
| `apple_silicon.select_all_metal_devices` | `true`                            |
| `persistent_data`               | `true` (keep BVH/shaders between frames)   |
| `clamp.{direct, indirect}`      | `0.0` / `0.0`                              |
| `world.{type, color, strength}` | `sky_background` / `[0.55, 0.70, 0.95]` / `1.5` — applied only when the loaded scene has no World |

Apply (pseudocode):
```python
rp = load_yaml(camera_yaml.render_profile)
prefs = bpy.context.preferences.addons['cycles'].preferences
if rp.apple_silicon.enabled:
    prefs.compute_device_type = rp.apple_silicon.compute_device_type
    for d in prefs.devices:
        d.use = (d.type == rp.apple_silicon.compute_device_type)
    prefs.use_metalrt = rp.apple_silicon.use_metalrt
    scene.cycles.device = rp.apple_silicon.cycles_device
    scene.cycles.denoising_use_gpu = rp.cycles.denoising_use_gpu

scene.render.engine                = rp.engine
scene.render.resolution_x          = rp.output.resolution_x
scene.render.resolution_y          = rp.output.resolution_y
scene.render.resolution_percentage = rp.output.resolution_percentage
scene.render.use_persistent_data   = rp.persistent_data
scene.cycles.samples               = rp.cycles.samples
scene.cycles.max_bounces           = rp.cycles.max_bounces
scene.cycles.glossy_bounces        = rp.cycles.glossy_bounces
scene.cycles.use_adaptive_sampling = rp.cycles.adaptive_sampling.enabled
scene.cycles.adaptive_threshold    = rp.cycles.adaptive_sampling.threshold
scene.cycles.use_denoising         = rp.cycles.use_denoising
scene.cycles.denoiser              = rp.cycles.denoiser
scene.cycles.pixel_filter_type     = rp.cycles.pixel_filter_type
scene.cycles.filter_width          = rp.cycles.filter_width
scene.cycles.sample_clamp_direct   = rp.clamp.direct
scene.cycles.sample_clamp_indirect = rp.clamp.indirect
```

Additional profiles (e.g. `preview.yaml` with lower samples, `analysis.yaml`
with higher samples and off denoiser for inspection) can live alongside
`default.yaml` and be selected by changing the camera yaml's
`render_profile` field.

**Camera + profile pairings** (shipped):

| Camera yaml                     | Render profile               | Lens    | FOV (H)  | Output         | Purpose                              |
| ------------------------------- | ---------------------------- | ------- | -------- | -------------- | ------------------------------------ |
| `driver_camera_{L,R}.yaml`      | `render/default.yaml`        | 200 mm  | ≈ 10.3°  | 1920 × 1080    | close-up (mirror fills frame)        |
| `driver_camera_wide_{L,R}.yaml` | `render/wide.yaml`           | 150 mm  | ≈ 13.7°  | 2560 × 1440    | wide (~30 % more context around mirror; same per-pixel angular resolution on mirror region as close-up) |

---

## 5. Cross-yaml fields used at each step (quick lookup)

| Step           | Reads from yaml…                                                          |
| -------------- | ------------------------------------------------------------------------- |
| Scene          | `scenes/<name>.source_blend`                                              |
| Vehicle        | `vehicles/<name>.{source_blend, origin.position, mirror_mount.{left,right}, eye_point, hitch_ground_projection}` |
| Caravan        | `caravans/<name>.source_blend`  +  vehicle.`hitch_ground_projection`     |
| Mirrors        | `mirrors/<name>_<side>.{source_blend, source_object, glass_center_offset.vector}`  +  vehicle.`{mirror_mount.<side>, eye_point}`  +  scene-defined `target` |
| Camera         | `cameras/driver_camera_<side>.{source_blend, source_object, placement, track_to, lens, scene_setup, render_profile}`  +  vehicle.`eye_point`  +  the mirror object placed in the previous step |
| Render profile | `render/<profile>.{engine, output, cycles, apple_silicon, persistent_data, clamp}`  (path from camera.`render_profile`) |

Vehicle yaml fields are read **once** and re-used across mirrors and camera —
keep one in-memory dict per vehicle. The render profile is also loaded once
and applied at the final step.

---

## 6. End-to-end pseudocode

```python
veh_cfg     = load_yaml(f"configs/vehicles/{vehicle_name}.yaml")
caravan_cfg = load_yaml(f"configs/caravans/{caravan_name}.yaml")   # optional
scene_cfg   = load_yaml(f"configs/scenes/{scene_name}.yaml")
mir_L_cfg   = load_yaml(f"configs/mirrors/{mirror_class}_L.yaml")
mir_R_cfg   = load_yaml(f"configs/mirrors/{mirror_class}_R.yaml")
cam_cfg     = load_yaml(f"configs/cameras/driver_camera_{side}.yaml")  # 'L' or 'R'
render_cfg  = load_yaml(cam_cfg.render_profile)                    # e.g. configs/render/default.yaml

# 1) Scene
load_scene(scene_cfg.source_blend)

# 2) Vehicle
ego = append_mesh(veh_cfg.source_blend, "node_0", new_name=f"{prefix}_ego",
                  loc=veh_cfg.origin.position)

# 3) Caravan (optional)
if caravan_cfg:
    append_mesh(caravan_cfg.source_blend, "node_0", new_name="Caravan",
                loc=veh_cfg.hitch_ground_projection)

# 4) Mirrors
for side, mc in (("L", mir_L_cfg), ("R", mir_R_cfg)):
    mount  = veh_cfg.mirror_mount[side.lower()]
    glass  = vec_add(mount, mc.glass_center_offset.vector)
    mirror = append_mesh(mc.source_blend, mc.source_object,
                         new_name=f"{prefix}_Mirror_{side}", loc=glass)
    mirror.rotation_euler = mirror_orientation(
        glass, veh_cfg.eye_point, target=(0, -20, 0.5))

# 5) Camera (one side)
cam = append_object(cam_cfg.source_blend, cam_cfg.source_object,
                    new_name=f"{prefix}_DriverCam_{side}")
cam.parent          = ego
cam.location        = veh_cfg.eye_point
cam.rotation_euler  = (0, 0, 0)
target_name         = cam_cfg.track_to.target_object_name_pattern.format(
                          vehicle_prefix=prefix)
con                 = cam.constraints.new('TRACK_TO')
con.target          = scene_objects[target_name]
con.track_axis      = 'TRACK_NEGATIVE_Z'
con.up_axis         = 'UP_Y'
scene.camera        = cam

# 6) Scene-state setup (from cam_cfg.scene_setup)
ego.visible_camera = cam_cfg.scene_setup.ego_ray_visibility.visible_camera
for m in (mirror_L, mirror_R):
    for p in m.data.polygons: p.use_smooth = cam_cfg.scene_setup.mirror_shading.use_smooth
if scene.world is None:
    create_sky_world(cam_cfg.scene_setup.world.color,
                     cam_cfg.scene_setup.world.strength)

# 7) Render profile (from render_cfg — engine + sampling + GPU)
apply_render_profile(scene, render_cfg)     # body listed under §4.7
```

---

## 7. Invariants the loader must preserve

- **Engine = CYCLES** at render time. EEVEE's SSR cannot render the convex
  mirror reflections faithfully.
- **Mirror mesh is never translated** — only the object location and rotation
  change. Translating mesh vertices breaks `placement.strategy`.
- **Mirror smooth shading on all polygons** — protected at runtime even
  though the assets ship smooth-shaded.
- **Vehicle visible_camera = False, visible_glossy = True** — driver-eye
  camera sees through the cabin while the body still appears in the mirror.
- **World shader present** — adds the sky reflection that the mirror needs
  to look natural.
