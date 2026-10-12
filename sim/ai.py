"""ai.py — AI 决策（年度第 4 步）。

读取目标参数组 GoalParams，决定税率、建造、改革立场，
并评估 7 个 IG 的反应（受益/受损 → 调整 agitation）。
"""

from typing import Dict, List, Optional

from .config import Config
from .models import Nation


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _adjust_ig(nation: Nation, ig_ids: List[str], delta: float) -> None:
    for ig_id in ig_ids:
        ig = nation.interest_groups.get(ig_id)
        if ig is not None:
            ig.agitation = _clamp(ig.agitation + delta, 0.0, 1.0)


def _set_tax(nation: Nation, goal, cfg: Config) -> None:
    """税率 = tax_bias × (1 + 赤字压力)，clamp 到 [TAX_MIN, TAX_MAX]。"""
    deficit = max(0.0, -nation.treasury) / max(nation.gdp, 1.0)
    nation.tax_rate = _clamp(goal.tax_bias * (1.0 + deficit),
                             cfg.TAX_MIN, cfg.TAX_MAX)
    # 高税率的 IG 反应
    if nation.tax_rate > 0.3:
        _adjust_ig(nation, ["military", "intelligentsia"], -cfg.AGITATE_BENEFIT)
        _adjust_ig(nation, ["industrialists", "trade_unions", "rural_folk"],
                   +cfg.AGITATE_HARM)


def _build_one(nation: Nation, kind: str, cost: float) -> None:
    if kind == "farm":
        prov = max(nation.provinces, key=lambda p: p.land_quality)
        prov.farms += 1
    elif kind == "mine":
        prov = max(nation.provinces, key=lambda p: p.coal_deposit)
        prov.mines += 1
    else:
        prov = max(nation.provinces, key=lambda p: p.coal_deposit + p.land_quality)
        prov.factories += 1
    nation.treasury -= cost


def _apply_build_agitation(nation: Nation, kind: str, cfg: Config) -> None:
    if kind == "factory":
        _adjust_ig(nation, ["trade_unions", "intelligentsia", "industrialists"],
                   -cfg.AGITATE_BENEFIT)
        _adjust_ig(nation, ["landowners", "church", "rural_folk"], +cfg.AGITATE_HARM)
    elif kind == "farm":
        _adjust_ig(nation, ["rural_folk", "landowners"], -cfg.AGITATE_BENEFIT)
    elif kind == "mine":
        _adjust_ig(nation, ["trade_unions", "industrialists"], -cfg.AGITATE_BENEFIT)
        _adjust_ig(nation, ["rural_folk"], +cfg.AGITATE_HARM)


def _build(nation: Nation, goal, cfg: Config) -> None:
    """按 build_priority 权重贪心建造，受国库与年度上限约束。"""
    costs = {"farm": cfg.BUILD_COST_FARM, "mine": cfg.BUILD_COST_MINE,
             "factory": cfg.BUILD_COST_FACTORY}
    order = sorted(goal.build_priority, key=goal.build_priority.get, reverse=True)
    built = 0
    for kind in order:
        cost = costs[kind]
        while built < cfg.MAX_NEW_BUILD and nation.treasury >= cost:
            _build_one(nation, kind, cost)
            _apply_build_agitation(nation, kind, cfg)
            built += 1


def _reform_agitation(nation: Nation, goal, cfg: Config) -> None:
    """改革立场的 IG 反应（推进/镇压）。"""
    stance = goal.reform_stance
    if stance > 0:
        _adjust_ig(nation, ["trade_unions", "intelligentsia", "industrialists"],
                   -cfg.AGITATE_BENEFIT)
        _adjust_ig(nation, ["landowners", "church"], +cfg.AGITATE_HARM)
    elif stance < 0:
        _adjust_ig(nation, ["landowners", "church", "military"],
                   -cfg.AGITATE_BENEFIT)
        _adjust_ig(nation, ["trade_unions", "intelligentsia"], +cfg.AGITATE_HARM)


def decide(nations: List[Nation], cfg: Config,
           goal_map: Optional[Dict] = None, world=None) -> None:
    """4. AI 决策（年末执行，影响下一年）。"""
    goal_map = goal_map or {}
    for n in nations:
        goal = goal_map.get(n.goal)
        if goal is None:
            continue
        _set_tax(n, goal, cfg)
        _build(n, goal, cfg)
        _reform_agitation(n, goal, cfg)
