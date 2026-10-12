"""economy.py — 经济结算（年度第 1 步）。

产出 → 世界市场价格 → 市场收入 → 税收 → 国库。
"""

from typing import Dict, List, Optional

from .config import Config
from .models import Nation
from .province import agri_output, mine_output, factory_output


def compute_outputs(nation: Nation, cfg: Config):
    """计算全国（agri, mine, indu）产出，产值口径、未乘价格。"""
    agri = 0.0
    mine = 0.0
    for prov in nation.provinces:
        agri += agri_output(prov, nation.tech_level, cfg)
        mine += mine_output(prov, nation.tech_level, cfg)

    # 煤供给对工业的加成（国级）：煤供给 = 矿业产出，煤需求 = 工厂容量
    coal_need = sum(p.factories for p in nation.provinces) * cfg.FACT_CAP
    coal_factor = 1.0 + cfg.COAL_FACTOR * min(mine / max(coal_need, 1e-9), 1.0)

    indu = 0.0
    for prov in nation.provinces:
        indu += factory_output(prov, nation.tech_level, coal_factor, cfg)
    return agri, mine, indu


def settle(world, nations: List[Nation], cfg: Config,
           goal_map: Optional[Dict] = None) -> None:
    """1. 经济结算。

    world: 多国 World 对象（含 compute_prices），单国时为 None。
    goal_map: {goal_key: GoalParams}，用于军费/福利支出比例。
    """
    goal_map = goal_map or {}

    # 各国产出
    outputs: Dict[int, tuple] = {}
    for n in nations:
        outputs[n.id] = compute_outputs(n, cfg)

    # 世界市场价格（单国则用基础价）
    if world is not None:
        prices = world.compute_prices(nations, outputs, cfg)
    else:
        prices = {
            "farm": cfg.PRICE_FARM,
            "mine": cfg.PRICE_MINE,
            "factory": cfg.PRICE_FACTORY,
        }

    for n in nations:
        agri, mine, indu = outputs[n.id]
        n.gdp = agri + mine + indu  # 产值口径 GDP
        market_income = (agri * prices["farm"]
                         + mine * prices["mine"]
                         + indu * prices["factory"])

        goal = goal_map.get(n.goal)
        mil = goal.military_spending if goal else 0.0
        wel = goal.welfare_spending if goal else 0.0

        # 税收效率：bureaucrats 越多越高
        tp = sum(p.size for prov in n.provinces for p in prov.pops)
        bur = sum(p.size for prov in n.provinces for p in prov.pops
                  if p.profession == "bureaucrats")
        tax_eff = min(1.0, 0.5 + (bur / tp * 10.0 if tp > 0 else 0.5))

        tax_income = market_income * n.tax_rate * tax_eff
        military_cost = mil * n.gdp
        welfare_cost = wel * n.gdp
        admin_cost = cfg.ADMIN_COEF * tp

        n.treasury += tax_income - military_cost - welfare_cost - admin_cost
        n.gdp_history.append(n.gdp)
