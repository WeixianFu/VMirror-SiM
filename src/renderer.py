"""Renderer — apply a render profile and (optionally) write a PNG.

Scope
-----
6c. World   — build a sky_background world if the loaded blend has none, using
              ``world:`` from the render yaml (moved here from the camera yaml).
7.  Profile — engine / resolution / cycles sampling / Apple-Silicon Metal / etc.
7b. Render  — ``bpy.ops.render.render(write_still=True)`` when ``output`` is set.

Reads an input ``.blend`` (CameraRig's output); does not modify geometry or
camera. Render settings are scene-level and persist only within this subprocess
unless ``output_blend`` is set (then saved back to disk).

Notebook usage
--------------
    from src import Renderer
    Renderer().render(
        input="/tmp/step2_camera.blend",
        output="output/builder/final.png",
    )
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._common import (
    BPY_COMMON_PRELUDE,
    PROJECT_ROOT,
    _project_mkdtemp,
    apply_timestamp,
    find_blender,
    load_yaml_abs,
    run_blender_script,
)

DEFAULT_RENDER_PROFILE = "configs/render/default.yaml"


class Renderer:
    def __init__(
        self,
        render_profile: str | None = None,
        blender_exe: str | None = None,
    ):
        rp = render_profile or DEFAULT_RENDER_PROFILE
        rp_abs = str((PROJECT_ROOT / rp).resolve())
        self.render_profile_path = rp_abs
        self.render_cfg = load_yaml_abs(rp_abs)
        self.blender_exe = find_blender(blender_exe)

    def _build_payload(
        self,
        input_blend: str,
        output_png: str | None,
        output_blend: str | None,
        report_path: str,
        camera_name: str | None = None,
    ) -> dict[str, Any]:
        return {
            "report_path":  report_path,
            "input_blend":  input_blend,
            "output_png":   output_png,
            "output_blend": output_blend,
            "render_cfg":   self.render_cfg,
            "camera_name":  camera_name,
        }

    def render(
        self,
        input: str | Path,
        output: str | Path | None = None,
        output_blend: str | Path | None = None,
        timestamp: bool = True,
        open_gui: bool = False,
        timeout: float = 1800.0,
        camera_name: str | None = None,
    ) -> dict[str, Any]:
        input_blend = str(Path(input).resolve())
        if output is not None and timestamp:
            output = apply_timestamp(output)
        if output_blend is not None and timestamp:
            output_blend = apply_timestamp(output_blend)
        output_png = str(Path(output).resolve()) if output else None
        output_blend_abs = str(Path(output_blend).resolve()) if output_blend else None
        report_path = _project_mkdtemp("renderer_") / "report.json"
        payload_json = json.dumps(
            self._build_payload(
                input_blend, output_png, output_blend_abs, str(report_path),
                camera_name=camera_name,
            )
        )
        script = (
            BPY_COMMON_PRELUDE
            + _RENDERER_BODY.replace("__PAYLOAD_JSON__", payload_json)
        )
        return run_blender_script(
            self.blender_exe, script, report_path,
            open_gui=open_gui, timeout=timeout,
        )

    def preview(
        self,
        input: str | Path,
        layout: str = "split",
        right_view: str = "top",
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        """Open the blend in a GUI Blender, apply the render profile, and
        flip the 3D viewport to camera view + Rendered shading.

        ``layout``:
          * ``"split"`` (default) — vertical split: LEFT = camera view +
            Rendered, RIGHT = free-orbit + Solid.
          * ``"triple"`` — three panes: left-top = L mirror cam (Rendered),
            left-bottom = R mirror cam (Rendered), right = free-orbit +
            Solid (manipulation pane). Needs both L+R cameras in the blend
            (use ``CameraRig(side="both")``).
          * ``"single"`` — every 3D area is camera view + Rendered.

        ``right_view`` (only honored for ``"split"`` / ``"triple"``):
          * ``"top"`` (default) — orthographic top-down centered between
            the vehicle and caravan. Best for moving objects on the ground.
          * ``"front"`` — looking +Y (along the road).
          * ``"side"`` — right-side view.
          * ``"free"`` — free-orbit User Perspective (Blender's default).

        No PNG is written. Window stays open; ``os.kill(report['_pid'], 15)``
        to close, or just quit Blender.
        """
        if layout not in ("split", "single", "triple"):
            raise ValueError(
                f"layout must be 'split', 'single', or 'triple', got {layout!r}"
            )
        if right_view not in ("top", "front", "side", "free"):
            raise ValueError(
                f"right_view must be 'top'/'front'/'side'/'free', got {right_view!r}"
            )
        input_blend = str(Path(input).resolve())
        report_path = _project_mkdtemp("renderer_preview_") / "report.json"
        payload = {
            "report_path": str(report_path),
            "input_blend": input_blend,
            "render_cfg":  self.render_cfg,
            "preview":     True,
            "layout":      layout,
            "right_view":  right_view,
        }
        payload_json = json.dumps(payload)
        script = (
            BPY_COMMON_PRELUDE
            + _RENDERER_BODY.replace("__PAYLOAD_JSON__", payload_json)
        )
        return run_blender_script(
            self.blender_exe, script, report_path,
            open_gui=True, timeout=timeout,
        )


_RENDERER_BODY = r'''

payload = json.loads(r"""__PAYLOAD_JSON__""")
report = {"step": "renderer", "render": None}


def _ensure_sky_world(spec):
    w = bpy.data.worlds.new("SkyWorld")
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg  = nt.nodes.new("ShaderNodeBackground")
    col = spec["color"]
    bg.inputs["Color"].default_value = (col[0], col[1], col[2], 1.0)
    bg.inputs["Strength"].default_value = spec["strength"]
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bpy.context.scene.world = w


def _apply_profile(rp):
    scn = bpy.context.scene

    # Apple-Silicon GPU setup
    asil = rp.get("apple_silicon", {})
    metal_devices = []
    asil_error = None
    if asil.get("enabled", False):
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = asil["compute_device_type"]
            if hasattr(prefs, "get_devices"):
                prefs.get_devices()
            for d in prefs.devices:
                d.use = (d.type == asil["compute_device_type"])
            if hasattr(prefs, "use_metalrt"):
                prefs.use_metalrt = asil.get("use_metalrt", False)
            scn.cycles.device = asil.get("cycles_device", "GPU")
            if hasattr(scn.cycles, "denoising_use_gpu"):
                scn.cycles.denoising_use_gpu = rp["cycles"].get(
                    "denoising_use_gpu", True
                )
            metal_devices = [d.name for d in prefs.devices if d.use]
        except Exception as e:
            asil_error = str(e)

    scn.render.engine = rp["engine"]
    out = rp["output"]
    scn.render.resolution_x = out["resolution_x"]
    scn.render.resolution_y = out["resolution_y"]
    scn.render.resolution_percentage = out["resolution_percentage"]
    scn.render.use_persistent_data = rp.get("persistent_data", False)

    cy = scn.cycles
    rc = rp["cycles"]
    cy.samples = rc["samples"]
    cy.preview_samples = rc.get("preview_samples", cy.preview_samples)
    cy.max_bounces = rc["max_bounces"]
    cy.diffuse_bounces = rc.get("diffuse_bounces", cy.diffuse_bounces)
    cy.glossy_bounces = rc["glossy_bounces"]
    cy.transmission_bounces = rc.get("transmission_bounces", cy.transmission_bounces)
    cy.transparent_max_bounces = rc.get(
        "transparent_max_bounces", cy.transparent_max_bounces
    )
    adapt = rc.get("adaptive_sampling", {})
    cy.use_adaptive_sampling = adapt.get("enabled", False)
    if cy.use_adaptive_sampling:
        cy.adaptive_threshold = adapt["threshold"]
        cy.adaptive_min_samples = adapt["min_samples"]
    cy.use_denoising = rc["use_denoising"]
    cy.denoiser = rc["denoiser"]
    cy.pixel_filter_type = rc["pixel_filter_type"]
    cy.filter_width = rc["filter_width"]
    clamp = rp.get("clamp", {})
    cy.sample_clamp_direct   = clamp.get("direct", 0.0)
    cy.sample_clamp_indirect = clamp.get("indirect", 0.0)

    return {"metal_devices": metal_devices, "apple_silicon_error": asil_error}


def _configure_space(space, perspective, shading):
    if space.type != "VIEW_3D":
        return
    try:
        space.region_3d.view_perspective = perspective
    except Exception:
        pass
    space.shading.type = shading


def _set_right_pane_view(area, win, screen, view_kind):
    """Configure a pane intended for free manipulation (Solid shading) with
    a chosen starting view: top / front / side / free."""
    # Pre-baked view_rotation quaternions matching Numpad-7/1/3 (in Blender's
    # `(w, x, y, z)` convention). Used as a fallback if view_axis operator
    # rejects the context.
    quat_map = {
        "top":   (1.0, 0.0, 0.0, 0.0),
        "front": (0.7071068, 0.7071068, 0.0, 0.0),
        "side":  (0.5, 0.5, 0.5, 0.5),
    }
    axis_map = {"top": "TOP", "front": "FRONT", "side": "RIGHT"}

    region = next((r for r in area.regions if r.type == "WINDOW"), None)

    for s in area.spaces:
        if s.type != "VIEW_3D":
            continue
        s.use_local_camera = False
        rv3d = s.region_3d
        if view_kind == "free":
            try:
                rv3d.view_perspective = "PERSP"
            except Exception:
                pass
        else:
            axis = axis_map.get(view_kind, "TOP")
            ok = False
            if region is not None:
                try:
                    with bpy.context.temp_override(
                        window=win, screen=screen, area=area, region=region,
                    ):
                        bpy.ops.view3d.view_axis(type=axis)
                    ok = True
                except Exception as e:
                    print("[VMirror] view_axis(%s) failed: %s" % (axis, e), flush=True)
            if not ok:
                # Manual fallback — set quaternion + ortho directly.
                try:
                    rv3d.view_rotation = quat_map[view_kind]
                    rv3d.view_perspective = "ORTHO"
                except Exception as e:
                    print("[VMirror] manual view set failed: %s" % e, flush=True)
            # Frame on the ego/caravan midpoint
            rv3d.view_location = (0.0, -4.0, 0.0)
            rv3d.view_distance = 12.0
        s.shading.type = "SOLID"


def _enter_single_layout():
    """Every VIEW_3D area in every screen → camera view + Rendered shading."""
    touched = 0
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                _configure_space(space, "CAMERA", "RENDERED")
                touched += 1
    return {"layout": "single", "areas_touched": touched}


def _schedule_split_layout(right_view="top"):
    """Defer area_split until Blender's main loop is ready (bpy.ops.screen.*
    needs a valid window/screen/area context which isn't available during
    --python startup)."""
    def _do_split():
        try:
            wm = bpy.context.window_manager
            if not wm.windows:
                return 0.5   # try again later
            win = wm.windows[0]
            screen = win.screen
            v3d = [a for a in screen.areas if a.type == "VIEW_3D"]
            if not v3d:
                return None
            target = v3d[0]
            with bpy.context.temp_override(window=win, screen=screen, area=target):
                bpy.ops.screen.area_split(direction="VERTICAL", factor=0.5)
            v3d = sorted(
                (a for a in screen.areas if a.type == "VIEW_3D"),
                key=lambda a: a.x,
            )
            left, right = v3d[0], v3d[-1]
            for s in left.spaces:
                _configure_space(s, "CAMERA", "RENDERED")
            _set_right_pane_view(right, win, screen, right_view)
            print("[VMirror preview] split layout applied (right=%s)" % right_view, flush=True)
        except Exception as e:
            print("[VMirror preview] split failed:", e, flush=True)
        return None   # unregister

    bpy.app.timers.register(_do_split, first_interval=1.0)
    # Also set every VIEW_3D to Rendered up-front so if user switches workspace
    # before the split fires, they still see the render preview.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.shading.type = "RENDERED"
                    try:
                        space.region_3d.view_perspective = "CAMERA"
                    except Exception:
                        pass
    return {"layout": "split", "scheduled": True}


def _schedule_triple_layout(right_view="top"):
    """Left column: L-mirror camera (top) + R-mirror camera (bottom), both
    Rendered. Right column: configurable view (default top-down ortho on
    the ego/caravan midpoint), Solid shading. Uses a multi-tick state machine
    — Blender needs a redraw between area_split calls before the resulting
    areas' dimensions are valid to act on."""
    state = {"stage": 0, "right_x": None}

    def _do():
        try:
            wm = bpy.context.window_manager
            if not wm.windows:
                return 0.3
            win = wm.windows[0]
            screen = win.screen
            scn = bpy.context.scene
            v3d = [a for a in screen.areas if a.type == "VIEW_3D"]
            if not v3d:
                return None

            # Stage 0: first VERTICAL split (left + right)
            if state["stage"] == 0:
                prefix = scn.get("vmirror_vehicle", "")
                cam_L = bpy.data.objects.get(prefix + "_DriverCam_L")
                cam_R = bpy.data.objects.get(prefix + "_DriverCam_R")
                if cam_L is None or cam_R is None:
                    print(
                        "[VMirror triple] need %s_DriverCam_L and _R; "
                        "fallback to split layout" % prefix, flush=True
                    )
                    _schedule_split_layout(right_view)
                    return None
                target = v3d[0]
                with bpy.context.temp_override(window=win, screen=screen, area=target):
                    bpy.ops.screen.area_split(direction="VERTICAL", factor=0.5)
                state["stage"] = 1
                return 0.3

            # Stage 1: second HORIZONTAL split on the left half
            if state["stage"] == 1:
                v3d_sorted = sorted(v3d, key=lambda a: a.x)
                left, right = v3d_sorted[0], v3d_sorted[-1]
                state["right_x"] = right.x
                with bpy.context.temp_override(window=win, screen=screen, area=left):
                    bpy.ops.screen.area_split(direction="HORIZONTAL", factor=0.5)
                state["stage"] = 2
                return 0.3

            # Stage 2: classify panes and bind cameras + shading
            if state["stage"] == 2:
                prefix = scn.get("vmirror_vehicle", "")
                cam_L = bpy.data.objects[prefix + "_DriverCam_L"]
                cam_R = bpy.data.objects[prefix + "_DriverCam_R"]
                right_x = state["right_x"]
                left_col  = [a for a in v3d if a.x < right_x]
                right_col = [a for a in v3d if a.x >= right_x]
                left_col.sort(key=lambda a: -a.y)
                left_top    = left_col[0]
                left_bottom = left_col[-1]
                right_pane  = right_col[0]

                def _bind(area, cam, zoom):
                    for s in area.spaces:
                        if s.type != "VIEW_3D":
                            continue
                        s.use_local_camera = True
                        s.camera = cam
                        try:
                            s.region_3d.view_perspective = "CAMERA"
                            s.region_3d.view_camera_zoom = zoom
                            s.region_3d.view_camera_offset = (0.0, 0.0)
                        except Exception:
                            pass
                        s.shading.type = "RENDERED"

                # view_camera_zoom 18 makes the camera frame fill
                # ~70% of a roughly-square left pane (see Blender's
                # logarithmic mapping).
                _bind(left_top, cam_L, zoom=18)
                _bind(left_bottom, cam_R, zoom=18)
                _set_right_pane_view(right_pane, win, screen, right_view)
                print("[VMirror triple] layout applied (3 panes, right=%s)" % right_view, flush=True)
                return None
        except Exception as e:
            import traceback
            print("[VMirror triple] failed:", e, flush=True)
            traceback.print_exc()
        return None

    bpy.app.timers.register(_do, first_interval=1.0)
    # Pre-split fallback as in the split layout
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.shading.type = "RENDERED"
                    try:
                        space.region_3d.view_perspective = "CAMERA"
                    except Exception:
                        pass
    return {"layout": "triple", "scheduled": True}


