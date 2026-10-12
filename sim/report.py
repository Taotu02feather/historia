"""report.py — CSV / TXT 报告生成。"""

import os
from datetime import datetime
from typing import List

import pandas as pd

from .config import Config
from .models import Nation, PROFESSIONS
from .nation import profession_sizes, total_pop
from .goals import GOALS, GoalParams


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def build_filename(cfg: Config, ts: str) -> str:
    """输出文件名（含关键参数，避免覆盖）。"""
    mode = "world" if cfg.nations > 1 else "sim"
    if mode == "sim":
        return f"sim_{cfg.goal}_y{cfg.years}_s{cfg.seed}_{ts}"
    return f"world_n{cfg.nations}_y{cfg.years}_s{cfg.seed}_{ts}"


def _final_row(n: Nation) -> dict:
    sizes = profession_sizes(n)
    ig_inf = {ig_id: ig.influence for ig_id, ig in n.interest_groups.items()}
    top = sorted(ig_inf, key=ig_inf.get, reverse=True)
    row = {
        "country_id": n.id, "country_name": n.name, "goal": n.goal,
        "treasury": round(n.treasury, 2), "tax_rate": round(n.tax_rate, 4),
        "stability": round(n.stability, 4), "reform_level": round(n.reform_level, 4),
        "reform_pressure": round(n.reform_pressure, 4),
        "total_pop": round(total_pop(n), 1),
        "gdp": round(n.gdp, 2), "tech_level": round(n.tech_level, 4),
        "political_system": n.political_system,
        "max_ig": top[0] if top else "",
        "max_ig_influence": round(ig_inf[top[0]], 4) if top else 0.0,
        "second_ig": top[1] if len(top) > 1 else "",
        "second_ig_influence": round(ig_inf[top[1]], 4) if len(top) > 1 else 0.0,
    }
    for prof in PROFESSIONS:
        row[f"pop_{prof}"] = round(sizes.get(prof, 0.0), 1)
    return row


def write_report(result, cfg: Config, outdir: str = "output") -> List[str]:
    """生成 CSV 与 TXT，返回生成的文件路径列表。"""
    ts = _timestamp()
    base = build_filename(cfg, ts)
    os.makedirs(outdir, exist_ok=True)

    yearly_path = os.path.join(outdir, base + ".csv")
    pd.DataFrame(result.snapshots).to_csv(yearly_path, index=False)

    events_path = os.path.join(outdir, base + "_events.csv")
    pd.DataFrame(result.events).to_csv(events_path, index=False)

    final_path = os.path.join(outdir, base + "_final.csv")
    pd.DataFrame([_final_row(n) for n in result.nations]).to_csv(
        final_path, index=False)

    txt_path = os.path.join(outdir, base + ".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(_build_txt(result, cfg))

    return [yearly_path, events_path, final_path, txt_path]


def _build_txt(result, cfg: Config) -> str:
    lines: List[str] = []
    p = result.params
    lines.append("=" * 72)
    lines.append("historia 运行报告")
    lines.append("=" * 72)
    lines.append("")
    lines.append("[参数头]")
    for k, v in p.items():
        lines.append(f"  {k} = {v}")
    lines.append(f"  时间戳 = {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 最终状态（按 GDP 排序）
    lines.append("[最终状态]（按 GDP 排序）")
    lines.append(f"  {'国家':<14}{'目标':<14}{'GDP':>10}  "
                 f"{'最大IG':<20}{'第二IG':<20}{'制度':<24}")
    nations_sorted = sorted(result.nations, key=lambda n: n.gdp, reverse=True)
    for n in nations_sorted:
        ig_inf = {ig.id: ig.influence for ig in n.interest_groups.values()}
        top = sorted(ig_inf, key=ig_inf.get, reverse=True)
        g = GOALS.get(n.goal)
        gname = g.name if g else n.goal
        max_ig = f"{top[0]}({ig_inf[top[0]]:.2f})" if top else "-"
        sec_ig = f"{top[1]}({ig_inf[top[1]]:.2f})" if len(top) > 1 else "-"
        lines.append(f"  {n.name:<14}{gname:<14}{n.gdp:>10.1f}  "
                     f"{max_ig:<20}{sec_ig:<20}{n.political_system:<24}")
    lines.append("")

    # 关键事件时间线
    lines.append("[关键事件时间线]")
    if result.events:
        for e in sorted(result.events, key=lambda x: (x["year"], x["country_id"])):
            lines.append(f"  第{e['year']:>4}年 | {e['country_name']:<14} "
                         f"| {e['event']:<24} | {e.get('detail','')}")
    else:
        lines.append("  （无事件）")
    lines.append("")

    # 变化对比
    lines.append("[变化对比]（起始 → 结束）")
    for n in result.nations:
        rows = [s for s in result.snapshots if s["country_id"] == n.id]
        if not rows:
            continue
        first, last = rows[0], rows[-1]
        def _share(r, profs):
            num = sum(r.get(f"pop_{x}", 0.0) for x in profs)
            return num / r["total_pop"] if r["total_pop"] else 0.0
        peasant0 = _share(first, ["peasants"])
        peasant1 = _share(last, ["peasants"])
        worker0 = _share(first, ["laborers", "clerks"])
        worker1 = _share(last, ["laborers", "clerks"])
        lines.append(f"  {n.name}: 农民占比 {peasant0:.2f}→{peasant1:.2f} | "
                     f"工人+职员 {worker0:.2f}→{worker1:.2f} | "
                     f"GDP {first['gdp']:.0f}→{last['gdp']:.0f} | "
                     f"制度 {first['political_system']}→{last['political_system']}")
    lines.append("")

    # 单国：IG 演变
    if len(result.nations) == 1:
        lines.append("[利益集团影响力演变]")
        n = result.nations[0]
        rows = [s for s in result.snapshots if s["country_id"] == n.id]
        if rows:
            first, last = rows[0], rows[-1]
            lines.append(f"  {'IG':<16}{first['year']:>6}{last['year']:>8}  {'变化':<4}")
            for ig_id, ig in n.interest_groups.items():
                a = first.get(f"ig_{ig_id}", 0.0)
                b = last.get(f"ig_{ig_id}", 0.0)
                arrow = _arrow(b - a)
                lines.append(f"  {ig.name:<16}{a:>8.2f}{b:>8.2f}  {arrow}")
    lines.append("")
    lines.append("=" * 72)
    return "\n".join(lines)


def _arrow(delta: float) -> str:
    if delta > 0.10:
        return "↑↑"
    if delta > 0.03:
        return "↑"
    if delta < -0.10:
        return "↓↓"
    if delta < -0.03:
        return "↓"
    return "-"

