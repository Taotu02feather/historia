"""simulate.py — 年度推演主循环（单国 / 多国）。"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from .config import Config
from .models import Nation, PROFESSIONS, IG_IDS
from .names import generate_nation_names
from .nation import (create_nation, total_pop, profession_sizes,
                     total_factories, total_farms, total_mines, mean_awareness)
from .interest_group import init_interest_groups, update_influence, apply_government
from .goals import GOALS
from . import economy, pop, politics, ai, events
from .events import EventTracker


@dataclass
class SimResult:
    nations: List[Nation] = field(default_factory=list)
    snapshots: List[dict] = field(default_factory=list)
    events: List[dict] = field(default_factory=list)
    params: dict = field(default_factory=dict)


def _make_snapshot(n: Nation, year: int, event: str) -> dict:
    sizes = profession_sizes(n)
    ig_inf = {ig_id: ig.influence for ig_id, ig in n.interest_groups.items()}
    row = {
        "year": year,
        "country_id": n.id,
        "country_name": n.name,
        "goal": n.goal,
        "treasury": round(n.treasury, 2),
        "tax_rate": round(n.tax_rate, 4),
        "stability": round(n.stability, 4),
        "reform_level": round(n.reform_level, 4),
        "reform_pressure": round(n.reform_pressure, 4),
        "total_pop": round(total_pop(n), 1),
    }
    for prof in PROFESSIONS:
        row[f"pop_{prof}"] = round(sizes.get(prof, 0.0), 1)
    for ig_id in IG_IDS:
        row[f"ig_{ig_id}"] = round(ig_inf.get(ig_id, 0.0), 4)
    row.update({
        "total_factories": total_factories(n),
        "total_farms": total_farms(n),
        "total_mines": total_mines(n),
        "avg_awareness": round(mean_awareness(n), 4),
        "gdp": round(n.gdp, 2),
        "political_system": n.political_system,
        "event": event,
    })
    return row


def _run_years(nations: List[Nation], world, rng: np.random.Generator,
               cfg: Config):
    """执行 years 年主循环，返回 (snapshots, all_events)。"""
    tracker = EventTracker()
    snapshots: List[dict] = []
    all_events: List[dict] = []

    for year in range(1, cfg.years + 1):
        # 1. 经济结算
        economy.settle(world, nations, cfg, GOALS)
        # 技术扩散（多国）
        if world is not None:
            world.diffuse_tech(nations, cfg, GOALS)
        # 2. POP 变化
        pop.settle(nations, cfg, GOALS)
        # 3. 政治结算
        politics.settle(nations, cfg, GOALS)
        # 农民起义（政治后、AI 前）
        uprising_ids = set()
        for n in nations:
            if politics.check_peasant_uprising(n, rng, cfg):
                uprising_ids.add(n.id)
        # 4. AI 决策
        ai.decide(nations, cfg, GOALS, world)
        # 事件检测
        new_events = events.detect(nations, cfg, tracker, year)
        for n in nations:
            if n.id in uprising_ids:
                new_events.append({
                    "year": year, "country_id": n.id, "country_name": n.name,
                    "event": "peasant_uprising", "detail": "",
                })
        all_events.extend(new_events)

        year_events: Dict[int, List[str]] = defaultdict(list)
        for e in new_events:
            year_events[e["country_id"]].append(e["event"])
        for n in nations:
            snapshots.append(_make_snapshot(
                n, year, ";".join(year_events.get(n.id, []))))

    return snapshots, all_events


def _init_nations(nations: List[Nation], cfg: Config) -> None:
    for n in nations:
        init_interest_groups(n)
        update_influence(n, cfg)
        apply_government(n, cfg)


def run_sim(cfg: Config) -> SimResult:
    """单国模拟。"""
    rng = np.random.default_rng(cfg.seed)
    name_rng, nation_rng, sim_rng = rng.spawn(3)
    name = generate_nation_names(name_rng, 1)[0]
    nation = create_nation(0, name, cfg, nation_rng, 0, cfg.provinces)
    nation.goal = cfg.goal
    nations = [nation]
    _init_nations(nations, cfg)

    snapshots, all_events = _run_years(nations, None, sim_rng, cfg)
    return SimResult(
        nations=nations, snapshots=snapshots, events=all_events,
        params={"mode": "sim", "goal": cfg.goal, "years": cfg.years,
                "provinces": cfg.provinces, "seed": cfg.seed,
                "tax_rate": cfg.tax_rate, "treasury": cfg.treasury,
                "initial_pop": cfg.initial_pop, "initial_tech": cfg.initial_tech},
    )


def run_world(cfg: Config, goals: Optional[List[str]] = None) -> SimResult:
    """多国模拟。goals 为每国目标 key 列表（长度 = nations）。"""
    rng = np.random.default_rng(cfg.seed)
    name_rng, nation_rng, goal_rng, sim_rng = rng.spawn(4)
    names = generate_nation_names(name_rng, cfg.nations)

    if goals is None:
        goals = _assign_goals(cfg, goal_rng)
    nations: List[Nation] = []
    for i in range(cfg.nations):
        nation = create_nation(i, names[i], cfg, nation_rng,
                               i * 10000, cfg.provinces_per_nation)
        nation.goal = goals[i]
        nations.append(nation)
    _init_nations(nations, cfg)

    from .world import World
    world = World(nations, cfg, sim_rng)
    snapshots, all_events = _run_years(nations, world, sim_rng, cfg)
    return SimResult(
        nations=nations, snapshots=snapshots, events=all_events,
        params={"mode": "world", "nations": cfg.nations, "years": cfg.years,
                "provinces_per_nation": cfg.provinces_per_nation,
                "seed": cfg.seed, "goal_mode": cfg.goal_mode,
                "goals": goals, "initial_tech": cfg.initial_tech},
    )


def _assign_goals(cfg: Config, rng: np.random.Generator) -> List[str]:
    """按 goal_mode 分配目标。"""
    keys = list(GOALS.keys())
    if cfg.goal_mode == "explicit" and cfg.goals:
        assert len(cfg.goals) == cfg.nations, \
            f"--goals 数量({len(cfg.goals)}) 必须等于 --nations({cfg.nations})"
        return list(cfg.goals)
    if cfg.goal_mode == "cycle":
        return [keys[i % len(keys)] for i in range(cfg.nations)]
    # random（默认）
    return [keys[int(rng.integers(0, len(keys)))] for _ in range(cfg.nations)]

