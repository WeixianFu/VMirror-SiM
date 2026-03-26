"""
场景物体构建模块

提供参考车辆、交通锥、R46法规标记等场景物体的 Blender 创建函数。
"""

from objects.reference_vehicle import create_reference_vehicle
from objects.traffic_cone import create_traffic_cone, create_reference_pole
from objects.regulatory_zone import create_r46_zone, create_r46_boundary_line, create_r46_test_pole
from objects.road_system import create_road_system, create_ground_plane, setup_lighting

__all__ = [
    "create_reference_vehicle",
    "create_traffic_cone",
    "create_reference_pole",
    "create_r46_zone",
    "create_r46_boundary_line",
    "create_r46_test_pole",
    "create_road_system",
    "create_ground_plane",
    "setup_lighting",
]
