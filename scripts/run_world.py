"""run_world.py — 多国模拟入口。"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim.config import Config
from sim.simulate import run_world
from sim.report import write_report


def main() -> None:
    parser = argparse.ArgumentParser(description="historia 多国模拟")
    parser.add_argument("--nations", type=int, default=6)
    parser.add_argument("--years", type=int, default=50)
    parser.add_argument("--provinces-per-nation", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--goal-mode", default="random",
                        choices=["random", "cycle", "explicit"])
    parser.add_argument("--goals", nargs="*", default=[],
                        help="显式目标 key 列表（explicit 模式，数量须等于 nations）")
    parser.add_argument("--initial-tech", type=float, default=0.1)
    parser.add_argument("--outdir", default="output")
    args = parser.parse_args()

    if args.goal_mode == "explicit":
        if len(args.goals) != args.nations:
            parser.error(f"--goals 数量({len(args.goals)}) 必须等于 --nations({args.nations})")

    cfg = Config(
        nations=args.nations, years=args.years,
        provinces_per_nation=args.provinces_per_nation, seed=args.seed,
        goal_mode=args.goal_mode, goals=list(args.goals),
        initial_tech=args.initial_tech, outdir=args.outdir,
    )
    result = run_world(cfg)
    files = write_report(result, cfg, args.outdir)
    print("生成文件：")
    for f in files:
        print("  ", f)


if __name__ == "__main__":
    main()
