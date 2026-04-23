"""ConfigExporter — dump a tuned .blend back into a drop-in configs/ tree.

Typical flow
------------
    1. Build scene / camera: SceneBuilder(...).build(output="tmp/step1.blend")
                             CameraRig(...).build(input=..., output="tmp/step2.blend")
    2. Hand-tune in Blender GUI (rotate mirrors, move caravan, tweak lens...),
       Ctrl+S to overwrite tmp/step2.blend.
    3. ConfigExporter().export(blend="tmp/step2.blend")
       → writes yamls under output/tuned-configs/<session>/ mirroring the
         top-level ``configs/`` layout so the bundle is drop-in.

What's exported
---------------
* ``vehicles/<name>.yaml`` — origin, eye_point
* ``caravans/<name>.yaml`` — location + ``ray_visibility`` block
* ``mirrors/<class>_{L,R}.yaml`` — glass_center_offset + explicit rotation
* ``cameras/driver_camera{_variant?}_{L,R}.yaml`` — lens, sensor, clip_start/end

Baseline yamls (from the current ``configs/`` tree) are loaded as templates;
only the fields we can actually re-derive from the blend are overwritten.
"""

from __future__ import annotations

import datetime
import json
import math
from pathlib import Path
from typing import Any

import yaml

from ._common import (
    BPY_COMMON_PRELUDE,
    CONFIG_DIR,
    PROJECT_ROOT,
    _project_mkdtemp,
    find_blender,
    load_yaml,
    load_yaml_abs,
    run_blender_script,
)

VALID_INCLUDE = ("vehicle", "mirror", "caravan", "camera")


