"""
场景 1：高速公路行驶（3车道）

3车道高速公路，车辆+房车位于中央车道，左右后方各有参考车辆。
用于真实驾驶环境下的视野验证。
"""

from objects.reference_vehicle import create_reference_vehicle
from objects.road_system import create_collection, create_guardrail
from scenarios.base import BaseScenario


class HighwayScenario(BaseScenario):
    scenario_key = "highway"
    needs_road = True

    def create_scenario_objects(self):
        """创建高速公路场景的参考车辆和护栏。"""
        obj_collection = create_collection("Highway_Objects")

        # --- 参考车辆 ---
        ref_vehicles = self.scenario.get("reference_vehicles", [])
        for rv in ref_vehicles:
            lane_num = rv["lane"]
            lane_x = self.get_lane_x(lane_num)
            y = rv["y_offset"]
            dims = tuple(rv["dimensions"])
            color = tuple(rv["color"])
            name = f"RefVehicle_{rv['id']}"

            create_reference_vehicle(
                name=name,
                position=(lane_x, y),
                dimensions=dims,
                color=color,
                collection=obj_collection,
            )
            print(f"  参考车辆: {rv['label']} -> ({lane_x:.2f}, {y})")

        # --- 中央护栏 ---
        guardrail_cfg = self.scenario.get("guardrail", {})
        gh = guardrail_cfg.get("height", 0.8)
        gw = guardrail_cfg.get("width", 0.12)
        gc = tuple(guardrail_cfg.get("color", [0.6, 0.6, 0.6, 1.0]))

        # 中央分隔带护栏（在快车道内侧）
        preset_name = self.scenario.get("road_preset", "highway_3lane")
        from objects.road_system import _load_road_preset
        preset = _load_road_preset(preset_name)
        mw = preset.get("median_width", 1.5)
        vehicle_lane = self.scenario.get("vehicle_lane", 2)
        lw = preset.get("lane_width", 3.75)

        # 中央护栏 X 位置（相对于车辆）
        median_x = -(mw / 2 + (vehicle_lane - 1) * lw + lw / 2) + mw / 2
        # 简化：护栏在中央分隔带两侧
        create_guardrail(
            "Guardrail_Median_Near", median_x + 0.2,
            height=gh, width=gw, color=gc, collection=obj_collection,
        )
        create_guardrail(
            "Guardrail_Median_Far", median_x - 0.2,
            height=gh, width=gw, color=gc, collection=obj_collection,
        )

        print(f"  护栏已创建 (H={gh}m)")
