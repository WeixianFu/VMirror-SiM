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
  cameras/   driver_camera_{L,R}.yaml
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
6. **Scene setup** — engine, world background, ego ray visibility,
   mirror smooth shading.

Each step is an `append` from the corresponding `.blend`.

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
| `orientation.policy`        | `dynamic_reflection` (sets via reflection law) |
| `placement.strategy`        | `object_at_glass_world_position` (DO NOT shift mesh) |
| `material.*`                | informational; baked into the blend           |

**Placement** (per side):
```
glass_world = vehicle.mirror_mount.<side> + glass_center_offset.vector
object.location       = glass_world
object.rotation_euler = mirror_orientation(glass_world, vehicle.eye_point, target)
```

`target` is the world point the mirror should aim at (default
`(0, -20, 0.5)` for both sides; can be customized per scenario).

**`mirror_orientation` (reflection law)**:
```
to_eye    = normalize(eye    − glass_world)
to_target = normalize(target − glass_world)
outward_n = normalize(to_eye + to_target)        # outward reflection normal

# Mesh convention: the analytical-sphere mesh is a single-sided dome with
# face normals pointing local +Z. The rotation below makes local +Z point
# AWAY from the outward reflection normal, so the camera always views the
# mesh from the side where face normals point away from it (the back-face).
z_axis = -outward_n                              # local +Z direction in world
x_axis = normalize(world_up × z_axis)
y_axis = z_axis × x_axis
rotation_matrix = [x_axis | y_axis | z_axis]
```

**Why this exact procedure** — every part is load-bearing:
- The mesh ships at the object origin; `placement.strategy` requires
  *no* mesh translation. Translating the mesh would couple the offset to
  the rotation and place the glass somewhere unintended.
- The mesh is a 256×256 analytical-sphere grid (single-sided dome,
  Z = bump at center, Z = 0 at rim). Earlier low-poly mirrors produced
  visible facet stripes through curved reflection; the dense analytical
  mesh provides a near-continuous normal field so `glossy_roughness = 0`
  works cleanly.
- The mirror material uses
  `Mix Shader(factor = Geometry.Backfacing)` to route shaders:
  - front face (camera sees the side face normals point toward)
    → **Diffuse** (dark back shell)
  - back face (camera sees the side face normals point away from)
    → **Glossy** (reflective mirror)

  Combined with `z_axis = −outward_n`, the camera always lands on the
  back-face side, so it sees the Glossy reflection. The surface curves
  AWAY from the camera (center furthest, rim closest), which is the
  optical definition of a convex mirror — wide FOV, compressed image.

### 4.5 Camera

Append `DriverCam` from `assets/blender-camera/driver_camera.blend`. Parent
to the ego, place at the eye point, attach a Track-To constraint to the
desired side mirror.

| Camera yaml field                | Purpose                                  |
| -------------------------------- | ---------------------------------------- |
| `source_blend`, `source_object`  | the shared 200 mm telephoto camera asset |
| `placement.strategy`             | `parent_to_vehicle_at_eye`               |
| `placement.local_position_source`| `vehicle.eye_point` (read from vehicle yaml) |
| `placement.local_rotation_euler_deg` | always `[0, 0, 0]` — superseded by Track-To |
| `track_to.target_object_name_pattern` | `{vehicle_prefix}_Mirror_{L\|R}` — the runtime mirror object name |
| `track_to.track_axis`            | `NEG_Z`                                  |
| `track_to.up_axis`               | `Y`                                      |
| `lens.focal_length_mm`           | `200`                                    |
| `lens.sensor_width_mm`           | `36.0`                                   |
| `lens.clip_start_m`/`clip_end_m` | `0.10` / `500.0`                         |
| `output.{resolution_x, resolution_y, resolution_percentage}` | `1920 × 1080 × 100%` |
| `render.engine`                  | **must be `CYCLES`**                     |
| `render.cycles.samples`          | `512` (final), `128` (preview)           |
| `render.cycles.glossy_bounces`   | `6` (supports mirror-in-mirror)          |
| `render.cycles.use_denoising`    | `true`                                   |

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

