"""run_sim.py — 单国模拟入口。"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim.config import Config
from sim.simulate import run_sim
from sim.report import write_report


def main() -> None:
    parser = argparse.ArgumentParser(description="historia 单国模拟")
    parser.add_argument("--goal", default="reform", help="目标 key（见 goals.py）")
    parser.add_argument("--years", type=int, default=50)
    parser.add_argument("--provinces", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--tax-rate", type=float, default=0.20, help="初始税率")
    parser.add_argument("--treasury", type=float, default=10000.0, help="初始国库")
    parser.add_argument("--initial-pop", type=int, default=1000, help="每省初始总人口")
    parser.add_argument("--initial-tech", type=float, default=0.1, help="初始技术水平")
    parser.add_argument("--outdir", default="output")
    args = parser.parse_args()

    cfg = Config(
        goal=args.goal, years=args.years, provinces=args.provinces,
        seed=args.seed, tax_rate=args.tax_rate, treasury=args.treasury,
        initial_pop=args.initial_pop, initial_tech=args.initial_tech,
        outdir=args.outdir,
    )
    result = run_sim(cfg)
    files = write_report(result, cfg, args.outdir)
    print("生成文件：")
    for f in files:
        print("  ", f)


if __name__ == "__main__":
    main()
