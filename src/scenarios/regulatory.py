"""
场景 3：UN ECE R46 法规验证

基于 UN ECE R46 Class III 法规要求，在地面标记可视区域边界，
并在关键位置放置测试柱，用于验证后视镜是否满足法规视野要求。

法规要点 (Class III, 15.2.4.3.2):
- 副驾驶侧远场: 从眼点后 20m 到地平线，可见宽度 ≥ 4m，从最外侧点起算
- 副驾驶侧近场: 从眼点后 4m 到 20m，可见宽度 ≥ 1m，从最外侧点起算
- 驾驶员侧: 镜像对称
"""

from objects.regulatory_zone import (
    create_r46_boundary_line,
    create_r46_test_pole,
    create_r46_zone,
)
from objects.road_system import create_collection
from scenarios.base import BaseScenario


class RegulatoryScenario(BaseScenario):
    scenario_key = "regulatory"
    needs_road = True

    def create_scenario_objects(self):
        """创建 R46 法规验证场景的区域标记和测试柱。"""
        zone_collection = create_collection("R46_Zones")
        pole_collection = create_collection("R46_Test_Poles")

        # 读取法规参数
        r46 = self.scenario.get("r46_class_iii", {})
        near_w = r46.get("near_field_width", 1.0)
        near_start = r46.get("near_field_start", 4.0)
        near_end = r46.get("near_field_end", 20.0)
        far_w = r46.get("far_field_width", 4.0)
        far_start = r46.get("far_field_start", 20.0)
        far_end = r46.get("far_field_end", 80.0)

        # 计算关键坐标
        x_outer = self.x_outer
        y_eye = self.eye_y

        zone_colors = self.scenario.get("zone_colors", {})
        boundary_cfg = self.scenario.get("boundary_line", {})
        pole_cfg = self.scenario.get("test_pole", {})

        print(f"  X_outer = {x_outer:.3f}m (max(车辆半宽={self.vehicle_half_width:.3f}, 房车半宽={self.caravan_half_width:.3f}))")
        print(f"  Y_eye = {y_eye:.3f}m")

        # ========== 副驾驶侧 (+X) ==========

        # 近场区域: X ∈ [X_outer, X_outer + near_w], Y ∈ [Y_eye - near_end, Y_eye - near_start]
        pass_near_color = tuple(zone_colors.get("passenger_near", [0.2, 0.8, 0.2, 0.3]))
        create_r46_zone(
            "R46_Passenger_Near",
            x_start=x_outer,
            x_end=x_outer + near_w,
            y_start=y_eye - near_end,
            y_end=y_eye - near_start,
            color=pass_near_color,
            collection=zone_collection,
        )
        print(f"  副驾近场: X=[{x_outer:.2f}, {x_outer + near_w:.2f}], Y=[{y_eye - near_end:.2f}, {y_eye - near_start:.2f}]")

        # 远场区域: X ∈ [X_outer, X_outer + far_w], Y ∈ [Y_eye - far_end, Y_eye - far_start]
        pass_far_color = tuple(zone_colors.get("passenger_far", [0.2, 0.2, 0.8, 0.3]))
        create_r46_zone(
            "R46_Passenger_Far",
            x_start=x_outer,
            x_end=x_outer + far_w,
            y_start=y_eye - far_end,
            y_end=y_eye - far_start,
            color=pass_far_color,
            collection=zone_collection,
        )
        print(f"  副驾远场: X=[{x_outer:.2f}, {x_outer + far_w:.2f}], Y=[{y_eye - far_end:.2f}, {y_eye - far_start:.2f}]")

        # ========== 驾驶员侧 (-X, 镜像) ==========

        drv_near_color = tuple(zone_colors.get("driver_near", [0.8, 0.8, 0.2, 0.3]))
        create_r46_zone(
            "R46_Driver_Near",
            x_start=-x_outer - near_w,
            x_end=-x_outer,
            y_start=y_eye - near_end,
            y_end=y_eye - near_start,
            color=drv_near_color,
            collection=zone_collection,
        )

        drv_far_color = tuple(zone_colors.get("driver_far", [0.8, 0.2, 0.2, 0.3]))
        create_r46_zone(
            "R46_Driver_Far",
            x_start=-x_outer - far_w,
            x_end=-x_outer,
            y_start=y_eye - far_end,
            y_end=y_eye - far_start,
            color=drv_far_color,
            collection=zone_collection,
        )

        # ========== 最外侧平面标线 ==========

        bl_width = boundary_cfg.get("width", 0.10)
        bl_color = tuple(boundary_cfg.get("color", [1.0, 0.5, 0.0, 1.0]))

        create_r46_boundary_line(
            "R46_Boundary_Passenger", x_outer,
            y_start=y_eye - far_end, y_end=0,
            width=bl_width, color=bl_color, collection=zone_collection,
        )
        create_r46_boundary_line(
            "R46_Boundary_Driver", -x_outer,
            y_start=y_eye - far_end, y_end=0,
            width=bl_width, color=bl_color, collection=zone_collection,
        )

        # ========== 测试柱 ==========

        pole_h = pole_cfg.get("height", 1.0)
        pole_r = pole_cfg.get("radius", 0.05)
        pole_color = tuple(pole_cfg.get("color", [0.95, 0.95, 0.95, 1.0]))

        # 副驾驶侧测试柱
        passenger_poles = [
            ("P1_Pass_FarInner_20m", x_outer + 0.5, y_eye - far_start),
            ("P2_Pass_FarOuter_20m", x_outer + far_w, y_eye - far_start),
            ("P3_Pass_NearMid_4m", x_outer + 0.5, y_eye - near_start),
            ("P4_Pass_NearOuter_4m", x_outer + near_w, y_eye - near_start),
            ("P5_Pass_FarMid_40m", x_outer + far_w / 2, y_eye - 40),
        ]

        for name, px, py in passenger_poles:
            create_r46_test_pole(
                f"R46_{name}", position=(px, py),
                height=pole_h, radius=pole_r, color=pole_color,
                collection=pole_collection,
            )

        # 驾驶员侧测试柱（镜像）
        driver_poles = [
            ("P1_Drv_FarInner_20m", -x_outer - 0.5, y_eye - far_start),
            ("P2_Drv_FarOuter_20m", -x_outer - far_w, y_eye - far_start),
            ("P3_Drv_NearMid_4m", -x_outer - 0.5, y_eye - near_start),
            ("P4_Drv_NearOuter_4m", -x_outer - near_w, y_eye - near_start),
            ("P5_Drv_FarMid_40m", -x_outer - far_w / 2, y_eye - 40),
        ]

        for name, px, py in driver_poles:
            create_r46_test_pole(
                f"R46_{name}", position=(px, py),
                height=pole_h, radius=pole_r, color=pole_color,
                collection=pole_collection,
            )

        print(f"  测试柱: {len(passenger_poles) + len(driver_poles)} 根")
        print(f"  验证方法: 渲染后视镜视角 → 检查 P1-P5 是否可见")
