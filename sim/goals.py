"""goals.py — 目标库（12 个参数组）。

每个目标是一组参数，AI 决策读取该参数组，而非硬编码 if-else。
"""

from dataclasses import dataclass, field
from typing import Dict

from .models import IG_IDS


@dataclass
class GoalParams:
    key: str
    name: str
    tax_bias: float
    build_priority: Dict[str, float]       # {farm, mine, factory}
    reform_stance: int                     # -2 镇压 -1 压制 0 中立 +1 改革 +2 激进
    military_spending: float
    welfare_spending: float
    tech_bias: float
    diffuse_resist: float
    ig_affinity: Dict[str, float]          # 7 个 IG 亲和度 -1~+1


def _aff(*vals: float) -> Dict[str, float]:
    """7 个值按 IG_IDS 顺序打包成亲和度 dict。"""
    return dict(zip(IG_IDS, vals))


def _bp(farm: float, mine: float, factory: float) -> Dict[str, float]:
    return {"farm": farm, "mine": mine, "factory": factory}


GOALS: Dict[str, GoalParams] = {
    "industrialize": GoalParams(
        "industrialize", "工业化优先", 0.20, _bp(0.05, 0.25, 0.70), +1,
        0.05, 0.02, 0.15, 0.0,
        _aff(-0.2, 0.6, 0.5, -0.5, -0.4, 0.8, -0.1)),
    "stabilize": GoalParams(
        "stabilize", "稳定优先", 0.15, _bp(0.40, 0.30, 0.30), -1,
        0.15, 0.05, 0.08, 0.1,
        _aff(0.3, -0.4, -0.2, 0.5, 0.4, -0.1, 0.5)),
    "reform": GoalParams(
        "reform", "改革优先", 0.25, _bp(0.40, 0.20, 0.40), +2,
        0.05, 0.10, 0.12, 0.0,
        _aff(0.2, 0.7, 0.7, -0.6, -0.5, 0.3, -0.3)),
    "balance": GoalParams(
        "balance", "均衡发展", 0.18, _bp(0.33, 0.33, 0.33), 0,
        0.08, 0.06, 0.10, 0.0,
        _aff(0.1, 0.2, 0.2, 0.1, 0.0, 0.2, 0.0)),
    "military": GoalParams(
        "military", "军事扩张", 0.30, _bp(0.20, 0.30, 0.50), -1,
        0.35, 0.02, 0.10, 0.0,
        _aff(0.0, -0.3, -0.1, 0.2, 0.2, 0.1, 0.9)),
    "mercantilist": GoalParams(
        "mercantilist", "重商主义", 0.28, _bp(0.20, 0.40, 0.40), 0,
        0.10, 0.02, 0.12, 0.2,
        _aff(-0.1, 0.3, 0.2, -0.2, -0.1, 0.7, 0.2)),
    "agrarian": GoalParams(
        "agrarian", "农业保守", 0.12, _bp(0.80, 0.10, 0.10), -2,
        0.08, 0.03, 0.04, 0.3,
        _aff(0.8, -0.5, -0.4, 0.7, 0.3, -0.5, -0.1)),
    "revolutionary": GoalParams(
        "revolutionary", "激进革命", 0.35, _bp(0.10, 0.30, 0.60), +2,
        0.10, 0.08, 0.15, 0.0,
        _aff(0.5, 0.9, 0.6, -0.8, -0.6, -0.3, -0.5)),
    "isolationist": GoalParams(
        "isolationist", "孤立主义", 0.15, _bp(0.50, 0.25, 0.25), -1,
        0.12, 0.05, 0.05, 0.6,
        _aff(0.4, -0.2, -0.3, 0.3, 0.3, -0.2, 0.2)),
    "theocracy": GoalParams(
        "theocracy", "神权统治", 0.20, _bp(0.40, 0.30, 0.30), -2,
        0.10, 0.04, 0.06, 0.5,
        _aff(0.2, -0.7, -0.6, 0.2, 0.9, -0.4, 0.0)),
    "welfare": GoalParams(
        "welfare", "福利国家", 0.32, _bp(0.40, 0.20, 0.40), +1,
        0.04, 0.15, 0.10, 0.0,
        _aff(0.3, 0.7, 0.4, -0.4, -0.1, 0.1, -0.2)),
    "enlightenment": GoalParams(
        "enlightenment", "科技启蒙", 0.22, _bp(0.20, 0.30, 0.50), +1,
        0.05, 0.05, 0.20, 0.0,
        _aff(-0.1, 0.5, 0.8, -0.5, -0.6, 0.4, -0.1)),
}

GOAL_KEYS = list(GOALS.keys())


def get_goal(key: str) -> GoalParams:
    return GOALS.get(key, GOALS["balance"])
