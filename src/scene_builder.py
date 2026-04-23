"""SceneBuilder — assemble the geometric scene (steps 1-4 of model_import.md).

Scope
-----
1. Scene     — append the scene blend (road, markings, approaching vehicles)
2. Vehicle   — append ``node_0`` at origin
3. Caravan   — optional, positioned at vehicle.hitch_ground_projection
4. Mirrors   — L + R, placed at mount + glass_center_offset, oriented via
               reflection law (``z_axis = +outward_n``), smooth-shaded

Output: a ``.blend`` file that downstream tools (CameraRig → Renderer) open.
No camera, no world, no render settings are touched here.

Notebook usage
--------------
    from src import SceneBuilder
    report = SceneBuilder(
        scene="lane_change", vehicle="hilux",
        caravan="large2", mirror="standard",
    ).build(output="/tmp/step1_scene.blend")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._common import (
    BPY_COMMON_PRELUDE,
    MIRROR_ALIASES,
    _project_mkdtemp,
    abs_blend,
    find_blender,
    load_yaml,
    load_yaml_abs,
    run_blender_script,
)

DEFAULT_MIRROR_TARGET = (0.0, -20.0, 0.5)


def _mirror_payload_entry(cfg: dict) -> dict:
    """Pack one mirror yaml into the flat payload dict the subprocess eats.

    Honors ``orientation.policy`` — ``"explicit"`` ships a bake rotation;
    anything else defaults to ``"dynamic_reflection"`` (reflection law).
    """
    orientation = cfg.get("orientation", {})
    policy = orientation.get("policy", "dynamic_reflection")
    entry = {
        "blend":               abs_blend(cfg["source_blend"]),
        "source_object":       cfg["source_object"],
        "glass_center_offset": list(cfg["glass_center_offset"]["vector"]),
        "orientation_policy":  policy,
    }
    if policy == "explicit":
        try:
            entry["rotation_euler_deg"] = list(orientation["rotation_euler_deg"])
        except KeyError as exc:
            raise RuntimeError(
                f"mirror yaml has orientation.policy=explicit but no "
                f"rotation_euler_deg: {cfg.get('model', cfg)}"
            ) from exc
    return entry


def _resolve_mirror_yaml(
    side: str,
    uniform: str,
    side_variant: str | None,
    side_path: str | None,
) -> tuple[dict, str]:
    """Load a mirror yaml for one side. Priority: side_path > side_variant > uniform.

    Returns ``(cfg, source_label)`` where ``source_label`` is a human-readable
    string used in reports/exports (e.g. ``"path:/abs/foo.yaml"`` or
    ``"name:standard_convex"``).
    """
    if side_path:
        return load_yaml_abs(side_path), f"path:{side_path}"
    name = side_variant if side_variant else uniform
    name = MIRROR_ALIASES.get(name, name)
    if name.endswith("_L") or name.endswith("_R"):
        if name[-1] != side:
            raise ValueError(
                f"mirror name {name!r} ends with _{name[-1]} but side={side!r}"
            )
        return load_yaml(f"mirrors/{name}.yaml"), f"name:{name[:-2]}"
    return load_yaml(f"mirrors/{name}_{side}.yaml"), f"name:{name}"


class SceneBuilder:
    def __init__(
        self,
        scene: str = "lane_change",
        vehicle: str = "passat",
        caravan: str | None = None,
        mirror: str = "standard",            # uniform default (alias ok)
        mirror_L: str | None = None,         # override left side only
        mirror_R: str | None = None,         # override right side only
        mirror_path_L: str | None = None,    # absolute yaml path, left
        mirror_path_R: str | None = None,    # absolute yaml path, right
        mirror_target: tuple[float, float, float] = DEFAULT_MIRROR_TARGET,
        clear_scene: bool = True,
        blender_exe: str | None = None,
    ):
        self.scene = scene
        self.vehicle = vehicle
        self.caravan = caravan
        self.mirror = MIRROR_ALIASES.get(mirror, mirror)
        self.mirror_target = tuple(float(v) for v in mirror_target)
        self.clear_scene = clear_scene
        self.blender_exe = find_blender(blender_exe)

        self.scene_cfg = load_yaml(f"scenes/{self.scene}.yaml")
        self.vehicle_cfg = load_yaml(f"vehicles/{self.vehicle}.yaml")
        self.caravan_cfg = (
            load_yaml(f"caravans/{self.caravan}.yaml")
            if self.caravan else None
        )
        self.mirror_L_cfg, self.mirror_L_source = _resolve_mirror_yaml(
            "L", self.mirror, mirror_L, mirror_path_L,
        )
        self.mirror_R_cfg, self.mirror_R_source = _resolve_mirror_yaml(
            "R", self.mirror, mirror_R, mirror_path_R,
        )

    def _build_payload(self, output_blend: str, report_path: str) -> dict[str, Any]:
        v = self.vehicle_cfg
        mL = self.mirror_L_cfg
        mR = self.mirror_R_cfg
        return {
            "report_path":   report_path,
            "output_blend":  output_blend,
            "clear_scene":   self.clear_scene,
            "scene_blend":   abs_blend(self.scene_cfg["source_blend"]),
            "vehicle": {
                "name":  v["model"],
                "blend": abs_blend(v["source_blend"]),
                "origin_position":     list(v["origin"]["position"]),
                "origin_rotation_deg": list(v["origin"]["rotation"]),
                "mirror_mount": {
                    "left":  list(v["mirror_mount"]["left"]),
                    "right": list(v["mirror_mount"]["right"]),
                },
                "eye_point":               list(v["eye_point"]),
                "hitch_ground_projection": list(v["hitch_ground_projection"]),
            },
            "caravan": (
                None if self.caravan_cfg is None else {
                    "name":  self.caravan_cfg["model"],
                    "blend": abs_blend(self.caravan_cfg["source_blend"]),
                }
            ),
            "mirrors": {
                "L": _mirror_payload_entry(mL),
                "R": _mirror_payload_entry(mR),
            },
            "mirror_target": list(self.mirror_target),
            "metadata": {
                "scene":   self.scene,
                "vehicle": self.vehicle,
                "caravan": self.caravan,
                "mirror":  self.mirror,
                "mirror_L_source": self.mirror_L_source,
                "mirror_R_source": self.mirror_R_source,
            },
        }

    def build(
        self,
        output: str | Path,
        open_gui: bool = False,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        output_blend = str(Path(output).resolve())
        report_path = _project_mkdtemp("scene_builder_") / "report.json"
        payload_json = json.dumps(
            self._build_payload(output_blend, str(report_path))
        )
        script = (
            BPY_COMMON_PRELUDE
            + _SCENE_BUILDER_BODY.replace("__PAYLOAD_JSON__", payload_json)
        )
        return run_blender_script(
            self.blender_exe, script, report_path,
            open_gui=open_gui, timeout=timeout,
        )


_SCENE_BUILDER_BODY = r'''

payload = json.loads(r"""__PAYLOAD_JSON__""")
report = {"step": "scene_builder", "scene": None, "vehicle": None,
          "caravan": None, "mirrors": {}}


def _mirror_rotation_euler(glass_world, eye_world, target_world):
    g = Vector(glass_world)
    to_eye = (Vector(eye_world)    - g).normalized()
    to_tgt = (Vector(target_world) - g).normalized()
    outward_n = (to_eye + to_tgt).normalized()
    z_axis = outward_n
    world_up = Vector((0.0, 0.0, 1.0))
    if abs(z_axis.dot(world_up)) > 0.999:
        world_up = Vector((0.0, 1.0, 0.0))
    x_axis = world_up.cross(z_axis).normalized()
    y_axis = z_axis.cross(x_axis).normalized()
    mat = Matrix((
        (x_axis.x, y_axis.x, z_axis.x, 0.0),
        (x_axis.y, y_axis.y, z_axis.y, 0.0),
        (x_axis.z, y_axis.z, z_axis.z, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))
    return mat.to_euler("XYZ")


def _build():
    if payload.get("clear_scene", True):
        _clear_scene()

    # 1) Scene
    report["scene"] = _append_scene(payload["scene_blend"])

    # 2) Vehicle
    v = payload["vehicle"]
    prefix = v["name"]
    ego = _append_single(v["blend"], "node_0", new_name=prefix + "_ego")
    ego.location = Vector(v["origin_position"])
    ego.rotation_euler = tuple(math.radians(a) for a in v["origin_rotation_deg"])
    report["vehicle"] = {"object": ego.name, "location": list(ego.location)}

    # 3) Caravan (optional)
    if payload.get("caravan"):
        c = payload["caravan"]
        caravan = _append_single(c["blend"], "node_0",
                                 new_name="Caravan_" + c["name"])
        caravan.location = Vector(v["hitch_ground_projection"])
        caravan.rotation_euler = (0.0, 0.0, 0.0)
        report["caravan"] = {"object": caravan.name,
                             "location": list(caravan.location)}

    # 4) Mirrors L+R
    target = payload["mirror_target"]
    eye_world = v["eye_point"]
    for side in ("L", "R"):
        m = payload["mirrors"][side]
        mount = v["mirror_mount"]["left" if side == "L" else "right"]
        offset = m["glass_center_offset"]
        glass_world = [mount[i] + offset[i] for i in range(3)]
        obj = _append_single(m["blend"], m["source_object"],
                             new_name=prefix + "_Mirror_" + side)
        obj.location = Vector(glass_world)
        policy = m.get("orientation_policy", "dynamic_reflection")
        if policy == "explicit":
            deg = m["rotation_euler_deg"]
            obj.rotation_euler = tuple(math.radians(a) for a in deg)
        else:
            obj.rotation_euler = _mirror_rotation_euler(glass_world, eye_world, target)
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.update()
        report["mirrors"][side] = {
            "object": obj.name,
            "location": list(obj.location),
            "rotation_deg": [math.degrees(a) for a in obj.rotation_euler],
            "orientation_policy": policy,
        }

    # Metadata — next stages read this so user does not have to re-pass names
    meta = payload["metadata"]
    scn = bpy.context.scene
    for k, v_ in meta.items():
        scn["vmirror_" + k] = "" if v_ is None else v_

    bpy.context.view_layer.update()
    _save_blend(payload["output_blend"])
    report["output_blend"] = payload["output_blend"]


try:
    _build()
    report["status"] = "success"
except Exception as e:
    report["status"] = "error"
    report["error"] = str(e)
    report["traceback"] = traceback.format_exc()

_write_report(payload["report_path"], report)
'''
