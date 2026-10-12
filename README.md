# historia

无头历史模拟沙盒。验证命题：**经济基础决定上层建筑**。

```
工业化 → 农民变工人 → 工人政治意识上升 → 改革压力 → 政治制度变化
```

本项目用多个规则 AI 同时模拟多个国家（8 职业 + 3 阶层 + 7 利益集团），
跑指定年数，观察该命题是否成立。只输出 CSV / TXT，无 UI。

## 技术栈

- Python 3.10+
- 仅 `numpy`、`pandas`

## 安装

```bash
pip install -r requirements.txt
```

## 快速冒烟测试

```bash
python scripts/run_sim.py --goal reform --years 10
python scripts/run_world.py --nations 3 --years 10
```

运行后 `output/` 下会生成 `.csv` 与 `.txt` 报告（文件名含参数与时间戳，不会覆盖）。

## 完整验证

单国 4 个目标对比（观察结局差异）：

```bash
python scripts/run_sim.py --goal industrialize --years 50
python scripts/run_sim.py --goal stabilize --years 50
python scripts/run_sim.py --goal reform --years 50
python scripts/run_sim.py --goal balance --years 50
```

多国 50 年（观察"工业化国家 vs 稳定但落后国家"的分化）：

```bash
python scripts/run_world.py --nations 6 --years 50
```

## 敏感性分析

```bash
python scripts/run_world.py --nations 3 --years 200 --seed 1
python scripts/run_world.py --nations 10 --years 50 --seed 1
python scripts/run_world.py --nations 10 --years 50 --seed 2
```

换 seed 后历史走向不同，但规律应一致（可复现）。

## 命令行参数

### 单国 `scripts/run_sim.py`

| 参数 | 默认 | 说明 |
|---|---|---|
| `--goal` | reform | 目标 key（industrialize / stabilize / reform / balance / military / mercantilist / agrarian / revolutionary / isolationist / theocracy / welfare / enlightenment） |
| `--years` | 50 | 模拟年数 |
| `--provinces` | 8 | 省份数 |
| `--seed` | 42 | 随机种子 |
| `--tax-rate` | 0.20 | 初始税率 |
| `--treasury` | 10000 | 初始国库 |
| `--initial-pop` | 1000 | 每省初始总人口 |
| `--initial-tech` | 0.1 | 初始技术水平 |

### 多国 `scripts/run_world.py`

| 参数 | 默认 | 说明 |
|---|---|---|
| `--nations` | 6 | 国家数 |
| `--years` | 50 | 模拟年数 |
| `--provinces-per-nation` | 4 | 每国省份数 |
| `--seed` | 42 | 随机种子 |
| `--goal-mode` | random | `random` / `cycle` / `explicit` |
| `--goals` | — | 显式目标列表（explicit 模式，数量须等于 nations） |
| `--initial-tech` | 0.1 | 初始技术水平 |

## 输出文件

```
output/
  sim_<goal>_y<years>_s<seed>_<timestamp>.csv           # 逐年快照（长表）
  sim_<goal>_y<years>_s<seed>_<timestamp>_final.csv     # 每国最终状态
  sim_<goal>_y<years>_s<seed>_<timestamp>_events.csv    # 事件时间线
  sim_<goal>_y<years>_s<seed>_<timestamp>.txt           # 人类可读报告
```

报告 TXT 含：参数头、最终状态（按 GDP 排序）、关键事件时间线、变化对比、单国 IG 演变。

## 目录结构

```
historia/
├── main.py
├── requirements.txt
├── docs/design.md          # 设计文档
├── sim/                    # 核心模拟包
│   ├── config.py           # 默认参数
│   ├── models.py           # 数据结构
│   ├── names.py            # 国家名生成
│   ├── pop.py              # POP 变化 + 阶级流动
│   ├── province.py         # 省份产出
│   ├── nation.py           # 国家创建
│   ├── interest_group.py   # 利益集团
│   ├── economy.py          # 经济结算
│   ├── politics.py         # 政治结算 + 农民起义
│   ├── ai.py               # AI 决策
│   ├── goals.py            # 目标库
│   ├── world.py            # 世界市场 + 技术扩散
│   ├── events.py           # 事件检测
│   ├── report.py           # 报告生成
│   └── simulate.py         # 主循环
├── scripts/
│   ├── run_sim.py
│   └── run_world.py
└── output/
```
