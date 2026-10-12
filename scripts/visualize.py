"""
从 output/ 里的 CSV 画图，输出到 output/figures/。
用法：python scripts/visualize.py
"""
import re
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm


def _setup_font():
    candidates = ["Microsoft YaHei", "SimHei", "PingFang SC",
                  "Noto Sans CJK SC", "WenQuanYi Micro Hei"]
    installed = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in installed:
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["axes.unicode_minus"] = False
            return True
    return False


HAS_CJK = _setup_font()
L = (lambda zh, en: zh) if HAS_CJK else (lambda zh, en: en)

PROFESSIONS = ["peasants", "laborers", "servicemen", "clerks",
               "clergymen", "bureaucrats", "aristocrats", "capitalists"]
IGS = ["rural_folk", "trade_unions", "intelligentsia", "landowners",
       "church", "industrialists", "military"]
SYSTEMS = ["absolute_monarchy", "constitutional_monarchy", "republic",
           "democracy", "socialist_republic", "theocracy"]


def find_col(df, *keywords):
    for c in df.columns:
        lc = c.lower()
        if all(k.lower() in lc for k in keywords):
            return c
    return None


def plot_lines(df, x_col, y_col, title, ylabel, out_path):
    fig, ax = plt.subplots(figsize=(11, 6), dpi=120)
    if "country_name" in df.columns and df["country_name"].nunique() > 1:
        for cname, sub in df.groupby("country_name"):
            ax.plot(sub[x_col], sub[y_col], label=cname, linewidth=2, alpha=0.8)
    else:
        ax.plot(df[x_col], df[y_col], linewidth=2)
    ax.set_xlabel(L("年份", "Year"))
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(alpha=0.3)
    if "country_name" in df.columns and df["country_name"].nunique() > 1:
        ax.legend(fontsize=8, ncol=2)
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"  写出: {out_path}")


def plot_stacked(df, x_col, cols, title, out_path, labels=None):
    fig, ax = plt.subplots(figsize=(11, 6), dpi=120)
    labels = labels or cols
    ax.stackplot(df[x_col], *[df[c] for c in cols], labels=labels, alpha=0.85)
    ax.set_xlabel(L("年份", "Year"))
    ax.set_ylabel(L("人数", "Population"))
    ax.set_title(title)
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"  写出: {out_path}")


def plot_systems(df, x_col, sys_col, title, out_path):
    order = {s: i for i, s in enumerate(SYSTEMS)}
    fig, ax = plt.subplots(figsize=(11, 5), dpi=120)
    for cname, sub in df.groupby("country_name"):
        y = sub[sys_col].map(lambda s: order.get(s, -1))
        ax.step(sub[x_col], y, where="post", label=cname, linewidth=2)
    ax.set_yticks(range(len(SYSTEMS)))
    ax.set_yticklabels(SYSTEMS, fontsize=8)
    ax.set_xlabel(L("年份", "Year"))
    ax.set_title(title)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"  写出: {out_path}")


def visualize_sim(df, tag, out_dir):
    x = find_col(df, "year")
    gdp = find_col(df, "gdp")
    sys_col = find_col(df, "political_system")
    pop_cols = [c for c in (find_col(df, p) for p in PROFESSIONS) if c]
    ig_cols = [c for c in (find_col(df, ig) for ig in IGS) if c]

    if gdp:
        plot_lines(df, x, gdp, f"[{tag}] GDP", "GDP", out_dir / f"{tag}_gdp.png")
    if pop_cols:
        plot_stacked(df, x, pop_cols,
                     f"[{tag}] {L('人口结构', 'Population Structure')}",
                     out_dir / f"{tag}_pops.png", labels=pop_cols)
    if ig_cols:
        plot_stacked(df, x, ig_cols,
                     f"[{tag}] {L('利益集团影响力', 'IG Influence')}",
                     out_dir / f"{tag}_igs.png", labels=ig_cols)
    if sys_col:
        # 单国也按 country_name 分组画（虽然只有一组）
        plot_systems(df, x, sys_col,
                     f"[{tag}] {L('政治制度', 'Political System')}",
                     out_dir / f"{tag}_system.png")


def visualize_world(df, tag, out_dir):
    x = find_col(df, "year")
    gdp = find_col(df, "gdp")
    sys_col = find_col(df, "political_system")
    worker = find_col(df, "laborers")
    pop_cols = [c for c in (find_col(df, p) for p in PROFESSIONS) if c]

    if gdp:
        plot_lines(df, x, gdp, f"[{tag}] {L('各国 GDP', 'GDP by Country')}",
                   "GDP", out_dir / f"{tag}_gdp.png")

    if worker and pop_cols:
        fig, ax = plt.subplots(figsize=(11, 6), dpi=120)
        for cname, sub in df.groupby("country_name"):
            total = sub[pop_cols].sum(axis=1).replace(0, 1)
            ratio = sub[worker] / total
            ax.plot(sub[x], ratio, label=cname, linewidth=2)
        ax.set_xlabel(L("年份", "Year"))
        ax.set_ylabel(L("工人占比", "Worker Ratio"))
        ax.set_title(f"[{tag}] {L('各国工人占比', 'Worker Ratio by Country')}")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, ncol=2)
        plt.tight_layout()
        plt.savefig(out_dir / f"{tag}_worker_ratio.png", bbox_inches="tight")
        plt.close(fig)
        print(f"  写出: {out_dir / f'{tag}_worker_ratio.png'}")

    if sys_col:
        plot_systems(df, x, sys_col,
                     f"[{tag}] {L('各国政治制度', 'Political Systems')}",
                     out_dir / f"{tag}_system.png")


def main():
    out_dir = Path("output/figures")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"中文字体: {'可用' if HAS_CJK else '不可用，标签用英文'}")
    print("=" * 60)

    print("\n[单国]")
    sim_files = sorted(Path("output").glob("sim_*.csv"))
    sim_files = [f for f in sim_files if "_events" not in f.name and "_final" not in f.name]
    if not sim_files:
        print("  未找到 sim_*.csv")
    for f in sim_files:
        m = re.search(r"sim_(\w+)_y\d+", f.name)
        tag = m.group(1) if m else f.stem
        df = pd.read_csv(f, encoding="utf-8")
        print(f"  处理 {f.name}")
        visualize_sim(df, f"sim_{tag}", out_dir)

    print("\n[多国]")
    world_files = sorted(Path("output").glob("world_*.csv"))
    world_files = [f for f in world_files if "_events" not in f.name and "_final" not in f.name]
    if not world_files:
        print("  未找到 world_*.csv")
    for f in world_files:
        m = re.search(r"world_n\d+_y\d+_s\d+", f.name)
        tag = m.group(0) if m else f.stem
        df = pd.read_csv(f, encoding="utf-8")
        print(f"  处理 {f.name}")
        visualize_world(df, tag, out_dir)

    print("\n完成。图片在:", out_dir)


if __name__ == "__main__":
    main()