"""Build a VMirror-SiM simulation scene by spawning a Blender subprocess.

No third-party Blender addon required. Two modes:

* ``mode="headless"`` — runs ``blender --background --python ...``; Blender
  exits when the script finishes. ``build()`` returns a report dict.
* ``mode="demo"``     — runs ``blender --python ...`` (with GUI); the window
  stays open with the built scene loaded so you can orbit the camera, pick
  objects, rotate mirrors by hand, etc. ``build()`` returns immediately with
  the spawned process handle.

Usage from a notebook
---------------------
    from src import SimulationBuilder
    SimulationBuilder().build()                              # headless default
    SimulationBuilder(mode="demo").build()                   # opens Blender GUI
    SimulationBuilder(vehicle="crv", caravan="middle",
                      mirror="towing_main", mode="demo").build()
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "configs"

MIRROR_ALIASES = {
    "standard": "standard_convex",
    "towing": "towing_main",
    "electric": "electric_main",
}

DEFAULT_MIRROR_TARGET = (0.0, -20.0, 0.5)

DEFAULT_BLENDER_PATHS = [
    "/Applications/Blender.app/Contents/MacOS/Blender",
    "/usr/local/bin/blender",
    "blender",
]


class SimulationBuilder:
    def __init__(
        self,
        scene: str = "lane_change",
        vehicle: str = "passat",
        caravan: str | None = None,
        mirror: str = "standard",
        mirror_target: tuple[float, float, float] = DEFAULT_MIRROR_TARGET,
        mode: str = "headless",
        blender_exe: str | None = None,
        clear_scene: bool = True,
        headless_timeout: float = 180.0,
    ):
        if mode not in ("headless", "demo"):
            raise ValueError(
                f"mode must be 'headless' or 'demo', got {mode!r}"
            )
        self.scene = scene
        self.vehicle = vehicle
        self.caravan = caravan
        self.mirror = MIRROR_ALIASES.get(mirror, mirror)
        self.mirror_target = tuple(float(v) for v in mirror_target)
        self.mode = mode
        self.blender_exe = blender_exe or self._find_blender()
        self.clear_scene = clear_scene
        self.headless_timeout = headless_timeout

        self.scene_cfg = self._load_yaml(f"scenes/{self.scene}.yaml")
        self.vehicle_cfg = self._load_yaml(f"vehicles/{self.vehicle}.yaml")
        self.caravan_cfg = (
            self._load_yaml(f"caravans/{self.caravan}.yaml")
            if self.caravan
            else None
        )
        self.mirror_L_cfg = self._load_yaml(f"mirrors/{self.mirror}_L.yaml")
        self.mirror_R_cfg = self._load_yaml(f"mirrors/{self.mirror}_R.yaml")

    @staticmethod
    def _find_blender() -> str:
        for p in DEFAULT_BLENDER_PATHS:
            if os.path.isabs(p):
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    return p
            else:
                found = shutil.which(p)
                if found:
                    return found
        raise RuntimeError(
            "Blender executable not found. Install Blender or pass "
            "`blender_exe=...` to the SimulationBuilder constructor."
        )

    @staticmethod
    def _load_yaml(rel_path: str) -> dict[str, Any]:
        path = CONFIG_DIR / rel_path
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _abs_blend(self, rel: str) -> str:
        return str((PROJECT_ROOT / rel).resolve())

    def _build_payload(self, report_path: str) -> dict[str, Any]:
        v = self.vehicle_cfg
        mL = self.mirror_L_cfg
        mR = self.mirror_R_cfg
        return {
            "report_path": report_path,
            "scene_blend": self._abs_blend(self.scene_cfg["source_blend"]),
            "vehicle": {
                "name": v["model"],
                "blend": self._abs_blend(v["source_blend"]),
                "origin_position": list(v["origin"]["position"]),
                "origin_rotation_deg": list(v["origin"]["rotation"]),
                "mirror_mount": {
                    "left": list(v["mirror_mount"]["left"]),
                    "right": list(v["mirror_mount"]["right"]),
                },
                "eye_point": list(v["eye_point"]),
                "hitch_ground_projection": list(v["hitch_ground_projection"]),
            },
            "caravan": (
                None
                if self.caravan_cfg is None
                else {
                    "name": self.caravan_cfg["model"],
                    "blend": self._abs_blend(self.caravan_cfg["source_blend"]),
                }
            ),
            "mirrors": {
                "L": {
                    "blend": self._abs_blend(mL["source_blend"]),
                    "source_object": mL["source_object"],
                    "glass_center_offset": list(mL["glass_center_offset"]["vector"]),
                },
                "R": {
                    "blend": self._abs_blend(mR["source_blend"]),
                    "source_object": mR["source_object"],
                    "glass_center_offset": list(mR["glass_center_offset"]["vector"]),
                },
            },
            "mirror_target": list(self.mirror_target),
            "clear_scene": self.clear_scene,
        }

    def _generate_code(self, report_path: str) -> str:
        payload_json = json.dumps(self._build_payload(report_path))
        return _BUILDER_TEMPLATE.replace("__PAYLOAD_JSON__", payload_json)

    def build(self) -> dict[str, Any]:
        tmpdir = Path(tempfile.mkdtemp(prefix="vmirror_sim_"))
        report_path = tmpdir / "report.json"
        script_path = tmpdir / "build_script.py"
        script_path.write_text(self._generate_code(str(report_path)))

        args = [self.blender_exe]
        if self.mode == "headless":
            args.append("--background")
        args.extend(["--python", str(script_path)])

        if self.mode == "headless":
            try:
                proc = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    timeout=self.headless_timeout,
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(
                    f"Blender subprocess timed out after "
                    f"{self.headless_timeout}s"
                ) from exc
            if not report_path.exists():
                raise RuntimeError(
                    "Blender subprocess did not produce a report.\n"
                    f"return code: {proc.returncode}\n"
                    f"stdout tail:\n{proc.stdout[-2000:]}\n"
                    f"stderr tail:\n{proc.stderr[-2000:]}"
                )
            report = json.loads(report_path.read_text())
            shutil.rmtree(tmpdir, ignore_errors=True)
            return report
        else:
            proc = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {
                "mode": "demo",
                "pid": proc.pid,
                "script": str(script_path),
                "report_path": str(report_path),
                "blender": self.blender_exe,
            }


_BUILDER_TEMPLATE = r"""
import json
import math
import os
import traceback
import bpy
from mathutils import Vector, Matrix

