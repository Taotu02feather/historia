"""
一键跑所有验证 + 可视化。
用法：python scripts/run_all.py
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime

COMMANDS = [
    ("单国-industrialize", ["python", "scripts/run_sim.py", "--goal", "industrialize", "--years", "50"]),
    ("单国-stabilize",     ["python", "scripts/run_sim.py", "--goal", "stabilize",     "--years", "50"]),
    ("单国-reform",        ["python", "scripts/run_sim.py", "--goal", "reform",        "--years", "50"]),
    ("单国-balance",       ["python", "scripts/run_sim.py", "--goal", "balance",       "--years", "50"]),
    ("世界-n6-y50",        ["python", "scripts/run_world.py", "--nations", "6",  "--years", "50"]),
    ("世界-n3-y200-s1",    ["python", "scripts/run_world.py", "--nations", "3",  "--years", "200", "--seed", "1"]),
    ("世界-n10-y50-s1",    ["python", "scripts/run_world.py", "--nations", "10", "--years", "50",  "--seed", "1"]),
    ("世界-n10-y50-s2",    ["python", "scripts/run_world.py", "--nations", "10", "--years", "50",  "--seed", "2"]),
]


def run_commands(log_path):
    """跑所有命令，把 stdout/stderr/耗时写入 log（不写报告正文）。"""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    with open(log_path, "w", encoding="utf-8") as log:
        log.write(f"historia 批量验证\n")
        log.write(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"命令数: {len(COMMANDS)}\n")
        log.write("=" * 70 + "\n\n")

        ok_count = 0
        for i, (name, cmd) in enumerate(COMMANDS, 1):
            print(f"[{i}/{len(COMMANDS)}] {name} ...", flush=True)
            log.write(f"[{i}/{len(COMMANDS)}] {name}\n")
            log.write(f"  命令: {' '.join(cmd)}\n")

            t0 = datetime.now()
            try:
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace")
                elapsed = (datetime.now() - t0).total_seconds()
                log.write(f"  耗时: {elapsed:.1f}s  返回码: {r.returncode}\n")
                if r.returncode != 0:
                    log.write(f"  !!! 失败\n")
                    if r.stderr:
                        log.write(f"  STDERR: {r.stderr[:500]}\n")
                else:
                    ok_count += 1
                log.write("\n")
                print(f"    耗时 {elapsed:.1f}s, 返回码 {r.returncode}")
            except Exception as e:
                log.write(f"  !!! 异常: {e}\n\n")
                print(f"    异常: {e}")

        log.write("=" * 70 + "\n")
        log.write(f"完成 {ok_count}/{len(COMMANDS)}\n")

    return ok_count


def main():
    log_path = Path("output") / f"run_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # 1. 跑所有命令
    print("=" * 60)
    print("阶段 1: 跑模拟")
    print("=" * 60)
    ok = run_commands(log_path)
    print(f"\n模拟完成: {ok}/{len(COMMANDS)} 成功")
    print(f"日志: {log_path}\n")

    # 2. 可视化
    print("=" * 60)
    print("阶段 2: 可视化")
    print("=" * 60)
    try:
        from visualize import main as visualize_main
        visualize_main()
    except ImportError:
        # 如果直接跑不在同目录，用子进程
        r = subprocess.run(["python", "scripts/visualize.py"])
        if r.returncode != 0:
            print("可视化失败。请确认已装 matplotlib:")
            print("  pip install matplotlib")
            sys.exit(1)
    except ModuleNotFoundError as e:
        if "matplotlib" in str(e):
            print("可视化失败：matplotlib 未安装。")
            print("  pip install matplotlib")
        else:
            raise

    print("\n" + "=" * 60)
    print(f"全部完成。图片在: output/figures/")
    print("=" * 60)


if __name__ == "__main__":
    main()