class ConfigExporter:
    def __init__(self, blender_exe: str | None = None):
        self.blender_exe = find_blender(blender_exe)

    # ------------------------------------------------------------- entry point
    def export(
        self,
        blend: str | Path,
        tag: str | None = None,
        mirror_mode: str = "explicit",
        include: tuple[str, ...] = VALID_INCLUDE,
        out_root: str | Path = "output/tuned-configs",
    ) -> dict[str, Any]:
        blend_abs = str(Path(blend).resolve())
        if mirror_mode != "explicit":
            raise NotImplementedError(
                f"mirror_mode={mirror_mode!r} not implemented; only 'explicit' is supported"
            )
        for item in include:
            if item not in VALID_INCLUDE:
                raise ValueError(f"unknown include tag {item!r}; valid: {VALID_INCLUDE}")

        probe = self._probe(blend_abs)
        if probe.get("status") == "error":
            raise RuntimeError(
                f"blend probe failed: {probe.get('error')}\n{probe.get('traceback')}"
            )

        meta = probe["metadata"]
        baselines = self._resolve_baselines(meta)
        session = self._session_name(meta, tag)
        out_dir = (PROJECT_ROOT / out_root / session).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        written: list[str] = []
        if "vehicle" in include:
            written.append(self._write_vehicle(probe, baselines, out_dir))
        if "caravan" in include and probe.get("caravan"):
            written.append(self._write_caravan(probe, baselines, out_dir))
        if "mirror" in include:
            written.extend(self._write_mirrors(probe, baselines, out_dir, mirror_mode))
        if "camera" in include:
            written.append(self._write_camera(probe, baselines, out_dir))

        return {
            "session_dir": str(out_dir),
            "files": written,
            "metadata": meta,
        }

    # ------------------------------------------------------------- session name
    @staticmethod
    def _session_name(meta: dict[str, Any], tag: str | None) -> str:
        if tag:
            return tag
        parts = [
            meta.get("vehicle") or "unknown",
            meta.get("caravan") or "nocaravan",
            f"side{meta.get('camera_side', '?')}",
        ]
        stamp = datetime.datetime.now().strftime("%m%d_%H%M")
        return f"{'_'.join(parts)}_{stamp}"

    # -------------------------------------------- baseline yaml path resolution
    @staticmethod
    def _resolve_baselines(meta: dict[str, Any]) -> dict[str, Path]:
        """Trace back from the blend metadata to each baseline yaml path."""
        out: dict[str, Path] = {}
        veh = meta.get("vehicle")
        if veh:
            out["vehicle"] = CONFIG_DIR / "vehicles" / f"{veh}.yaml"
        car = meta.get("caravan")
        if car:
            out["caravan"] = CONFIG_DIR / "caravans" / f"{car}.yaml"
        cam_yaml = meta.get("camera_yaml")
        if cam_yaml:
            cy = Path(cam_yaml)
            if cy.is_absolute():
                out["camera"] = cy
            else:
                # SceneBuilder/CameraRig stores relative-to-configs (e.g.
                # "cameras/driver_camera_L.yaml"). Try CONFIG_DIR first, then
                # PROJECT_ROOT for anything outside configs/.
                candidate = CONFIG_DIR / cy
                if not candidate.exists():
                    candidate = PROJECT_ROOT / cy
                out["camera"] = candidate
        # Mirrors: mirror_L_source / mirror_R_source are "name:<cls>" or "path:<abs>"
        for side in ("L", "R"):
            src = meta.get(f"mirror_{side}_source", "")
            if src.startswith("path:"):
                out[f"mirror_{side}"] = Path(src[5:])
            elif src.startswith("name:"):
                cls = src[5:]
                out[f"mirror_{side}"] = CONFIG_DIR / "mirrors" / f"{cls}_{side}.yaml"
            else:
                # Fall back to the uniform mirror name
                cls = meta.get("mirror", "standard_convex")
                out[f"mirror_{side}"] = CONFIG_DIR / "mirrors" / f"{cls}_{side}.yaml"
        return out

    # ----------------------------------------------------------- blend probing
    def _probe(self, blend_abs: str) -> dict[str, Any]:
        report_path = _project_mkdtemp("config_exporter_") / "probe.json"
        payload = {"report_path": str(report_path), "input_blend": blend_abs}
        payload_json = json.dumps(payload)
        script = BPY_COMMON_PRELUDE + _PROBE_BODY.replace("__PAYLOAD_JSON__", payload_json)
        return run_blender_script(
            self.blender_exe, script, report_path,
            open_gui=False, timeout=120.0,
        )

    # ------------------------------------------------------------- yaml writers
    @staticmethod
    def _dump_yaml(path: Path, data: dict[str, Any]) -> str:
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True,
                           default_flow_style=False)
        return str(path)

    def _write_vehicle(self, probe, baselines, out_dir: Path) -> str:
        base = load_yaml_abs(str(baselines["vehicle"]))
        v = probe["vehicle"]
        base["origin"]["position"] = [round(x, 6) for x in v["location"]]
        base["origin"]["rotation"] = [round(math.degrees(x), 6) for x in v["rotation_euler"]]
        base["eye_point"] = [round(x, 6) for x in probe["camera"]["local_position"]]
        sub = out_dir / "vehicles"
        sub.mkdir(exist_ok=True)
        return self._dump_yaml(sub / f"{probe['metadata']['vehicle']}.yaml", base)

    def _write_caravan(self, probe, baselines, out_dir: Path) -> str:
        base = load_yaml_abs(str(baselines["caravan"]))
        c = probe["caravan"]
        # Record ray visibility (user's common tweak)
        base["ray_visibility"] = {
            "camera":         c["visible_camera"],
            "glossy":         c["visible_glossy"],
            "shadow":         c["visible_shadow"],
            "diffuse":        c["visible_diffuse"],
            "transmission":   c["visible_transmission"],
            "volume_scatter": c["visible_volume_scatter"],
        }
        # Location delta from the vehicle's hitch (documented, not re-applied at load)
        base["applied_world_location"] = [round(x, 6) for x in c["location"]]
        sub = out_dir / "caravans"
        sub.mkdir(exist_ok=True)
        return self._dump_yaml(sub / f"{probe['metadata']['caravan']}.yaml", base)

    def _write_mirrors(self, probe, baselines, out_dir: Path,
                       mirror_mode: str) -> list[str]:
        sub = out_dir / "mirrors"
        sub.mkdir(exist_ok=True)
        out: list[str] = []
        # Vehicle mount points (world frame, from baseline vehicle yaml)
        veh_base = load_yaml_abs(str(baselines["vehicle"]))
        mounts = {
            "L": veh_base["mirror_mount"]["left"],
            "R": veh_base["mirror_mount"]["right"],
        }
        for side in ("L", "R"):
            m = probe["mirrors"][side]
            base = load_yaml_abs(str(baselines[f"mirror_{side}"]))
            glass_world = m["location"]
            mount = mounts[side]
            new_offset = [round(glass_world[i] - mount[i], 6) for i in range(3)]
            base["glass_center_offset"]["vector"] = new_offset
            # Keep scalar mirrors of the vector so yaml stays self-consistent
            base["glass_center_offset"]["lateral"] = abs(new_offset[0])
            base["glass_center_offset"]["forward"] = new_offset[1]
            base["glass_center_offset"]["rise"]    = new_offset[2]

            if mirror_mode == "explicit":
                base.setdefault("orientation", {})
                base["orientation"]["policy"] = "explicit"
                base["orientation"]["rotation_euler_deg"] = [
                    round(math.degrees(a), 6) for a in m["rotation_euler"]
                ]

            # File naming: keep the baseline stem (e.g. "standard_convex_L.yaml")
            stem = Path(baselines[f"mirror_{side}"]).stem
            out.append(self._dump_yaml(sub / f"{stem}.yaml", base))
        return out

    def _write_camera(self, probe, baselines, out_dir: Path) -> str:
        base = load_yaml_abs(str(baselines["camera"]))
        cam = probe["camera"]
        base.setdefault("lens", {})
        base["lens"]["focal_length_mm"] = round(cam["lens"], 6)
        base["lens"]["sensor_width_mm"] = round(cam["sensor_width"], 6)
        base["lens"]["clip_start_m"]    = round(cam["clip_start"], 6)
        base["lens"]["clip_end_m"]      = round(cam["clip_end"], 6)
        sub = out_dir / "cameras"
        sub.mkdir(exist_ok=True)
        stem = Path(baselines["camera"]).stem  # e.g. driver_camera_wide_L
        return self._dump_yaml(sub / f"{stem}.yaml", base)