### 4.6 Render-time scene setup

The camera yaml's `scene_setup` block lists conditions that must be applied
at render time (they are *not* baked into any asset):

| `scene_setup` field             | Required value          | Why                                       |
| ------------------------------- | ----------------------- | ----------------------------------------- |
| `ego_ray_visibility.visible_camera`     | `false`         | camera at driver's eye looks through the cabin to the side mirror without the body blocking |
| `ego_ray_visibility.visible_glossy`     | `true`          | the body still appears in the mirror's reflection |
| `ego_ray_visibility.visible_shadow`     | `true`          | the body still casts ground shadows       |
| `mirror_shading.use_smooth`             | `true`          | safety against any flat-shade regression |
| `world.type` / `color` / `strength`     | `sky_background` / `[0.55, 0.70, 0.95]` / `1.5` | scene blends ship with no World; reflections need an environment to sample |
| `render.engine`                         | `CYCLES`        | EEVEE's screen-space reflections are not faithful for this setup |

Apply with:
```python
ego.visible_camera   = False
# (other ray flags already default to True; set explicitly for clarity)
for m in (mirror_L, mirror_R):
    for p in m.data.polygons: p.use_smooth = True
if scene.world is None:
    # build a background-only world with [0.55, 0.70, 0.95] @ 1.5
    ...
scene.render.engine = 'CYCLES'
scene.cycles.samples         = camera_yaml.render.cycles.samples
scene.cycles.glossy_bounces  = camera_yaml.render.cycles.glossy_bounces
scene.cycles.use_denoising   = camera_yaml.render.cycles.use_denoising
```

---

## 5. Cross-yaml fields used at each step (quick lookup)

| Step       | Reads from yaml…                                                          |
| ---------- | ------------------------------------------------------------------------- |
| Scene      | `scenes/<name>.source_blend`                                              |
| Vehicle    | `vehicles/<name>.{source_blend, origin.position, mirror_mount.{left,right}, eye_point, hitch_ground_projection}` |
| Caravan    | `caravans/<name>.source_blend`  +  vehicle.`hitch_ground_projection`     |
| Mirrors    | `mirrors/<name>_<side>.{source_blend, source_object, glass_center_offset.vector}`  +  vehicle.`{mirror_mount.<side>, eye_point}`  +  scene-defined `target` |
| Camera     | `cameras/driver_camera_<side>.{source_blend, source_object, lens, output, render, scene_setup}`  +  vehicle.`eye_point`  +  the mirror object placed in the previous step |

Vehicle yaml fields are read **once** and re-used across mirrors and camera —
keep one in-memory dict per vehicle.

---

## 6. End-to-end pseudocode

```python
veh_cfg     = load_yaml(f"configs/vehicles/{vehicle_name}.yaml")
caravan_cfg = load_yaml(f"configs/caravans/{caravan_name}.yaml")   # optional
scene_cfg   = load_yaml(f"configs/scenes/{scene_name}.yaml")
mir_L_cfg   = load_yaml(f"configs/mirrors/{mirror_class}_L.yaml")
mir_R_cfg   = load_yaml(f"configs/mirrors/{mirror_class}_R.yaml")
cam_cfg     = load_yaml(f"configs/cameras/driver_camera_{side}.yaml")  # 'L' or 'R'

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

# 6) Render setup (from cam_cfg.scene_setup and cam_cfg.render)
ego.visible_camera          = cam_cfg.scene_setup.ego_ray_visibility.visible_camera
for m in (mirror_L, mirror_R):
    for p in m.data.polygons: p.use_smooth = cam_cfg.scene_setup.mirror_shading.use_smooth
if scene.world is None:
    create_sky_world(cam_cfg.scene_setup.world.color,
                     cam_cfg.scene_setup.world.strength)
scene.render.engine          = cam_cfg.render.engine            # CYCLES
scene.cycles.samples         = cam_cfg.render.cycles.samples
scene.cycles.glossy_bounces  = cam_cfg.render.cycles.glossy_bounces
scene.cycles.use_denoising   = cam_cfg.render.cycles.use_denoising
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
