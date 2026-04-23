"""CameraRig — attach the driver-eye camera to an already-built scene.

Scope
-----
5. Camera           — append ``DriverCam`` from the camera blend, parent to
                       ``{vehicle}_ego``, place at vehicle.eye_point, add a
                       Track-To constraint pointing at ``{vehicle}_Mirror_{side}``.
6a. ego_ray_visibility — apply the 6 cycles ray visibility flags from camera yaml.
6b. mirror smooth   — already done by SceneBuilder; re-asserted here if
                       ``scene_setup.mirror_shading.use_smooth`` is true.

Reads an input ``.blend`` (SceneBuilder's output), augments it with the
camera + state flags, saves to output ``.blend``. Does not render.

Notebook usage
--------------
    from src import CameraRig
    CameraRig(side="L", vehicle="hilux").build(
        input="/tmp/step1_scene.blend",
        output="/tmp/step2_camera.blend",
    )
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._common import (
    BPY_COMMON_PRELUDE,
    CONFIG_DIR,
    _project_mkdtemp,
    abs_blend,
    find_blender,
    load_yaml,
    load_yaml_abs,
    run_blender_script,
)


def _resolve_camera_yaml_path(
    side: str,
    camera: str | None,
    camera_path: str | None,
) -> tuple[str, bool]:
    """Return (yaml_path, is_absolute). Priority: camera_path > camera > default.

    Name resolution rules when ``camera`` is set:
      * Ends with ``_L`` / ``_R`` → use as-is, must match ``side``
      * Starts with ``driver_camera`` → append ``_{side}``
      * Otherwise (short variant like ``"wide"``) → ``driver_camera_{name}_{side}``
    """
    if camera_path:
        return str(camera_path), True
    if camera is None:
        return f"cameras/driver_camera_{side}.yaml", False

    stem = camera
    if stem.endswith("_L") or stem.endswith("_R"):
        suffix = stem[-1]
        if suffix != side:
            raise ValueError(
                f"camera name {camera!r} ends with _{suffix} but side={side!r}"
            )
        full = stem
    elif stem.startswith("driver_camera"):
        full = f"{stem}_{side}"
    else:
        full = f"driver_camera_{stem}_{side}"
    return f"cameras/{full}.yaml", False


class CameraRig:
    def __init__(
        self,
        side: str = "L",
        vehicle: str | None = None,
        camera: str | None = None,
        camera_path: str | None = None,
        blender_exe: str | None = None,
    ):
        if side not in ("L", "R", "both"):
            raise ValueError(f"side must be 'L', 'R', or 'both', got {side!r}")
        if side == "both" and camera_path is not None:
            raise ValueError(
                "`camera_path` is incompatible with side='both'. Use `camera` "
                "(the variant name) so the resolver can pick the matching L and R yamls."
            )
        self.side = side
        self.vehicle = vehicle
        self.blender_exe = find_blender(blender_exe)

        # Resolve one or two camera yamls, depending on side.
        self._camera_configs: list[tuple[str, str, dict[str, Any]]] = []
        sides = ("L", "R") if side == "both" else (side,)
        for s in sides:
            rel_or_abs, is_abs = _resolve_camera_yaml_path(s, camera, camera_path)
            cfg = load_yaml_abs(rel_or_abs) if is_abs else load_yaml(rel_or_abs)
            self._camera_configs.append((s, rel_or_abs, cfg))

        # Primary (for single-side) is the only entry; for 'both' it's L.
        primary = self._camera_configs[0]
        self.camera_yaml_path = primary[1]
        self.camera_cfg = primary[2]
        self.render_profile_from_camera = self.camera_cfg.get("render_profile")
        self._vehicle_cfg_cache: dict[str, Any] | None = None

    def _resolve_vehicle(self, fallback_name: str | None) -> dict[str, Any]:
        name = self.vehicle or fallback_name
        if not name:
            raise RuntimeError(
                "CameraRig needs a vehicle name. Pass `vehicle=...` to the "
                "constructor, or have the blend carry `vmirror_vehicle` metadata."
            )
        if self._vehicle_cfg_cache is None or self._vehicle_cfg_cache.get("model") != name:
            self._vehicle_cfg_cache = load_yaml(f"vehicles/{name}.yaml")
        return self._vehicle_cfg_cache

    def _build_payload(
        self,
        input_blend: str,
        output_blend: str,
        report_path: str,
        vehicle_name_hint: str | None,
    ) -> dict[str, Any]:
        v = self._resolve_vehicle(vehicle_name_hint)
        sides_payload = []
        for side, yaml_path, cam in self._camera_configs:
            sides_payload.append({
                "side":             side,
                "camera_yaml_path": yaml_path,
                "camera": {
                    "blend":         abs_blend(cam["source_blend"]),
                    "source_object": cam["source_object"],
                    "lens_mm":       cam["lens"]["focal_length_mm"],
                    "sensor_width":  cam["lens"]["sensor_width_mm"],
                    "clip_start":    cam["lens"]["clip_start_m"],
                    "clip_end":      cam["lens"]["clip_end_m"],
                    "track_axis":    cam["track_to"]["track_axis"],
                    "up_axis":       cam["track_to"]["up_axis"],
                    "target_pattern": cam["track_to"]["target_object_name_pattern"],
                    "scene_setup":   cam["scene_setup"],
                },
            })
        return {
            "report_path":  report_path,
            "input_blend":  input_blend,
            "output_blend": output_blend,
            "side":         self.side,            # "L" / "R" / "both"
            "vehicle_name": v["model"],
            "eye_point":    list(v["eye_point"]),
            "sides":        sides_payload,
        }

    def build(
        self,
        input: str | Path,
        output: str | Path,
        open_gui: bool = False,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        input_blend = str(Path(input).resolve())
        output_blend = str(Path(output).resolve())
        report_path = _project_mkdtemp("camera_rig_") / "report.json"
        payload_json = json.dumps(
            self._build_payload(
                input_blend, output_blend, str(report_path),
                vehicle_name_hint=self.vehicle,
            )
        )
        script = (
            BPY_COMMON_PRELUDE
            + _CAMERA_RIG_BODY.replace("__PAYLOAD_JSON__", payload_json)
        )
        return run_blender_script(
            self.blender_exe, script, report_path,
            open_gui=open_gui, timeout=timeout,
        )


_CAMERA_RIG_BODY = r'''

payload = json.loads(r"""__PAYLOAD_JSON__""")
report = {"step": "camera_rig", "camera": None, "ego_visibility": None}


_TRACK_AXIS_MAP = {
    "POS_X": "TRACK_X",  "NEG_X": "TRACK_NEGATIVE_X",
    "POS_Y": "TRACK_Y",  "NEG_Y": "TRACK_NEGATIVE_Y",
    "POS_Z": "TRACK_Z",  "NEG_Z": "TRACK_NEGATIVE_Z",
}
_UP_AXIS_MAP = {"X": "UP_X", "Y": "UP_Y", "Z": "UP_Z"}


def _build():
    _open_blend(payload["input_blend"])

    scn = bpy.context.scene
    prefix = scn.get("vmirror_vehicle") or payload["vehicle_name"]
    ego_name = prefix + "_ego"
    ego = bpy.data.objects.get(ego_name)
    if ego is None:
        raise RuntimeError("ego not found: %s" % ego_name)

    report["cameras"] = {}
    report["ego_visibility"] = None

    for entry in payload["sides"]:
        side = entry["side"]
        cs = entry["camera"]
        mirror_name = prefix + "_Mirror_" + side
        mirror = bpy.data.objects.get(mirror_name)
        if mirror is None:
            raise RuntimeError("mirror not found: %s" % mirror_name)

        new_cam_name = prefix + "_DriverCam_" + side
        # Idempotent: remove old camera of same name if present (re-runs)
        old = bpy.data.objects.get(new_cam_name)
        if old is not None:
            bpy.data.objects.remove(old, do_unlink=True)

        cam = _append_single(cs["blend"], cs["source_object"], new_name=new_cam_name)
        cam.data.lens = cs["lens_mm"]
        cam.data.sensor_width = cs["sensor_width"]
        cam.data.clip_start = cs["clip_start"]
        cam.data.clip_end = cs["clip_end"]
        cam.parent = ego
        cam.location = Vector(payload["eye_point"])
        cam.rotation_euler = (0.0, 0.0, 0.0)
        for c in list(cam.constraints):
            cam.constraints.remove(c)
        con = cam.constraints.new(type="TRACK_TO")
        con.target = mirror
        con.track_axis = _TRACK_AXIS_MAP[cs["track_axis"]]
        con.up_axis    = _UP_AXIS_MAP[cs["up_axis"]]

        report["cameras"][side] = {"object": cam.name, "tracks": mirror.name}

        # Apply scene_setup from the FIRST side only (ego ray visibility is
        # not side-specific; mirror smooth shading is identical across sides).
        if report["ego_visibility"] is None:
            ss = cs["scene_setup"]
            rv = ss["ego_ray_visibility"]
            ego.visible_camera         = rv["visible_camera"]
            ego.visible_glossy         = rv["visible_glossy"]
            ego.visible_shadow         = rv["visible_shadow"]
            ego.visible_diffuse        = rv["visible_diffuse"]
            ego.visible_transmission   = rv["visible_transmission"]
            ego.visible_volume_scatter = rv["visible_volume_scatter"]
            report["ego_visibility"] = rv
            if ss.get("mirror_shading", {}).get("use_smooth"):
                for obj in bpy.data.objects:
                    if obj.name.startswith(prefix + "_Mirror_"):
                        for p in obj.data.polygons:
                            p.use_smooth = True
                        obj.data.update()

    # Pick the primary (first in payload) as the scene.camera default
    primary_entry = payload["sides"][0]
    primary_cam = bpy.data.objects[prefix + "_DriverCam_" + primary_entry["side"]]
    scn.camera = primary_cam
    scn["vmirror_camera_side"] = payload["side"]   # "L" / "R" / "both"
    scn["vmirror_camera_yaml"] = primary_entry["camera_yaml_path"]

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