_PROBE_BODY = r'''

payload = json.loads(r"""__PAYLOAD_JSON__""")
report = {"vehicle": None, "caravan": None, "mirrors": {}, "camera": None,
          "metadata": {}}


def _build():
    _open_blend(payload["input_blend"])
    scn = bpy.context.scene

    # Metadata — read custom properties SceneBuilder/CameraRig wrote
    for k in scn.keys():
        if k.startswith("vmirror_"):
            report["metadata"][k[len("vmirror_"):]] = scn[k]

    vehicle_name = report["metadata"].get("vehicle") or ""
    side = report["metadata"].get("camera_side") or ""
    ego_name    = vehicle_name + "_ego" if vehicle_name else None
    mirror_name = lambda s: vehicle_name + "_Mirror_" + s
    cam_name    = vehicle_name + "_DriverCam_" + side if vehicle_name and side else None

    ego = bpy.data.objects.get(ego_name) if ego_name else None
    if ego is None:
        raise RuntimeError("ego object not found in blend: %s" % ego_name)
    report["vehicle"] = {
        "object": ego.name,
        "location": list(ego.matrix_world.translation),
        "rotation_euler": list(ego.rotation_euler),
    }

    # Caravan — first object whose name starts with Caravan_
    for o in bpy.data.objects:
        if o.name.startswith("Caravan_"):
            report["caravan"] = {
                "object": o.name,
                "location": list(o.matrix_world.translation),
                "visible_camera":       bool(o.visible_camera),
                "visible_glossy":       bool(o.visible_glossy),
                "visible_shadow":       bool(o.visible_shadow),
                "visible_diffuse":      bool(o.visible_diffuse),
                "visible_transmission": bool(o.visible_transmission),
                "visible_volume_scatter": bool(o.visible_volume_scatter),
            }
            break

    # Mirrors L + R
    for s in ("L", "R"):
        obj = bpy.data.objects.get(mirror_name(s))
        if obj is None:
            continue
        report["mirrors"][s] = {
            "object":         obj.name,
            "location":       list(obj.matrix_world.translation),
            "rotation_euler": list(obj.rotation_euler),
        }

    # Camera (parented to ego → local_position == vehicle.eye_point)
    if cam_name:
        cam = bpy.data.objects.get(cam_name)
        if cam is not None:
            report["camera"] = {
                "object":        cam.name,
                "local_position": list(cam.location),   # local == eye_point
                "world_position": list(cam.matrix_world.translation),
                "lens":           cam.data.lens,
                "sensor_width":   cam.data.sensor_width,
                "clip_start":     cam.data.clip_start,
                "clip_end":       cam.data.clip_end,
            }


try:
    _build()
    report["status"] = "success"
except Exception as e:
    report["status"] = "error"
    report["error"] = str(e)
    report["traceback"] = traceback.format_exc()

_write_report(payload["report_path"], report)
'''
