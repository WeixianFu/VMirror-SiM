"""SimulationPipeline — one-shot chain of SceneBuilder → CameraRig → Renderer.

Convenience wrapper for users who want "yaml parameters in, PNG out" without
the manual step-by-step cell workflow. Intermediate .blend files go to a
temp directory and are cleaned up unless ``keep_intermediates=True``.

Notebook usage
--------------
    from src import SimulationPipeline
    SimulationPipeline(
        scene="lane_change", vehicle="hilux", caravan="large2",
        mirror="standard", camera_side="L",
        output_png="output/builder/final.png",
    ).run()
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ._common import _project_mkdtemp
from .scene_builder import SceneBuilder, DEFAULT_MIRROR_TARGET
from .camera_rig import CameraRig
from .renderer import Renderer


class SimulationPipeline:
    def __init__(
        self,
        scene: str = "lane_change",
        vehicle: str = "passat",
        caravan: str | None = None,
        mirror: str = "standard",
        mirror_L: str | None = None,
        mirror_R: str | None = None,
        mirror_path_L: str | None = None,
        mirror_path_R: str | None = None,
        mirror_target: tuple[float, float, float] = DEFAULT_MIRROR_TARGET,
        camera_side: str = "L",
        camera: str | None = None,
        camera_path: str | None = None,
        render_profile: str | None = None,
        output_png: str | None = None,
        output_blend: str | None = None,
        timestamp: bool = True,
        blender_exe: str | None = None,
        keep_intermediates: bool = False,
    ):
        self.scene_builder = SceneBuilder(
            scene=scene, vehicle=vehicle, caravan=caravan,
            mirror=mirror,
            mirror_L=mirror_L, mirror_R=mirror_R,
            mirror_path_L=mirror_path_L, mirror_path_R=mirror_path_R,
            mirror_target=mirror_target, blender_exe=blender_exe,
        )
        self.camera_rig = CameraRig(
            side=camera_side, vehicle=vehicle,
            camera=camera, camera_path=camera_path,
            blender_exe=blender_exe,
        )
        # If caller did not pin a render profile, follow the one the camera
        # yaml declares (e.g. wide camera → render/wide.yaml).
        effective_rp = render_profile or self.camera_rig.render_profile_from_camera
        self.renderer = Renderer(
            render_profile=effective_rp, blender_exe=blender_exe,
        )
        self.output_png = output_png
        self.output_blend = output_blend
        self.timestamp = timestamp
        self.keep_intermediates = keep_intermediates

    def run(self, open_gui: bool = False) -> dict[str, Any]:
        tmp = _project_mkdtemp("vmirror_pipeline_")
        step1 = tmp / "step1_scene.blend"
        step2 = tmp / "step2_camera.blend"
        reports: dict[str, Any] = {}

        reports["scene"]  = self.scene_builder.build(output=step1)
        reports["camera"] = self.camera_rig.build(input=step1, output=step2)
        reports["render"] = self.renderer.render(
            input=step2,
            output=self.output_png,
            output_blend=self.output_blend,
            timestamp=self.timestamp,
            open_gui=open_gui,
        )

        if not self.keep_intermediates:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            reports["intermediates_dir"] = str(tmp)
        return reports
