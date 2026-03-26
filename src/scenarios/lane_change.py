"""
场景 4：变道检测

后方接近车辆在不同距离下的可见性测试。
每个距离单独渲染一帧，生成"检测距离-可见性"图表。
"""

from objects.reference_vehicle import create_reference_vehicle
from objects.road_system import create_collection
from scenarios.base import BaseScenario


class LaneChangeScenario(BaseScenario):
    scenario_key = "lane_change"
    needs_road = True

    def create_scenario_objects(self):
        """
        创建变道检测场景的接近车辆。

        默认创建所有距离的车辆（不同透明度区分远近）。
        批量渲染时可通过 build_single() 只创建单个距离的车辆。
        """
        collection = create_collection("LaneChange_Vehicles")

        approaching = self.scenario.get("approaching_vehicle", {})
        dims = tuple(approaching.get("dimensions", [1.85, 4.5, 1.5]))
        base_color = list(approaching.get("color", [0.85, 0.15, 0.15, 1.0]))
        distances = approaching.get("distances", [10, 20, 30, 50, 70])
        lanes = approaching.get("lanes", {})

        for side_name, lane_num in lanes.items():
            lane_x = self.get_lane_x(lane_num)

            for dist in distances:
                y = -dist

                # 近处不透明，远处半透明（便于区分）
                alpha = max(0.3, 1.0 - (dist - 10) / 80)
                color = (base_color[0], base_color[1], base_color[2], alpha)

                name = f"Approaching_{side_name}_{dist}m"
                create_reference_vehicle(
                    name=name,
                    position=(lane_x, y),
                    dimensions=dims,
                    color=color,
                    collection=collection,
                )

            print(f"  {side_name} 车道 (X={lane_x:+.2f}): {len(distances)} 个距离")

        print(f"  共 {len(lanes) * len(distances)} 辆参考车")
        print(f"  距离: {distances}")

    def build_single(self, side: str, distance: float):
        """
        构建只包含单个参考车辆的场景（用于批量渲染）。

        参数:
            side: 'left' 或 'right'
            distance: 后方距离 (m)
        """
        self._clean_defaults()
        self._setup_environment()
        self._create_road()

        collection = create_collection("LaneChange_Single")

        approaching = self.scenario.get("approaching_vehicle", {})
        dims = tuple(approaching.get("dimensions", [1.85, 4.5, 1.5]))
        color = tuple(approaching.get("color", [0.85, 0.15, 0.15, 1.0]))
        lanes = approaching.get("lanes", {})

        lane_num = lanes.get(side, 1 if side == "left" else 3)
        lane_x = self.get_lane_x(lane_num)

        from objects.road_system import setup_render_settings
        setup_render_settings()

        create_reference_vehicle(
            name=f"Approaching_{side}_{distance}m",
            position=(lane_x, -distance),
            dimensions=dims,
            color=color,
            collection=collection,
        )

        print(f"  变道检测: {side} 车道, 距离 {distance}m")
