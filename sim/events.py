"""events.py — 关键事件检测（只读，不影响模拟状态）。"""

from collections import defaultdict
from typing import Dict, List, Optional

from .config import Config
from .models import Nation
from .nation import total_pop, worker_awareness


class EventTracker:
    """跨年状态：已触发事件、峰值、制度/执政快照。"""

    def __init__(self) -> None:
        self.fired = defaultdict(set)     # nation_id -> set(一次性事件 key)
        self.rf_peak: Dict[int, float] = {}
        self.tech_leader: Optional[int] = None
        self.last_system: Dict[int, str] = {}
        self.last_gov: Dict[int, frozenset] = {}
        self.neg_years: Dict[int, int] = {}


def _once(tracker: EventTracker, nid: int, key: str) -> bool:
    """一次性事件：未触发过则记录并返回 True。"""
    if key in tracker.fired[nid]:
        return False
    tracker.fired[nid].add(key)
    return True


def _event(n: Nation, year: int, key: str, detail: str = "") -> dict:
    return {"year": year, "country_id": n.id, "country_name": n.name,
            "event": key, "detail": detail}


def _avg_prof_satisfaction(n: Nation, prof: str) -> float:
    total = 0.0
    sat = 0.0
    for prov in n.provinces:
        for p in prov.pops:
            if p.profession == prof:
                total += p.size
                sat += p.size * p.satisfaction
    return sat / total if total > 0 else 0.5


