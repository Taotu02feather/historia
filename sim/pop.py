"""pop.py — POP 变化（年度第 2 步）：财富分配、满意度、人口增长、阶级流动、军人招募。"""

import math
from typing import Dict, List, Optional

from .config import Config
from .models import Nation
from .province import get_pop
from .nation import total_pop, pop_by_profession, profession_sizes


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _distribute_wealth(nation: Nation, cfg: Config) -> None:
    """按职业分配当年产出（地租从农民收入扣，转入贵族，不额外生成产出）。"""
    agri, mine, indu = nation.agri, nation.mine, nation.indu
    rent = agri * nation.rent_rate

    # 全国各职业总收入
    incomes = {
        "peasants": agri - rent,
        "laborers": mine + indu * 0.40,
        "clerks": indu * 0.10,
        "capitalists": indu * 0.30,
        "aristocrats": rent,
        "servicemen": 0.0,
        "clergymen": 0.0,
        "bureaucrats": 0.0,
    }
    sizes = profession_sizes(nation)

    for prov in nation.provinces:
        for p in prov.pops:
            inc = incomes.get(p.profession, 0.0)
            n_prof = sizes.get(p.profession, 0.0)
            if p.profession in ("servicemen", "clergymen", "bureaucrats"):
                # 非生产职业：财富向参照水平缓慢靠拢
                ref = cfg.REF_WEALTH.get(p.profession, p.wealth)
                p.wealth += 0.1 * (ref - p.wealth)
            else:
                per_capita = inc / max(n_prof, 1e-9)
                # 平滑更新，避免单年剧烈跳变
                p.wealth = 0.7 * p.wealth + 0.3 * per_capita
            p.wealth = max(p.wealth, 1e-3)

    # 资本家负利润判断（人均利润下降则累计）
    cap_size = sizes.get("capitalists", 0.0)
    if cap_size > 0:
        cap_wealth = incomes["capitalists"] / cap_size
        last = getattr(nation, "_last_cap_wealth", cap_wealth)
        if cap_wealth < last - 1e-6:
            nation.neg_profit_years += 1
        else:
            nation.neg_profit_years = 0
        nation._last_cap_wealth = cap_wealth


def _update_satisfaction(nation: Nation, cfg: Config, goal_map: Dict) -> None:
    """满意度（§3.2b）。"""
    goal = goal_map.get(nation.goal)
    wel = goal.welfare_spending if goal else 0.0
    church_inf = nation.interest_groups["church"].influence \
        if "church" in nation.interest_groups else 0.0

    for prov in nation.provinces:
        for p in prov.pops:
            ref = cfg.REF_WEALTH.get(p.profession, p.wealth)
            sat = (cfg.SAT_BASE
                   + cfg.SAT_WEALTH * (math.log(max(p.wealth, 1e-6))
                                       - math.log(max(ref, 1e-6)))
                   - cfg.SAT_TAX * nation.tax_rate
                   + cfg.SAT_WELFARE * wel
                   + cfg.SAT_CLERGY * church_inf * (1 - p.political_awareness))
            p.satisfaction = _clamp(sat, 0.0, 1.0)


def _grow_population(nation: Nation, cfg: Config) -> None:
    """人口自然增长。"""
    for prov in nation.provinces:
        for p in prov.pops:
            growth = _clamp(cfg.GROWTH_BASE * (0.5 + p.satisfaction),
                            cfg.GROWTH_MIN, cfg.GROWTH_MAX)
            p.size *= (1.0 + growth)


def _recruit_servicemen(nation: Nation, cfg: Config, goal_map: Dict) -> None:
    """军人招募（§Q2）：随军事开支从 peasants 招募，约束上下限。"""
    goal = goal_map.get(nation.goal)
    mil = goal.military_spending if goal else 0.0
    tp = total_pop(nation)
    if tp <= 0:
        return
    ratio = pop_by_profession(nation, "servicemen") / tp
    # 目标比例：下限 + 军费推动（越接近上限）
    target = min(cfg.SERVICEMEN_MIN_RATIO + mil * 4.0 * cfg.SERVICEMEN_CAP_RATIO,
                 cfg.SERVICEMEN_CAP_RATIO)
    if ratio >= target:
        return
    recruit = min(cfg.SERVICEMEN_RECRUIT * tp, (target - ratio) * tp)
    peasant_total = pop_by_profession(nation, "peasants")
    if peasant_total <= 0:
        return
    for prov in nation.provinces:
        p = get_pop(prov, "peasants")
        if p is None:
            continue
        amt = recruit * (p.size / peasant_total)
        _migrate(prov, "peasants", "servicemen", amt)


