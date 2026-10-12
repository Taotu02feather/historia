"""main.py — 顶层入口，分发到单国 / 多国模拟。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    print("historia — 无头历史模拟沙盒")
    print("用法：")
    print("  python scripts/run_sim.py --goal reform --years 10")
    print("  python scripts/run_world.py --nations 3 --years 10")


if __name__ == "__main__":
    main()
