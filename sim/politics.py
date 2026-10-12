"""politics.py — 政治结算（年度第 3 步）+ 农民起义机制。

顺序：意识增长 → 思想控制 → IG 影响力 → 地租率 → 执政联盟
     → IG 立场 → 改革压力 → 稳定性 → 制度变化 → 在野躁动。
"""

from typing import Dict, List, Optional

import numpy as np

from .config import Config
from .models import Nation, SYSTEM_ORDER, THEOCRACY
from . import interest_group
from .nation import total_pop, pop_by_profession, mean_satisfaction, worker_awareness


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _inequality(nation: Nation) -> float:
    """贫富比 = upper 平均财富 / lower 平均财富（>=1）。"""
    upper_w = lower_w = 0.0
    upper_n = lower_n = 0.0
    for prov in nation.provinces:
        for p in prov.pops:
            if p.profession in ("aristocrats", "capitalists"):
                upper_w += p.size * p.wealth
                upper_n += p.size
            elif p.profession in ("peasants", "laborers"):
                lower_w += p.size * p.wealth
                lower_n += p.size
    if upper_n <= 0 or lower_n <= 0:
        return 1.0
    return (upper_w / upper_n) / max(lower_w / lower_n, 1e-9)


def _step_awareness(nation: Nation, cfg: Config) -> None:
    """每职业政治意识增长（§8.2 + 工业化/贫富/改革/教育修正）。"""
    tp = total_pop(nation)
    if tp <= 0:
        return
    workers = pop_by_profession(nation, "laborers") / tp
    ineq = _inequality(nation)
    for prov in nation.provinces:
        for p in prov.pops:
            base = cfg.AW_BASE.get(p.profession, 0.0)
            delta = (base
                     + cfg.AW_INDUSTRY * workers
                     + cfg.AW_INEQUALITY * max(ineq - 1.0, 0.0)
                     + cfg.AW_REFORM * nation.reform_level
                     + cfg.AW_EDUCATION * nation.tech_level)
            p.political_awareness = _clamp(
                p.political_awareness + delta * cfg.AW_SPEED, 0.0, 1.0)


def _apply_clergy_suppression(nation: Nation, cfg: Config) -> None:
    """思想控制：有效意识 = 意识 × (1 - 教士占比 × 2)。"""
    tp = total_pop(nation)
    if tp <= 0:
        return
    clergy = pop_by_profession(nation, "clergymen") / tp
    factor = max(0.0, 1.0 - clergy * cfg.CLERGY_SUPPRESS)
    for prov in nation.provinces:
        for p in prov.pops:
            p.political_awareness *= factor


def _update_rent_rate(nation: Nation, cfg: Config) -> None:
    """动态地租率：随地主贵族影响力上升（下限 30%，上限 60%）。"""
    landowners_inf = nation.interest_groups["landowners"].influence
    rate = cfg.RENT_RATE * (1.0 + 0.5 * landowners_inf)
    nation.rent_rate = _clamp(rate, cfg.RENT_RATE, 0.6)


def _reform_pressure(nation: Nation) -> float:
    """改革压力 = Σ(influence × stance) × (1 + 工人意识)；执政 IG 立场加倍。"""
    total = 0.0
    for ig in nation.interest_groups.values():
        stance = ig.stance_on_reform
        if ig.in_government:
            stance *= 2.0
        total += ig.influence * stance
    return total * (1.0 + worker_awareness(nation))


def _update_stability(nation: Nation, cfg: Config) -> None:
    """稳定性（§8.6）+ 军人镇压下限 + 被镇压长期受损。"""
    church_inf = nation.interest_groups["church"].influence
    gov_count = sum(1 for ig in nation.interest_groups.values() if ig.in_government)
    sat = mean_satisfaction(nation)
    stab = (cfg.STAB_BASE
            + cfg.STAB_SAT * (sat - 0.5)
            - cfg.STAB_PRESS * abs(nation.reform_pressure)
            - cfg.STAB_TAX * (nation.tax_rate - 0.2)
            + cfg.STAB_IG * gov_count
            + cfg.STAB_CLERGY * church_inf)
    nation.stability = _clamp(stab, 0.0, 1.0)

    # 军人镇压能力：servicemen 超 5% 时稳定下限提升
    tp = total_pop(nation)
    if tp > 0 and pop_by_profession(nation, "servicemen") / tp > cfg.SERVICEMEN_CAP_RATIO:
        nation.stability = max(nation.stability, cfg.STAB_FLOOR_SERVICEMEN)

    # 被镇压长期受损
    if nation.suppressed:
        nation.stability = max(0.0, nation.stability - 0.1)
        if nation.stability > 0.6:
            nation.suppressed = False


