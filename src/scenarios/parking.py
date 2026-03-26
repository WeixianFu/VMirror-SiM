"""
场景 2：停车场静态测试

开阔停车场地面，雪糕桶和立杆组成参考物网格。
用于受控环境下的系统化可见性测试。
"""

import numpy as np

from objects.road_system import create_collection
from objects.traffic_cone import (
    create_landmark_cube,
    create_reference_pole,
    create_traffic_cone,
)
from scenarios.base import BaseScenario


class ParkingScenario(BaseScenario):
    scenario_key = "parking"
    needs_road = False

    def create_scenario_objects(self):
        """创建停车场场景的参考物网格和地标。"""
        grid_collection = create_collection("Parking_Reference_Grid")
        landmark_collection = create_collection("Parking_Landmarks")

        # --- 参考物网格 ---
        grid_cfg = self.scenario.get("reference_grid", {})
        x_range = grid_cfg.get("x_range", [-12, 12])
        x_spacing = grid_cfg.get("x_spacing", 2.0)
        y_range = grid_cfg.get("y_range", [-4, -40])
        y_spacing = grid_cfg.get("y_spacing", 4.0)

        cone_cfg = grid_cfg.get("cone", {})
        pole_cfg = grid_cfg.get("pole", {})

        # 生成网格位置
        x_positions = np.arange(x_range[0], x_range[1] + x_spacing / 2, x_spacing)
        y_positions = np.arange(y_range[0], y_range[1] - y_spacing / 2, -y_spacing)

        obj_count = 0
        for yi, y in enumerate(y_positions):
            is_cone_row = yi % 2 == 0

            for xi, x in enumerate(x_positions):
                if is_cone_row:
                    create_traffic_cone(
                        name=f"Cone_X{x:+.1f}_Y{y:+.1f}",
                        position=(x, y),
                        height=cone_cfg.get("height", 0.5),
                        base_radius=cone_cfg.get("base_radius", 0.15),
                        top_radius=cone_cfg.get("top_radius", 0.02),
                        color=tuple(cone_cfg.get("color", [1.0, 0.5, 0.0, 1.0])),
                        collection=grid_collection,
                    )
                else:
                    create_reference_pole(
                        name=f"Pole_X{x:+.1f}_Y{y:+.1f}",
                        position=(x, y),
                        height=pole_cfg.get("height", 1.0),
                        radius=pole_cfg.get("radius", 0.05),
                        color=tuple(pole_cfg.get("color", [0.9, 0.1, 0.1, 1.0])),
                        collection=grid_collection,
                    )
                obj_count += 1

        print(f"  参考物网格: {obj_count} 个物体 ({len(x_positions)} 列 × {len(y_positions)} 行)")

        # --- 特殊地标物 ---
        landmarks = self.scenario.get("landmarks", [])
        for lm in landmarks:
            pos = lm["position"]
            create_landmark_cube(
                name=f"Landmark_{lm['id']}",
                position=(pos[0], pos[1]),
                size=lm.get("size", 1.0),
                color=tuple(lm["color"]),
                collection=landmark_collection,
            )
            print(f"  地标: {lm['id']} -> ({pos[0]}, {pos[1]})")