def _detect_nation(n: Nation, cfg: Config, tracker: EventTracker,
                   year: int, events: List[dict]) -> None:
    tp = total_pop(n)
    if tp <= 0:
        return
    igs = n.interest_groups
    prof: Dict[str, float] = {}
    for prov in n.provinces:
        for p in prov.pops:
            prof[p.profession] = prof.get(p.profession, 0.0) + p.size

    # --- 阶级流动事件 ---
    if prof.get("clerks", 0.0) > 0 and _once(tracker, n.id, "first_clerk_appears"):
        events.append(_event(n, year, "first_clerk_appears",
                             f"clerks={prof['clerks']:.1f}"))
    worker_share = (prof.get("laborers", 0.0) + prof.get("clerks", 0.0)) / tp
    if worker_share > cfg.CLASS_MOBILITY_SHARE \
            and _once(tracker, n.id, "class_mobility_start"):
        events.append(_event(n, year, "class_mobility_start",
                             f"工人+职员占比={worker_share:.2f}"))
    lab_sat = _avg_prof_satisfaction(n, "laborers")
    if (lab_sat < cfg.LABOR_CRISIS_SAT and n.reform_pressure > cfg.LABOR_CRISIS_PRESS
            and _once(tracker, n.id, "labor_crisis")):
        events.append(_event(n, year, "labor_crisis", f"劳工满意度={lab_sat:.2f}"))

    # --- 利益集团事件 ---
    for ig in igs.values():
        if ig.influence > cfg.IG_FORMED_THRESH \
                and _once(tracker, n.id, f"ig_formed:{ig.id}"):
            events.append(_event(n, year, "ig_formed", f"{ig.name} 影响力>0.01"))
        if ig.influence > cfg.IG_DOMINANT \
                and _once(tracker, n.id, f"ig_dominant:{ig.id}"):
            events.append(_event(n, year, "ig_dominant",
                                 f"{ig.name} 影响力={ig.influence:.2f}"))
        if ig.agitation > cfg.AGITATE_CRISIS:
            events.append(_event(n, year, "ig_agitation_crisis",
                                 f"{ig.name} 躁动={ig.agitation:.2f}"))
    gov = frozenset(ig.id for ig in igs.values() if ig.in_government)
    if n.id in tracker.last_gov and gov != tracker.last_gov[n.id]:
        events.append(_event(n, year, "ig_government_change",
                             f"{sorted(tracker.last_gov[n.id])} -> {sorted(gov)}"))
    tracker.last_gov[n.id] = gov

    # --- 乡村民众事件 ---
    rf = igs.get("rural_folk")
    if rf is not None:
        if rf.influence > cfg.IG_DOMINANT \
                and _once(tracker, n.id, "rural_folk_dominant"):
            events.append(_event(n, year, "rural_folk_dominant",
                                 f"影响力={rf.influence:.2f}"))
        peak = tracker.rf_peak.get(n.id, rf.influence)
        tracker.rf_peak[n.id] = max(peak, rf.influence)
        if peak > 0.1 and rf.influence < peak * 0.5 \
                and _once(tracker, n.id, "rural_folk_decline"):
            events.append(_event(n, year, "rural_folk_decline",
                                 f"{peak:.2f} -> {rf.influence:.2f}"))
        tu = igs.get("trade_unions")
        if tu is not None:
            if (_avg_prof_satisfaction(n, "peasants") < cfg.ALLIANCE_SAT
                    and _avg_prof_satisfaction(n, "laborers") < cfg.ALLIANCE_SAT
                    and rf.influence > cfg.ALLIANCE_INFLUENCE
                    and tu.influence > cfg.ALLIANCE_INFLUENCE
                    and _once(tracker, n.id, "rural_urban_alliance")):
                events.append(_event(n, year, "rural_urban_alliance",
                                     "乡村民众与工会结盟"))

    # --- 制度事件 ---
    if n.political_system in ("republic", "democracy") \
            and _once(tracker, n.id, "first_election"):
        events.append(_event(n, year, "first_election", f"进入 {n.political_system}"))
    tu = igs.get("trade_unions")
    if tu is not None and (tu.in_government or tu.influence > cfg.TU_LEGAL_INFLUENCE) \
            and _once(tracker, n.id, "trade_unions_legalized"):
        events.append(_event(n, year, "trade_unions_legalized",
                             f"影响力={tu.influence:.2f}"))
    if n.political_system == "theocracy" \
            and _once(tracker, n.id, "theocracy_established"):
        events.append(_event(n, year, "theocracy_established", ""))

    # --- 原有检测 ---
    if n.gdp > 0 and n.indu / n.gdp >= cfg.INDUSTRIAL_REVOLUTION_SHARE \
            and _once(tracker, n.id, "industrial_revolution"):
        events.append(_event(n, year, "industrial_revolution",
                             f"工业占比={n.indu/n.gdp:.2f}"))
    if worker_awareness(n) >= cfg.WORKER_AWAKENING_THRESH \
            and _once(tracker, n.id, "worker_awakening"):
        events.append(_event(n, year, "worker_awakening",
                             f"劳工意识={worker_awareness(n):.2f}"))
    if n.reform_pressure > cfg.REFORM_THRESH \
            and _once(tracker, n.id, "reform_movement"):
        events.append(_event(n, year, "reform_movement",
                             f"压力={n.reform_pressure:.2f}"))
    if n.id in tracker.last_system and tracker.last_system[n.id] != n.political_system:
        events.append(_event(n, year, "system_change",
                             f"{tracker.last_system[n.id]} -> {n.political_system}"))
    tracker.last_system[n.id] = n.political_system
    if n.stability < cfg.REVOLT_THRESH and _once(tracker, n.id, "revolution"):
        events.append(_event(n, year, "revolution", f"稳定度={n.stability:.2f}"))

    # --- 经济危机（连续负国库） ---
    if n.treasury < 0:
        tracker.neg_years[n.id] = tracker.neg_years.get(n.id, 0) + 1
    else:
        tracker.neg_years[n.id] = 0
    if tracker.neg_years[n.id] >= cfg.ECONOMIC_CRISIS_YEARS \
            and _once(tracker, n.id, "economic_crisis"):
        events.append(_event(n, year, "economic_crisis",
                             f"国库连续 {tracker.neg_years[n.id]} 年为负"))


def detect(nations: List[Nation], cfg: Config, tracker: EventTracker,
           year: int) -> List[dict]:
    """检测所有国家本年事件，并返回新增事件列表。"""
    events: List[dict] = []
    for n in nations:
        _detect_nation(n, cfg, tracker, year, events)
    # 全球技术领袖易主
    if len(nations) > 1:
        leader = max(nations, key=lambda x: x.tech_level).id
        if tracker.tech_leader is not None and leader != tracker.tech_leader:
            n = next(x for x in nations if x.id == leader)
            events.append(_event(n, year, "tech_leader_change",
                                 f"tech={n.tech_level:.2f}"))
        tracker.tech_leader = leader
    return events