def _up_modifier(nation: Nation, cfg: Config) -> float:
    """向上流动的税率/技术修正。"""
    return max(0.0, (1.0 - cfg.UP_TAX_PENALTY * nation.tax_rate)
               * (0.5 + 0.5 * nation.tech_level))


def _recession(nation: Nation) -> bool:
    """经济衰退：最近一年 GDP 下降。"""
    h = nation.gdp_history
    return len(h) >= 2 and h[-1] < h[-2]


def _migrate(prov, src: str, dst: str, amount: float) -> None:
    """人口按比例迁移，wealth 按人均随迁（总财富守恒）。"""
    amount = max(0.0, amount)
    s = get_pop(prov, src)
    d = get_pop(prov, dst)
    if s is None or d is None or amount <= 0 or s.size <= 0:
        return
    amount = min(amount, s.size)
    moved_wealth = amount * s.wealth
    s.size -= amount
    new_d = d.size + amount
    d.wealth = (d.size * d.wealth + moved_wealth) / new_d if new_d > 0 else d.wealth
    d.size = new_d


def settle(nations: List[Nation], cfg: Config,
           goal_map: Optional[Dict] = None) -> None:
    """2. POP 变化。"""
    goal_map = goal_map or {}
    for n in nations:
        _distribute_wealth(n, cfg)
        _update_satisfaction(n, cfg, goal_map)
        _grow_population(n, cfg)
        update_pop_promotion(n, cfg)
        _recruit_servicemen(n, cfg, goal_map)


def update_pop_promotion(nation: Nation, cfg: Config) -> None:
    """阶级流动（§9）。每省独立，不跨省。"""
    tech = nation.tech_level
    build_ref = cfg.PROV_BUILDING_REF
    clerk_share = pop_by_profession(nation, "clerks") / max(total_pop(nation), 1e-9)
    education = min(1.0, nation.reform_level + clerk_share * 2.0)

    for prov in nation.provinces:
        peasants = (get_pop(prov, "peasants").size
                    if get_pop(prov, "peasants") else 0.0)
        laborers = (get_pop(prov, "laborers").size
                    if get_pop(prov, "laborers") else 0.0)
        clerks = (get_pop(prov, "clerks").size
                  if get_pop(prov, "clerks") else 0.0)
        capitalists = (get_pop(prov, "capitalists").size
                       if get_pop(prov, "capitalists") else 0.0)
        has_ind = prov.factories > 0 or prov.mines > 0

        # 1) peasants → laborers
        if has_ind and peasants > 0:
            trig = min(1.0, (prov.factories + prov.mines) / build_ref) \
                * (1.0 - 0.4 * prov.land_quality)
            _migrate(prov, "peasants", "laborers",
                     peasants * min(cfg.MAX_P2L * trig * _up_modifier(nation, cfg),
                                    cfg.MIG_CAP))

        # 2) laborers → clerks
        if tech > 0.3 and prov.factories > 0 and laborers > 0:
            trig = min(1.0, (tech - 0.3) / 0.7) * min(1.0, prov.factories / build_ref)
            _migrate(prov, "laborers", "clerks",
                     laborers * min(cfg.MAX_L2C * trig * _up_modifier(nation, cfg),
                                    cfg.MIG_CAP))

        # 3) peasants → clerks
        if tech > 0.5 and peasants > 0:
            trig = min(1.0, (tech - 0.5) / 0.5) * education
            _migrate(prov, "peasants", "clerks",
                     peasants * min(cfg.MAX_P2C * trig * _up_modifier(nation, cfg),
                                    cfg.MIG_CAP))

        # 4) laborers / clerks → capitalists（财富达阈值）
        for src in ("laborers", "clerks"):
            p = get_pop(prov, src)
            if p is not None and p.size > 0 and p.wealth >= cfg.WEALTH_CAPITALIST:
                _migrate(prov, src, "capitalists", p.size * cfg.MAX_2CAP)

        # 5) laborers → peasants（不满）
        lab = get_pop(prov, "laborers")
        if lab is not None and lab.size > 0 and lab.satisfaction < 0.2:
            trig = min(1.0, (0.2 - lab.satisfaction) / 0.2)
            _migrate(prov, "laborers", "peasants",
                     lab.size * min(cfg.MAX_L2P * trig, cfg.MIG_CAP))

        # 6) clerks → laborers（经济衰退）
        if _recession(nation) and clerks > 0:
            _migrate(prov, "clerks", "laborers",
                     clerks * min(cfg.MAX_C2L, cfg.MIG_CAP))

        # 7) capitalists → clerks（连续负利润）
        if nation.neg_profit_years >= cfg.NEG_PROFIT_YEARS and capitalists > 0:
            _migrate(prov, "capitalists", "clerks",
                     capitalists * cfg.MAX_CAP2C)

