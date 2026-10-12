"""interest_group.py — 利益集团（IG）影响力、立场、执政联盟、躁动。"""

from typing import Dict, List

from .config import Config
from .models import (Nation, InterestGroup, IG_IDS, IG_NAMES,
                     GOVERNMENT_COALITION)

# IG → 代表职业
IG_MEMBER_PROFESSIONS: Dict[str, List[str]] = {
    "rural_folk": ["peasants"],
    "trade_unions": ["laborers"],
    "intelligentsia": ["clerks", "bureaucrats"],
    "landowners": ["aristocrats"],
    "church": ["clergymen"],
    "industrialists": ["capitalists"],
    "military": ["servicemen"],
}

# IG 基础改革立场
IG_BASE_STANCE: Dict[str, float] = {
    "rural_folk": -0.3, "trade_unions": 0.8, "intelligentsia": 0.7,
    "landowners": -0.9, "church": -0.7, "industrialists": 0.3,
    "military": -0.2,
}


def init_interest_groups(nation: Nation) -> None:
    """初始化 7 个 IG 对象。"""
    nation.interest_groups = {}
    for ig_id in IG_IDS:
        nation.interest_groups[ig_id] = InterestGroup(
            id=ig_id,
            name=IG_NAMES[ig_id],
            member_professions=list(IG_MEMBER_PROFESSIONS[ig_id]),
        )


def update_influence(nation: Nation, cfg: Config) -> None:
    """影响力 = Σ(size × wealth × (0.5 + awareness))，全体归一化和 = 1。"""
    raw: Dict[str, float] = {ig_id: 0.0 for ig_id in IG_IDS}
    for prov in nation.provinces:
        for p in prov.pops:
            if p.ig_membership in raw:
                raw[p.ig_membership] += (
                    p.size * max(p.wealth, 0.0) * (0.5 + p.political_awareness)
                )
    total = sum(raw.values())
    for ig_id in IG_IDS:
        ig = nation.interest_groups[ig_id]
        ig.influence = raw[ig_id] / total if total > 0 else 0.0


def _peasant_satisfaction(nation: Nation) -> float:
    """rural_folk 成员（peasants）的加权平均满意度。"""
    total = 0.0
    sat = 0.0
    for prov in nation.provinces:
        for p in prov.pops:
            if p.profession == "peasants":
                total += p.size
                sat += p.size * p.satisfaction
    return sat / total if total > 0 else 0.5


def update_stance(nation: Nation, cfg: Config) -> None:
    """计算各 IG 的 stance_on_reform，含 rural_folk 特殊修正。"""
    for ig_id in IG_IDS:
        nation.interest_groups[ig_id].stance_on_reform = IG_BASE_STANCE[ig_id]

    rf = nation.interest_groups["rural_folk"]
    church_inf = nation.interest_groups["church"].influence
    # 1) 农民不满 → 从保守变激进
    if _peasant_satisfaction(nation) < 0.3:
        rf.stance_on_reform += 0.8
    # 2) 地租压迫过重（地租率 > 0.35）
    if nation.rent_rate > 0.35:
        rf.stance_on_reform += 0.3
    # 3) 教会影响力高 → 安抚农民，趋于保守
    if church_inf > 0.3:
        rf.stance_on_reform -= 0.2


def apply_government(nation: Nation, cfg: Config) -> None:
    """根据政治制度设置执政 IG（in_government）。"""
    sys = nation.political_system
    if sys in ("republic", "democracy"):
        # 选举：按影响力选 top 3；democracy 放大工会影响力
        weights = {ig_id: ig.influence
                   for ig_id, ig in nation.interest_groups.items()}
        if sys == "democracy":
            weights["trade_unions"] *= 1.5
        top3 = sorted(weights, key=weights.get, reverse=True)[:3]
        for ig_id, ig in nation.interest_groups.items():
            ig.in_government = ig_id in top3
    else:
        coalition = GOVERNMENT_COALITION.get(sys, [])
        for ig_id, ig in nation.interest_groups.items():
            ig.in_government = ig_id in coalition


def update_agitation_opposition(nation: Nation, cfg: Config) -> None:
    """在野 IG 每年躁动 +AGITATE_OPPOSITION。"""
    for ig in nation.interest_groups.values():
        if not ig.in_government:
            ig.agitation = min(1.0, ig.agitation + cfg.AGITATE_OPPOSITION)