def _advance_system(nation: Nation) -> None:
    if nation.political_system in SYSTEM_ORDER:
        idx = SYSTEM_ORDER.index(nation.political_system)
        if idx < len(SYSTEM_ORDER) - 1:
            nation.political_system = SYSTEM_ORDER[idx + 1]


def _regress_system(nation: Nation) -> None:
    if nation.political_system in SYSTEM_ORDER:
        idx = SYSTEM_ORDER.index(nation.political_system)
        if idx > 0:
            nation.political_system = SYSTEM_ORDER[idx - 1]


def _update_system(nation: Nation, cfg: Config, goal) -> None:
    """制度变化：压力高前进、压力低倒退、教会强则 theocracy。

    改革立场（reform_stance）通过 AI_REFORM_PUSH 调整有效压力：
    推进（+）更容易触发改革，镇压（-）更难。
    """
    stance = goal.reform_stance if goal else 0
    eff_pressure = nation.reform_pressure + stance * cfg.AI_REFORM_PUSH
    if nation.reform_cooldown > 0:
        nation.reform_cooldown -= 1
    else:
        if eff_pressure > cfg.REFORM_THRESH:
            nation.reform_level = _clamp(nation.reform_level + cfg.REFORM_STEP, 0.0, 1.0)
            _advance_system(nation)
            nation.reform_cooldown = cfg.REFORM_COOLDOWN
        elif eff_pressure < cfg.REGRESS_THRESH:
            nation.reform_level = _clamp(nation.reform_level - cfg.REFORM_STEP, 0.0, 1.0)
            _regress_system(nation)
            nation.reform_cooldown = cfg.REFORM_COOLDOWN

    if nation.interest_groups["church"].influence > cfg.CHURCH_THEOCRACY:
        nation.political_system = THEOCRACY


def settle(nations: List[Nation], cfg: Config,
           goal_map: Optional[Dict] = None) -> None:
    """3. 政治结算。"""
    goal_map = goal_map or {}
    for n in nations:
        _step_awareness(n, cfg)
        _apply_clergy_suppression(n, cfg)
        interest_group.update_influence(n, cfg)
        _update_rent_rate(n, cfg)
        interest_group.apply_government(n, cfg)
        interest_group.update_stance(n, cfg)
        n.reform_pressure = _reform_pressure(n)
        _update_stability(n, cfg)
        _update_system(n, cfg, goal_map.get(n.goal))
        interest_group.update_agitation_opposition(n, cfg)


def check_peasant_uprising(nation: Nation, rng: np.random.Generator,
                           cfg: Config) -> bool:
    """农民起义机制（§6）。返回是否触发。"""
    rf = nation.interest_groups.get("rural_folk")
    if rf is None:
        return False
    if not (rf.agitation > cfg.UPRISING_AGITATION
            and rf.influence > cfg.UPRISING_INFLUENCE):
        return False

    nation.stability = max(0.0, nation.stability - cfg.UPRISING_STAB_HIT)
    for ig in nation.interest_groups.values():
        ig.agitation = _clamp(ig.agitation + cfg.UPRISING_AGITATE_SPREAD, 0.0, 1.0)

    sys = nation.political_system
    if sys in ("absolute_monarchy", "constitutional_monarchy"):
        if rng.random() < 0.5:
            nation.political_system = "republic"
        else:
            nation.suppressed = True
    elif sys == "republic":
        if rng.random() < 0.3:
            nation.political_system = "socialist_republic"
        else:
            rf.influence *= cfg.UPRISING_RF_DECLINE

    # 起义后躁动部分释放，避免连环触发
    rf.agitation = min(1.0, rf.agitation * 0.5)
    return True

