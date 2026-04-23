"""Shared utilities for SceneBuilder / CameraRig / Renderer.

Each class spawns its own Blender subprocess; state between steps is carried
by intermediate .blend files on disk.
"""

from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "configs"
TMP_DIR = PROJECT_ROOT / "tmp"


def _project_mkdtemp(prefix: str) -> Path:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(TMP_DIR)))


def apply_timestamp(path: str | os.PathLike, fmt: str = "%m%d_%H%M") -> str:
    """Insert a ``_MMDD_HHMM`` suffix before the file extension.

    Example: ``output/render-results/hilux.png`` → ``.../hilux_0423_1410.png``.
    Directory components and extension are preserved.
    """
    p = Path(path)
    stamp = datetime.datetime.now().strftime(fmt)
    return str(p.with_name(f"{p.stem}_{stamp}{p.suffix}"))

MIRROR_ALIASES = {
    "standard": "standard_convex",
    "towing":   "towing_main",
    "electric": "electric_main",
}

DEFAULT_BLENDER_PATHS = [
    "/Applications/Blender.app/Contents/MacOS/Blender",
    "/usr/local/bin/blender",
    "blender",
]


def find_blender(override: str | None = None) -> str:
    if override:
        return override
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
        "`blender_exe=...` to the constructor."
    )


def load_yaml(rel_path: str) -> dict[str, Any]:
    path = CONFIG_DIR / rel_path
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_yaml_abs(abs_path: str) -> dict[str, Any]:
    p = Path(abs_path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def abs_blend(rel: str) -> str:
    return str((PROJECT_ROOT / rel).resolve())


def run_blender_script(
    blender_exe: str,
    script_body: str,
    report_path: Path,
    open_gui: bool = False,
    timeout: float = 600.0,
) -> dict[str, Any]:
    """Spawn Blender, execute ``script_body``, collect the JSON report.

    In headless mode (``open_gui=False``) this blocks until Blender exits.
    In GUI mode it polls for ``report_path`` to appear (the script writes it
    as its final act), then returns while the Blender window keeps living.
    """
    tmpdir = _project_mkdtemp("vmirror_sim_")
    script_path = tmpdir / "script.py"
    script_path.write_text(script_body)

    args = [blender_exe]
    if not open_gui:
        args.append("--background")
    args.extend(["--python", str(script_path)])

    if open_gui:
        # Capture stdout/stderr to a log file inside the tmpdir so errors
        # from deferred timers (e.g. area_split failures) can be inspected.
        log_path = tmpdir / "blender_stdout.log"
        log_f = open(log_path, "w")
        proc = subprocess.Popen(
            args, stdout=log_f, stderr=subprocess.STDOUT,
        )
        deadline = time.time() + timeout
        while not report_path.exists() and time.time() < deadline:
            time.sleep(0.3)
        if not report_path.exists():
            raise RuntimeError(
                f"Blender GUI did not write report within {timeout}s"
            )
        report = json.loads(report_path.read_text())
        report["_pid"] = proc.pid
        report["_mode"] = "gui"
        report["_log_path"] = str(log_path)
        return report

    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Blender subprocess timed out after {timeout}s"
        ) from exc
    if not report_path.exists():
        raise RuntimeError(
            "Blender subprocess did not produce a report.\n"
            f"return code: {proc.returncode}\n"
            f"stdout tail:\n{proc.stdout[-2000:]}\n"
            f"stderr tail:\n{proc.stderr[-2000:]}"
        )
    report = json.loads(report_path.read_text())
    report["_mode"] = "headless"
    shutil.rmtree(tmpdir, ignore_errors=True)
    shutil.rmtree(report_path.parent, ignore_errors=True)
    return report


BPY_COMMON_PRELUDE = r'''
import json
import math
import os
import traceback
import bpy
from mathutils import Vector, Matrix


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
    existing = {c.name for c in root.children}
    for coll in data_to.collections:
        if coll is None:
            continue
        if coll.name not in existing:
            root.children.link(coll)
    linked_any = {o.name for c in data_to.collections if c for o in c.all_objects}
    for obj in data_to.objects:
        if obj is None or obj.name in linked_any:
            continue
        try:
            bpy.context.collection.objects.link(obj)
        except RuntimeError:
            pass
    return {
        "collections": [c.name for c in data_to.collections if c],
        "objects": sum(1 for o in data_to.objects if o),
    }


def _clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        try:
            bpy.data.collections.remove(coll)
        except Exception:
            pass
    for datablocks in (
        bpy.data.meshes, bpy.data.materials, bpy.data.images,
        bpy.data.curves, bpy.data.lights, bpy.data.node_groups,
        bpy.data.cameras, bpy.data.worlds,
    ):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def _open_blend(path):
    bpy.ops.wm.open_mainfile(filepath=path)


def _save_blend(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path)


def _write_report(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)
    print("VMIRROR_SIM_REPORT:", path)
'''