def _build():
    _open_blend(payload["input_blend"])
    rp = payload["render_cfg"]

    # Step 6c — world shader from render yaml if the loaded blend has none.
    world_spec = rp.get("world")
    if world_spec and bpy.context.scene.world is None:
        _ensure_sky_world(world_spec)

    # Step 7 — render profile
    report["render"] = _apply_profile(rp)
    bpy.context.view_layer.update()

    # Preview mode: flip viewport to camera view + Rendered shading, don't render
    if payload.get("preview"):
        layout = payload.get("layout", "split")
        right_view = payload.get("right_view", "top")
        if layout == "split":
            report["preview"] = _schedule_split_layout(right_view)
        elif layout == "triple":
            report["preview"] = _schedule_triple_layout(right_view)
        else:
            report["preview"] = _enter_single_layout()
        report["active_camera"] = (
            bpy.context.scene.camera.name if bpy.context.scene.camera else None
        )
        return

    # Step 7b — render PNG if requested
    out_png = payload.get("output_png")
    if out_png:
        cam_name = payload.get("camera_name")
        if cam_name:
            cam_obj = bpy.data.objects.get(cam_name)
            if cam_obj is None:
                raise RuntimeError("camera_name %r not in blend" % cam_name)
            bpy.context.scene.camera = cam_obj
            report["active_camera"] = cam_obj.name
        os.makedirs(os.path.dirname(out_png), exist_ok=True)
        bpy.context.scene.render.filepath = out_png
        bpy.context.scene.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(write_still=True)
        report["output_png"] = out_png

    # Optional: persist the render-configured scene for later re-use
    out_blend = payload.get("output_blend")
    if out_blend:
        _save_blend(out_blend)
        report["output_blend"] = out_blend


try:
    _build()
    report["status"] = "success"
except Exception as e:
    report["status"] = "error"
    report["error"] = str(e)
    report["traceback"] = traceback.format_exc()

_write_report(payload["report_path"], report)
'''
