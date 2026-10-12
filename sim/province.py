"""province.py — 省份级产出与建造。"""

from typing import Optional

from .config import Config
from .models import Province, Pop


def get_pop(province: Province, profession: str) -> Optional[Pop]:
    """按职业取该省的 Pop（无则返回 None）。"""
    for p in province.pops:
        if p.profession == profession:
            return p
    return None


def labor_factor(workers: float, capacity: float) -> float:
    """劳动力充足度，范围 0.3~1.0。capacity<=0 时按最低算。"""
    if capacity <= 0:
        return 0.3
    return 0.3 + 0.7 * min(workers / capacity, 1.0)


def agri_output(province: Province, tech_level: float, cfg: Config) -> float:
    """农业产出。peasants 是主要劳动力。"""
    peasant = get_pop(province, "peasants")
    p = peasant.size if peasant else 0.0
    labor = labor_factor(p, province.farms * cfg.FARM_CAP)
    return province.land_quality * province.farms * cfg.AGR_BASE * labor


def mine_output(province: Province, tech_level: float, cfg: Config) -> float:
    """矿业产出。laborers 是劳动力。"""
    laborer = get_pop(province, "laborers")
    w = laborer.size if laborer else 0.0
    labor = labor_factor(w, province.mines * cfg.MINE_CAP)
    return province.coal_deposit * province.mines * cfg.MINE_BASE \
        * (1 + 0.08 * tech_level) * labor


def factory_output(province: Province, tech_level: float, coal_factor: float,
                   cfg: Config) -> float:
    """工业产出。laborers + clerks（clerks 效率 1.5 倍）。"""
    laborer = get_pop(province, "laborers")
    clerk = get_pop(province, "clerks")
    w = (laborer.size if laborer else 0.0) \
        + cfg.CLERK_EFF * (clerk.size if clerk else 0.0)
    labor = labor_factor(w, province.factories * cfg.FACT_CAP)
    return province.factories * cfg.IND_BASE * (1 + cfg.TECH_GAIN * tech_level) \
        * labor * coal_factor
