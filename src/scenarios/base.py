"""
场景基类

所有场景继承自 BaseScenario，处理通用的配置加载、
道路创建、光照设置、渲染配置等。
"""

import pathlib

import yaml

import bpy

from objects.road_system import (
    create_collection,
    create_ground_plane,
    create_road_system,
    setup_lighting,
    setup_render_settings,
)

_CONFIG_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "config"


def _load_yaml(name: str) -> dict:
    with open(_CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


class BaseScenario:
    """
    场景基类。

    子类需实现 create_scenario_objects() 方法来添加场景特有的物体。

    使用:
        scenario = HighwayScenario('suv', 'L')
        scenario.build()
    """

    # 子类需设置的类属性
    scenario_key: str = ""          # scenarios.yaml 中的键名
    needs_road: bool = True          # 是否需要道路系统

    def __init__(self, vehicle_key: str = "suv", caravan_key: str = "L"):
        self.vehicle_key = vehicle_key
        self.caravan_key = caravan_key

        # 加载配置
        self.vehicles_cfg = _load_yaml("vehicles.yaml")
        self.caravans_cfg = _load_yaml("caravans.yaml")
        self.scenarios_cfg = _load_yaml("scenarios.yaml")

        self.vehicle = self.vehicles_cfg["vehicles"][vehicle_key]
        self.caravan = self.caravans_cfg["caravans"][caravan_key]
        self.scenario = self.scenarios_cfg["scenarios"][self.scenario_key]

    # ========== 属性 ==========

    @property
    def vehicle_half_width(self) -> float:
        """车辆半宽 (m)。"""
        return self.vehicle["dimensions"]["body_width"] / 2

    @property
    def caravan_half_width(self) -> float:
        """房车半宽 (m)。"""
        return self.caravan["dimensions"]["body_width"] / 2

    @property
    def x_outer(self) -> float:
        """车辆+房车组合的最大半宽（用于 R46 计算）。"""
        return max(self.vehicle_half_width, self.caravan_half_width)

    @property
    def eye_point(self) -> list:
        """驾驶员 P50 眼点坐标 [x, y, z]。"""
        return list(self.vehicle["eye_point"]["reference"])

    @property
    def eye_y(self) -> float:
        """驾驶员眼点 Y 坐标。"""
        return self.eye_point[1]

    @property
    def caravan_front_wall_y(self) -> float:
        """房车前壁 Y 坐标。"""
        positions = self.caravans_cfg["caravan_positions"]
        return positions[self.vehicle_key][self.caravan_key]

    # ========== 车道位置计算 ==========

    def get_lane_x(self, lane_num: int) -> float:
        """
        计算指定车道中心相对于车辆原点的 X 坐标。

        参数:
            lane_num: 车道编号（从中央分隔带起算，1-indexed）

        返回:
            X 偏移量（相对于车辆原点）
        """
        preset_name = self.scenario.get("road_preset")
        if not preset_name:
            return 0

        road_presets = self.scenarios_cfg.get("road_presets", {})
        # 也从 test_scene.yaml 查找
        scene_cfg = _load_yaml("test_scene.yaml")
        all_presets = {**scene_cfg.get("presets", {}), **road_presets}

        preset = all_presets.get(preset_name, {})
        lw = preset.get("lane_width", 3.75)
        mw = preset.get("median_width", 1.5)

        vehicle_lane = self.scenario.get("vehicle_lane", 1)

        # 各车道中心距道路中心线的距离
        lane_center = mw / 2 + (lane_num - 1) * lw + lw / 2
        vehicle_center = mw / 2 + (vehicle_lane - 1) * lw + lw / 2

        return lane_center - vehicle_center

    # ========== 构建流程 ==========

    def build(self):
        """构建完整场景。"""
        self._clean_defaults()
        self._setup_environment()

        if self.needs_road:
            self._create_road()
        else:
            self._create_parking_ground()

        self.create_scenario_objects()

        setup_render_settings()

        print("=" * 50)
        print(f"场景 [{self.scenario['display_name']}] 创建完成!")
        print(f"  车辆: {self.vehicle['display_name']}")
        print(f"  房车: {self.caravan['display_name']}")
        print("=" * 50)

    def _clean_defaults(self):
        """清理 Blender 默认物体。"""
        for name in ["Cube", "Light", "Camera"]:
            obj = bpy.data.objects.get(name)
            if obj:
                bpy.data.objects.remove(obj, do_unlink=True)

    def _setup_environment(self):
        """设置光照和天空。"""
        setup_lighting()

    def _create_road(self):
        """创建道路系统。"""
        preset_name = self.scenario.get("road_preset", "highway")
        vehicle_lane = self.scenario.get("vehicle_lane", 1)

        self.road_collection, self.road_offset_x = create_road_system(
            preset_name=preset_name,
            vehicle_lane=vehicle_lane,
        )

        # 草地地面
        create_ground_plane()

    def _create_parking_ground(self):
        """创建停车场地面（用于无道路的场景）。"""
        from objects.road_system import create_parking_surface

        surface_cfg = self.scenario.get("surface", {})
        dims = surface_cfg.get("dimensions", [40, 60])
        center = surface_cfg.get("center", [0, -20])
        color = tuple(surface_cfg.get("color", [0.30, 0.30, 0.30, 1.0]))

        create_parking_surface(
            width=dims[0], length=dims[1],
            center_y=center[1], color=color,
        )

        # 周围草地
        create_ground_plane(size=200, center_y=-20)

    # ========== 驾驶员视野 ==========

    def setup_driver_view(self, vehicle_objects: list):
        """
        设置驾驶员视野验证：创建驾驶员摄像机 + 设置车辆穿透。

        在导入车辆模型后调用。车辆对摄像机不可见（可穿透），
        但对镜面反射仍然可见。

        参数:
            vehicle_objects: 已导入的车辆 Blender 对象列表

        返回:
            驾驶员摄像机对象
        """
        from mirror_builder import create_driver_camera, set_vehicle_ray_visibility

        set_vehicle_ray_visibility(vehicle_objects)
        cam = create_driver_camera(
            vehicle_key=self.vehicle_key,
            vehicles_config=self.vehicles_cfg,
        )
        return cam

    # ========== 子类接口 ==========

    def create_scenario_objects(self):
        """
        子类实现：创建场景特有的物体。

        在 build() 流程中，道路/光照/渲染已配置好后调用。
        """
        raise NotImplementedError("子类必须实现 create_scenario_objects()")
