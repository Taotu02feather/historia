"""nation.py — 国家创建与初始化、国级聚合。"""

from typing import Dict, List

import numpy as np

from .config import Config
from .models import (Nation, Province, Pop, PROFESSIONS, STRATA)
from .names import province_name

# 初始人口分布（每省比例，和 = 1）
INITIAL_POP_DIST: Dict[str, float] = {
    "peasants": 0.70, "laborers": 0.05, "servicemen": 0.05,
    "clergymen": 0.10, "bureaucrats": 0.05, "aristocrats": 0.03,
    "capitalists": 0.02, "clerks": 0.00,
}

# 初始人均财富
INITIAL_WEALTH: Dict[str, float] = {
    "peasants": 10.0, "laborers": 12.0, "servicemen": 11.0,
    "clerks": 15.0, "clergymen": 13.0, "bureaucrats": 14.0,
    "aristocrats": 40.0, "capitalists": 50.0,
}

# 初始政治意识
INITIAL_AWARENESS: Dict[str, float] = {
    "peasants": 0.05, "laborers": 0.15, "servicemen": 0.05,
    "clerks": 0.25, "clergymen": 0.10, "bureaucrats": 0.20,
    "aristocrats": 0.30, "capitalists": 0.40,
}


def make_pops(cfg: Config, total_pop: int) -> List[Pop]:
    """按初始分布生成某省的 8 个 Pop。"""
    pops: List[Pop] = []
    for prof in PROFESSIONS:
        size = total_pop * INITIAL_POP_DIST.get(prof, 0.0)
        pops.append(Pop(
            profession=prof,
            strata=STRATA[prof],
            size=size,
            wealth=INITIAL_WEALTH[prof],
            political_awareness=INITIAL_AWARENESS[prof],
        ))
    return pops


def create_nation(nid: int, name: str, cfg: Config, rng: np.random.Generator,
                  start_province_id: int, n_provinces: int) -> Nation:
    """创建一个国家（省份 + 初始人口）。"""
    provinces: List[Province] = []
    for i in range(n_provinces):
        land_quality = float(rng.uniform(0.3, 1.0))
        coal_deposit = float(rng.uniform(0.0, 1.0))
        # 农业社会起点：农场为主，少量矿场/工厂
        farms = int(rng.integers(8, 15))
        mines = int(rng.integers(0, 3))
        factories = int(rng.integers(0, 2))
        provinces.append(Province(
            id=start_province_id + i,
            name=province_name(name, i + 1),
            land_quality=land_quality,
            coal_deposit=coal_deposit,
            factories=factories,
            farms=farms,
            mines=mines,
            pops=make_pops(cfg, cfg.initial_pop),
        ))
    return Nation(
        id=nid, name=name, provinces=provinces,
        treasury=cfg.treasury, tax_rate=cfg.tax_rate,
        goal=cfg.goal, tech_level=cfg.initial_tech,
        rent_rate=cfg.RENT_RATE,
    )


# ============ 国级聚合工具 ============

def total_pop(nation: Nation) -> float:
    return sum(p.size for prov in nation.provinces for p in prov.pops)


def pop_by_profession(nation: Nation, profession: str) -> float:
    return sum(p.size for prov in nation.provinces for p in prov.pops
               if p.profession == profession)


def profession_sizes(nation: Nation) -> Dict[str, float]:
    result: Dict[str, float] = {prof: 0.0 for prof in PROFESSIONS}
    for prov in nation.provinces:
        for p in prov.pops:
            result[p.profession] += p.size
    return result


def total_factories(nation: Nation) -> int:
    return sum(p.factories for p in nation.provinces)


def total_farms(nation: Nation) -> int:
    return sum(p.farms for p in nation.provinces)


def total_mines(nation: Nation) -> int:
    return sum(p.mines for p in nation.provinces)


def mean_satisfaction(nation: Nation) -> float:
    total = total_pop(nation)
    if total <= 0:
        return 0.5
    s = sum(p.size * p.satisfaction for prov in nation.provinces for p in prov.pops)
    return s / total


def mean_awareness(nation: Nation) -> float:
    total = total_pop(nation)
    if total <= 0:
        return 0.0
    s = sum(p.size * p.political_awareness
            for prov in nation.provinces for p in prov.pops)
    return s / total


def worker_awareness(nation: Nation) -> float:
    """laborers 职业的平均政治意识。"""
    total = 0.0
    aware = 0.0
    for prov in nation.provinces:
        for p in prov.pops:
            if p.profession == "laborers":
                total += p.size
                aware += p.size * p.political_awareness
    return aware / total if total > 0 else 0.0