payload = json.loads(r'''__PAYLOAD_JSON__''')

report = {"scene": None, "vehicle": None, "caravan": None, "mirrors": {}}


def _append_single(blend_path, obj_name, new_name):
    with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
        if obj_name not in data_from.objects:
            raise RuntimeError(
                "Object '%s' not found in %s. Available: %s"
                % (obj_name, blend_path, list(data_from.objects))
            )
        data_to.objects = [obj_name]
    obj = data_to.objects[0]
    if obj is None:
        raise RuntimeError("Failed to append %s from %s" % (obj_name, blend_path))
    obj.name = new_name
    bpy.context.collection.objects.link(obj)
    return obj


def _append_scene(blend_path):
    with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
        data_to.objects = list(data_from.objects)
        data_to.collections = list(data_from.collections)
    root = bpy.context.scene.collection
    existing_children = {c.name for c in root.children}
    for coll in data_to.collections:
        if coll is None:
            continue
        if coll.name not in existing_children:
            root.children.link(coll)
    linked_in_any = {o.name for c in data_to.collections if c for o in c.all_objects}
    for obj in data_to.objects:
        if obj is None:
            continue
        if obj.name in linked_in_any:
            continue
        try:
            bpy.context.collection.objects.link(obj)
        except RuntimeError:
            pass
    return {
        "collections": [c.name for c in data_to.collections if c],
        "objects": sum(1 for o in data_to.objects if o),
    }


def _clear_scene(keep_cameras=True):
    protected = set()
    if keep_cameras:
        for o in bpy.data.objects:
            if o.type == "CAMERA":
                protected.add(o.name)
    for obj in list(bpy.data.objects):
        if obj.name in protected:
            continue
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        try:
            bpy.data.collections.remove(coll)
        except Exception:
            pass
    for datablocks in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.curves,
        bpy.data.lights,
        bpy.data.node_groups,
    ):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def _mirror_rotation_matrix(glass_world, eye_world, target_world):
    g = Vector(glass_world)
    to_eye = (Vector(eye_world) - g).normalized()
    to_tgt = (Vector(target_world) - g).normalized()
    outward_n = (to_eye + to_tgt).normalized()
    z_axis = (-outward_n).normalized()
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
    return mat


def _build():
    if payload.get("clear_scene", True):
        _clear_scene(keep_cameras=True)

    report["scene"] = _append_scene(payload["scene_blend"])

    v = payload["vehicle"]
    prefix = v["name"]
    ego = _append_single(v["blend"], "node_0", new_name=prefix + "_ego")
    ego.location = Vector(v["origin_position"])
    ego.rotation_euler = (
        math.radians(v["origin_rotation_deg"][0]),
        math.radians(v["origin_rotation_deg"][1]),
        math.radians(v["origin_rotation_deg"][2]),
    )
    report["vehicle"] = {
        "object": ego.name,
        "location": list(ego.location),
        "rotation_deg": [math.degrees(a) for a in ego.rotation_euler],
    }

    if payload.get("caravan"):
        c = payload["caravan"]
        caravan = _append_single(
            c["blend"], "node_0", new_name="Caravan_" + c["name"]
        )
        caravan.location = Vector(v["hitch_ground_projection"])
        caravan.rotation_euler = (0.0, 0.0, 0.0)
        report["caravan"] = {
            "object": caravan.name,
            "location": list(caravan.location),
        }

    target = payload["mirror_target"]
    eye_world = v["eye_point"]
    for side in ("L", "R"):
        m = payload["mirrors"][side]
        mount = v["mirror_mount"]["left" if side == "L" else "right"]
        offset = m["glass_center_offset"]
        glass_world = [mount[i] + offset[i] for i in range(3)]
        new_name = prefix + "_Mirror_" + side
        mir = _append_single(m["blend"], m["source_object"], new_name=new_name)
        mir.location = Vector(glass_world)
        rot_mat = _mirror_rotation_matrix(glass_world, eye_world, target)
        mir.rotation_euler = rot_mat.to_euler("XYZ")
        for p in mir.data.polygons:
            p.use_smooth = True
        report["mirrors"][side] = {
            "object": mir.name,
            "location": list(mir.location),
            "rotation_deg": [math.degrees(a) for a in mir.rotation_euler],
        }

    bpy.context.view_layer.update()


try:
    _build()
    report["status"] = "success"
except Exception as e:
    report["status"] = "error"
    report["error"] = str(e)
    report["traceback"] = traceback.format_exc()

report_path = payload["report_path"]
os.makedirs(os.path.dirname(report_path), exist_ok=True)
with open(report_path, "w") as f:
    json.dump(report, f)

print("VMIRROR_SIM_REPORT:", report_path)
"""
