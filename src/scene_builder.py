"""
场景构建器 — 顶层入口

在 Blender Python 控制台中使用:

    import sys
    sys.path.insert(0, '/path/to/VMirror-SiM/src')
    from scene_builder import build_scenario

    # 创建高速公路场景 (SUV + 大型房车)
    build_scenario('highway', 'suv', 'L')

    # 创建停车场场景 (皮卡 + 中型房车)
    build_scenario('parking', 'pickup', 'M')

    # 创建 R46 法规验证场景 (小车 + 大型房车 — 最差情况)
    build_scenario('regulatory', 'hatchback', 'L')

    # 创建变道检测场景
    build_scenario('lane_change', 'suv', 'L')

    # 变道检测 — 单个距离（用于批量渲染）
    build_lane_change_single('suv', 'L', side='left', distance=20)
"""

from scenarios import (
    HighwayScenario,
    LaneChangeScenario,
    ParkingScenario,
    RegulatoryScenario,
)

_SCENARIO_CLASSES = {
    "highway": HighwayScenario,
    "parking": ParkingScenario,
    "regulatory": RegulatoryScenario,
    "lane_change": LaneChangeScenario,
}

# 可选的车辆和房车键名（供参考）
VEHICLE_KEYS = ["suv", "pickup", "wagon", "hatchback"]
CARAVAN_KEYS = ["S", "M", "L"]


def build_scenario(
    scenario_name: str,
    vehicle_key: str = "suv",
    caravan_key: str = "L",
):
    """
    构建指定场景。

    参数:
        scenario_name: 场景名称 ('highway', 'parking', 'regulatory', 'lane_change')
        vehicle_key: 车辆类型 ('suv', 'pickup', 'wagon', 'hatchback')
        caravan_key: 房车尺寸 ('S', 'M', 'L')

    返回:
        场景实例
    """
    if scenario_name not in _SCENARIO_CLASSES:
        available = ", ".join(_SCENARIO_CLASSES.keys())
        raise ValueError(f"Unknown scenario: '{scenario_name}'. Available: {available}")

    scenario_class = _SCENARIO_CLASSES[scenario_name]
    scenario = scenario_class(vehicle_key, caravan_key)
    scenario.build()
    return scenario


def build_lane_change_single(
    vehicle_key: str = "suv",
    caravan_key: str = "L",
    side: str = "left",
    distance: float = 20,
):
    """
    构建变道检测场景（单个距离，用于批量渲染）。

    参数:
        vehicle_key: 车辆类型
        caravan_key: 房车尺寸
        side: 'left' 或 'right'
        distance: 后方距离 (m)

    返回:
        场景实例
    """
    scenario = LaneChangeScenario(vehicle_key, caravan_key)
    scenario.build_single(side, distance)
    return scenario


def list_scenarios():
    """列出所有可用场景。"""
    import yaml
    import pathlib

    config_dir = pathlib.Path(__file__).resolve().parent.parent / "config"
    with open(config_dir / "scenarios.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    print("=" * 50)
    print("可用场景:")
    print("=" * 50)
    for key, scenario in cfg["scenarios"].items():
        print(f"  {key:15s} — {scenario['display_name']}")
        print(f"  {'':15s}   {scenario['description']}")
        print()

    print("车辆类型:", ", ".join(VEHICLE_KEYS))
    print("房车尺寸:", ", ".join(CARAVAN_KEYS))
    print()
    print("使用示例:")
    print("  build_scenario('highway', 'suv', 'L')")


if __name__ == "__main__":
    list_scenarios()
