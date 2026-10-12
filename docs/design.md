# historia — 设计方案（v2）

> 无头历史模拟沙盒 · 验证命题："经济基础决定上层建筑"
> 本文档是**阶段 A 的设计规格**，不含实现代码。确认后再进入阶段 B 实现。

---

## 0. 概述

因果链：

```
工业化 → 农民变工人 → 工人政治意识上升 → 改革压力 → 政治制度变化
```

验证方式：多个规则 AI 国家同时模拟，跑指定年数，观察命题是否成立。要求**可验证、可复现、可观察**（只输出 CSV/TXT，无 UI）。

技术栈硬约束：Python 3.10+，仅 numpy + pandas；dataclass 定义结构；类型注解；中文注释；argparse；`numpy.random.default_rng(seed)`。

---

## 1. 模块组织（A1）

```
historia/
├── main.py                  # 顶层入口（分发到 run_sim / run_world）
├── requirements.txt         # numpy, pandas
├── README.md
├── docs/design.md           # 本文件
├── sim/
│   ├── __init__.py
│   ├── config.py            # 默认参数（dataclass + 常量）
│   ├── models.py            # Pop / Province / Nation / InterestGroup
│   ├── names.py             # 国家名音节生成
│   ├── pop.py               # POP 财富/意识/满意度 + update_pop_promotion(阶级流动)
│   ├── province.py          # 省份产出、建造
│   ├── nation.py            # 国家初始化、国级聚合
│   ├── interest_group.py    # IG 影响力计算、执政联盟、agitation
│   ├── economy.py           # 经济结算：产出→税收→国库
│   ├── politics.py          # 政治结算：意识→改革压力→稳定性→制度变化
│   ├── ai.py                # AI 决策（读目标参数组 + IG 反应）
│   ├── goals.py             # 目标库（12 个参数组）
│   ├── world.py             # 多国：世界市场定价 + 技术扩散
│   ├── events.py            # 关键事件检测
│   ├── report.py            # CSV / TXT 报告
│   └── simulate.py          # 年度推演主循环
├── scripts/
│   ├── run_sim.py           # 单国入口
│   └── run_world.py         # 多国入口
└── output/                  # 输出（gitignore）
```

依赖方向（无环）：

```
models ← names, goals
interest_group, pop, province ← models
economy, politics, ai ← models (+pop/province/interest_group)
world ← economy(价格) + politics(技术/扩散)
events, report ← models
simulate ← 以上全部
scripts/main ← simulate + config
```

---

## 2. 数据结构（dataclass）

### 2.1 Pop（8 职业）
| 字段 | 类型 | 说明 |
|---|---|---|
| profession | str | 8 职业之一（见 §4） |
| strata | str | `"lower" | "middle" | "upper"` |
| size | float | 人口规模（内部 float，报告 round 成 int；迁移时 <1 累积不归零） |
| wealth | float | 人均财富 |
| political_awareness | float | 政治意识 0~1 |
| satisfaction | float | 满意度 0~1 |
| ig_membership | str \| None | 所属利益集团 id |

### 2.2 Province
| 字段 | 类型 | 说明 |
|---|---|---|
| id | int | 全球唯一递增 |
| name | str | `"<国家名>-P<数字>"` |
| land_quality | float | 农业地力 0~1 |
| coal_deposit | float | 煤矿丰度 0~1 |
| factories | int | 工厂数 |
| farms | int | 农场数 |
| mines | int | 矿山数 |
| pops | list[Pop] | 该省 8 职业的 Pop |

### 2.3 InterestGroup（7 个）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | str | 见 §5 |
| name | str | 中文名 |
| member_professions | list[str] | 代表职业 |
| influence | float | 影响力 0~1（全体归一化和为 1） |
| stance_on_reform | float | 改革立场 -1~+1 |
| in_government | bool | 是否执政 |
| agitation | float | 躁动 0~1 |

### 2.4 Nation
保留原核心字段 + 新增（`(*)`）：
| 字段 | 类型 | 说明 |
|---|---|---|
| id | int | |
| name | str | 音节随机生成 |
| provinces | list[Province] | |
| treasury | float | 国库 |
| tax_rate | float | 税率 0~1 |
| stability | float | 稳定度 0~1 |
| reform_level | float | 改革程度 0~1 |
| reform_pressure | float | 改革压力（无固定界，触发阈值见 §5.3/§8.7） |
| political_system | str | 制度枚举（见 §8） |
| goal | str | 目标 key |
| `(*)` tech_level | float | 技术水平 0~1（驱动产出/流动/扩散） |
| `(*)` interest_groups | dict[str, InterestGroup] | 7 个 IG |
| `(*)` gdp | float | 当年 GDP（缓存） |
| `(*)` gdp_history | list[float] | 历年 GDP（缓存，供报告/衰退判断） |

## 3. 核心循环（A2）

每年严格四步，顺序不可变：

```
for year in range(years):
    economy.settle(world, nations)         # 1. 经济结算
    pop.step(nations)                       # 2. POP 变化（财富/意识/满意度 + 阶级流动）
    politics.settle(nations)                # 3. 政治结算（IG 影响力 + 改革压力 + 制度）
    ai.decide(nations, world)               # 4. AI 决策（次年生效）
    events.detect(...)                      # 事件检测（只读）
```

- AI 决策在年末执行，影响**下一年**的税率/建造/改革立场；第 1 年用初始参数。
- 每步依赖的字段与参数详见 §7~§11。

---

## 4. 阶级体系（A3）— 8 职业 + 3 阶层

### 4.1 三阶层
| 阶层 | 成员 | 定位 |
|---|---|---|
| lower | peasants, laborers, servicemen | 底层 |
| middle | clerks, clergymen, bureaucrats | 中层 |
| upper | aristocrats, capitalists | 上层 |

### 4.2 八职业
| profession | 中文 | 阶层 | 角色 |
|---|---|---|---|
| peasants | 农民/自耕农 | lower | 传统农业基础，保守，工业化劳动力蓄水池 |
| laborers | 劳工/矿工 | lower | 早期工业无产者，与矿产/工厂挂钩 |
| servicemen | 军人 | lower | 维持稳定的暴力工具，来自下层，效忠国家 |
| clerks | 职员/文书 | middle | 工厂管理者/技术工人，技术扩散关键 |
| clergymen | 教士 | middle | 传统教育与思想控制，降意识但阻改革 |
| bureaucrats | 官僚 | middle | 国家机器运转，提行政效率，忠诚度影响稳定 |
| aristocrats | 贵族/地主 | upper | 旧制度统治阶级，靠地租，强烈反改革 |
| capitalists | 资本家 | upper | 工业化推动者，逐利，支持经济自由与有限改革 |

### 4.3 初始人口分布（每省，比例）
```
peasants 70% · laborers 5% · servicemen 5% · clergymen 10%
bureaucrats 5% · aristocrats 3% · capitalists 2% · clerks 0%
```
- `clerks` 初始 0 人口，呼应事件 `first_clerk_appears`；`clergymen` 初始 10%。
- 初始 IG 影响力由该分布计算（`rural_folk` 最高，因 peasants 占 70%）。

## 5. 利益集团（A4）— 7 个 IG

| id | 中文名 | 代表职业 | 立场 |
|---|---|---|---|
| rural_folk | 乡村民众 | peasants | 传统保守，但被逼急会激进起义 |
| trade_unions | 工会 | laborers | 劳工权益、普选权、社会改革 |
| intelligentsia | 知识分子 | clerks, bureaucrats | 教育、世俗化、自由改革、科技 |
| landowners | 地主贵族 | aristocrats | 传统、土地权利、稳定、反改革 |
| church | 教会 | clergymen | 宗教教育、传统道德、穷人救济 |
| industrialists | 工业家 | capitalists | 自由贸易、利润、有限改革 |
| military | 军方 | servicemen | 军费、秩序、扩张、镇压 |

### 5.1 影响力计算（每年政治结算时重算）
```
raw_influence[ig] = Σ (成员.size × wealth × (0.5 + political_awareness))
influence[ig]     = raw_influence[ig] / Σ_all raw_influence      # 全体归一化和=1
```

### 5.2 基础改革立场（stance_on_reform）
```
trade_unions    +0.8
intelligentsia  +0.7
industrialists  +0.3
military        -0.2
rural_folk      -0.3   （基础值，有特殊修正）
church          -0.7
landowners      -0.9
```

`rural_folk` 特殊修正：
```
平均 satisfaction < 0.3        → stance += 0.8   （从保守变激进）
aristocrats 压迫过重(地租/农民税前收入 > 0.35) → stance += 0.3
clergymen 影响力高(>0.3)       → stance -= 0.2
```

### 5.3 改革压力（politics）
```
reform_pressure = Σ (influence[ig] × stance_on_reform[ig]) × (1 + 工人政治意识)
  >  +0.6 → 启动制度改革（制度前进一格，见 §8）
  <  -0.3 → 可能倒退（theocracy 或强化君主制）
```
- "工人政治意识" = laborers 职业的平均 `political_awareness`。

### 5.4 执政联盟规则
| 制度 | 执政 IG |
|---|---|
| absolute_monarchy | landowners, church, military |
| constitutional_monarchy | + industrialists, intelligentsia |
| republic | 所有 IG 可选，每 5 年"选举" |
| democracy | 每 3 年选举，trade_unions 影响力放大 |
| theocracy | church 独占 |
| socialist_republic | trade_unions, intelligentsia 主导 |

执政/在野效果：
- 执政 IG：改革立场对 `reform_pressure` 影响**加倍**，并提供 stability 加成。
- 在野 IG：`agitation` 每年 +0.05；`agitation > 0.7` 触发抗议（stability 下降、该 IG 立场更激进）。

### 5.5 IG 之间的互动（定性规则，用于修正立场/同盟）
```
rural_folk + landowners:    默认同盟，但加租过度(地租>阈值)则倒向工会
rural_folk + church:        默认同盟，但教会站贵族一边则疏远
rural_folk + trade_unions:  潜在同盟，需双方 satisfaction 都低
rural_folk + industrialists: 敌对
```

---

## 6. 农民起义机制（A5）

触发条件（同时满足）：
```
rural_folk.agitation > 0.85 且 rural_folk.influence > 0.35
```

效果：
1. `stability -= 0.3`（clamp 到 0）。
2. 所有 IG `agitation += 0.1`。
3. 依当前制度分支：
   - **monarchy**（absolute/constitutional）：
     - 50% → 直接进入 `republic`
     - 50% → 被镇压，但 stability 长期受损（设 `suppressed_flag`，后续每年 stability 缓慢恢复）
   - **republic**：
     - 30% → 变为 `socialist_republic`
     - 70% → 恢复稳定，但 `rural_folk.influence` 永久下降（乘 0.7）

实现为独立函数 `check_peasant_uprising(nation, rng)`，在政治结算后、AI 决策前调用。

## 7. 经济结算（A6）

### 7.1 各职业生产贡献
- **农业**：`peasants` 主要产出；`aristocrats` 抽 30% 地租。
  ```
  Agri = Σ_省 (land_quality × farms × AGR_BASE × labor_farm)
  labor_farm = 0.3 + 0.7 × min(peasant.size / (farms × FARM_CAP), 1)
  地租 = Agri × 0.30   （从 peasants 税前收入里扣，转入 aristocrats，不额外生成产出）
  ```
- **矿业**：`laborers` 产出。
  ```
  Mine = Σ_省 (coal_deposit × mines × MINE_BASE × labor_mine)
  labor_mine = 0.3 + 0.7 × min(laborer.size / (mines × MINE_CAP), 1)
  ```
- **工厂**：`laborers + clerks`（clerks 效率 1.5 倍）；`capitalists` 获利润。
  ```
  Indu = Σ_省 (factories × IND_BASE × (1 + TECH_GAIN × tech_level)
               × labor_factory × coal_factor)
  labor_factory = 0.3 + 0.7 × min((laborer + 1.5×clerk) / (factories × FACT_CAP), 1)
  coal_factor   = 1 + 0.5 × min(coal_supply / coal_need, 1)
  ```
- **税收效率**：`tax_eff = min(1.0, 0.5 + bureaucrats.size / total_pop × 10)`。
- **clergymen** 不直接贡献经济，但影响 stability（见 §8）。

### 7.2 世界市场（多国模式，三类独立定价）
```
price_farm    = base_farm    × (1 - 全球农产出 / 基准农产出 × 0.5)
price_mine    = base_mine    × (1 - 全球矿产出 / 基准矿产出 × 0.5)
price_factory = base_factory × (1 - 全球工产出 / 基准工产出 × 0.5)
基础价：base_factory > base_mine > base_farm（体现国际贸易的结构性不平等）
每国收入 = farm产出 × price_farm + mine产出 × price_mine + factory产出 × price_factory
```
- 单国模式：三类价格都 = 对应 base（无外部市场）。
- 基准产出 = 首年全球各类产出（可复现）。
- "剪刀差"：农业国被工业化国家挤压（工业品贵、农产品贱）。

### 7.3 税收 → 国库
```
gdp         = Agri + Mine + Indu
tax_income  = gdp × tax_rate × tax_eff
treasury   += tax_income
              - military_cost   (goal.military_spending × gdp)
              - welfare_cost    (goal.welfare_spending × gdp)
              - admin_cost      (ADMIN_COEF × total_pop)
              - build_cost      (本年建造扣款，§11)
```
`treasury` 允许短期为负；连续 3 年为负触发 `economic_crisis`。

---

## 8. 政治结算（A7）

### 8.1 改革阻力与推动
- 阻力：`aristocrats`(强)、`clergymen`(强)、`servicemen`(中)。
- 推动：`capitalists`、`clerks`、`laborers`、`bureaucrats`。
- 落实为 IG 的 `stance_on_reform`（§5.2）与改革压力公式（§5.3）。

### 8.2 政治意识增长率（每职业 / 年）
```
laborers 0.025 · clerks 0.015 · peasants 0.005 · servicemen 0.002
aristocrats 0.001 · clergymen 0.001 · bureaucrats 0.003 · capitalists 0.010
```

### 8.3 思想控制（clergymen）
```
有效意识 = 原始意识 × (1 - clergymen.size / total_pop × 2)   # clamp ≥ 0
```

### 8.4 军人规模约束 + 镇压能力
```
servicemen 规模约束：
  上限：servicemen.size ≤ total_pop × 0.05
  下限：servicemen.size ≥ total_pop × 0.01（财政危机 treasury<0 时可突破下限）
镇压能力：servicemen.size > total_pop × 0.05 时，stability 下限提升到 0.3
```

### 8.5 政治制度序列
```
absolute_monarchy → constitutional_monarchy → republic → democracy
                                                        ↘ socialist_republic
独立分支：theocracy（任一制度可退化，当 church 影响力 > 0.5）
```

### 8.6 stability 计算
```
stability = clamp( STAB_BASE
                 + STAB_SAT   × (mean_satisfaction - 0.5)
                 - STAB_PRESS × reform_pressure
                 - STAB_TAX   × (tax_rate - 0.2)
                 + STAB_IG    × (执政 IG 加成)
                 + STAB_CLERGY× clergy_bias, 0, 1 )
```
- `reform_pressure` 已含 IG 加权（§5.3），`STAB_PRESS` 用其绝对值惩罚。

### 8.7 制度改革触发
```
reform_pressure > +0.6 → 制度前进一格（沿主线）
reform_pressure < -0.3 → 可能倒退（theocracy 或强化君主制）
church.influence > 0.5  → 可退化为 theocracy
```

## 9. 阶级流动（A8）— update_pop_promotion

每年在 POP 变化步骤中运行 `update_pop_promotion(nation)`，**每省独立、不跨省**。

### 9.1 流动规则表
| 方向 | 条件 | 最大速率 | 触发强度 trigger |
|---|---|---|---|
| peasants → laborers | 有工厂或矿场 | 3% | `min(1,(factories+mines)/PROV_BUILDING_REF) × (1 - 0.4×land_quality)` |
| laborers → clerks | tech_level > 0.3 且有工厂 | 1% | `min(1,(tech_level-0.3)/0.7) × min(1,factories/PROV_BUILDING_REF)` |
| peasants → clerks | tech_level > 0.5 且教育高 | 0.5% | `min(1,(tech_level-0.5)/0.5) × education` |
| laborers/clerks → capitalists | 财富累积到阈值 | 0.1% | `1 if wealth ≥ WEALTH_CAPITALIST else 0` |
| laborers → peasants | satisfaction < 0.2 | 2% | `min(1,(0.2-satisfaction)/0.2)` |
| clerks → laborers | 经济衰退 | 1% | `1 if gdp 连续 2 年下降 else 0` |
| capitalists → clerks | 连续多年负利润 | 0.05% | `1 if 连续负利润 ≥ N else 0` |

- `education` = `min(1, reform_level + clerks占比 × 2)`（教育水平由改革程度与职员规模近似）。
- 负利润：工业利润 < 0 的连续年数。

### 9.2 通用规则
1. 实际速率 = 最大速率 × 触发强度（再受 §9.3 修正）。
2. 人数按比例迁移，`wealth` 也按比例迁移（保持迁移前后总财富守恒）。
3. 每省独立，不跨省。
4. 高税率抑制向上流动，高 tech_level 促进向上流动（见 §9.3）。
5. 流动后重新计算所有 IG 影响力（§5.1）。
6. `size` 为 float；迁移时若某职业剩余人数 < 1，累积到下回合，不归零。

### 9.3 税率 / 技术修正
```
向上流动实际速率 ×= (1 - UP_TAX_PENALTY × tax_rate)   # 高税抑制
向上流动实际速率 ×= (0.5 + 0.5 × tech_level)           # 高技术促进
```

---

## 10. 技术扩散（A9，多国模式）

```
每国每年：
  自主研发   tech += TECH_SPEED × goal.tech_bias × (0.5 + 0.5 × 工业产出占比)
  基础扩散   tech += 0.03 × 0.01 × (1 - goal.diffuse_resist)   # 3% 概率 +0.01
  邻接扩散   tech += (相邻国中最高 tech - 本国 tech) × 0.1 × (1 - goal.diffuse_resist)
```
- **邻接限制**：环形邻接，`id` 相邻（`|id_a - id_b| == 1`）且国 N-1 与国 0 相邻。
- **阻力**：孤立主义 / 神权 的 `diffuse_resist` 高，扩散慢。
- `tech_level` clamp 到 [0, 1]。

## 11. AI 决策（A10）

AI 读取目标参数组 `GoalParams`，并在决策时**评估 7 个 IG 的反应**（受益/受损 → 影响其 agitation 与后续 stance）。

### 11.1 决策项与 IG 反应
| 决策 | 受益 IG | 受损 IG |
|---|---|---|
| 建工厂 | trade_unions, intelligentsia, industrialists | landowners, church, rural_folk |
| 建农田 | rural_folk, landowners | — |
| 建矿场 | trade_unions, industrialists | rural_folk |
| 高税率 | military, bureaucrats | industrialists, trade_unions, rural_folk |
| 推进改革 | trade_unions, intelligentsia, industrialists | landowners, church |
| 镇压 | landowners, church, military | trade_unions, intelligentsia（危险：可能激怒 rural_folk） |

### 11.2 决策逻辑
```
税率   tax_rate = clamp(goal.tax_bias × (1 + deficit_pressure), 0.05, 0.60)
建造   按 goal.build_priority 权重贪心，优先权重高、国库负担得起者
改革   goal.reform_stance 决定：推进 / 中立 / 镇压（-2 镇压 -1 压制 0 中立 +1 改革 +2 激进）
军费   military_cost = goal.military_spending × gdp
福利   welfare_cost  = goal.welfare_spending × gdp
```
决策执行后，按 §11.1 更新相关 IG 的 `agitation`（受益 -0.02，受损 +0.03，clamp 0~1）。

### 11.3 目标库（12 个）— GoalParams 字段
```
key, name,
tax_bias, build_priority{农田,矿场,工厂}, reform_stance,
military_spending, welfare_spending, tech_bias, diffuse_resist,
ig_affinity: dict[str,float]   # 对 7 个 IG 的亲和度 -1~+1
```

| key | 名称 | tax | build{农,矿,工} | reform | 军费 | 福利 | tech | 阻力 |
|---|---|---|---|---|---|---|---|---|
| industrialize | 工业化优先 | .20 | {.05,.25,.70} | +1 | .05 | .02 | .15 | 0 |
| stabilize | 稳定优先 | .15 | {.40,.30,.30} | -1 | .15 | .05 | .08 | .1 |
| reform | 改革优先 | .25 | {.40,.20,.40} | +2 | .05 | .10 | .12 | 0 |
| balance | 均衡发展 | .18 | {.33,.33,.33} | 0 | .08 | .06 | .10 | 0 |
| military | 军事扩张 | .30 | {.20,.30,.50} | -1 | .35 | .02 | .10 | 0 |
| mercantilist | 重商主义 | .28 | {.20,.40,.40} | 0 | .10 | .02 | .12 | .2 |
| agrarian | 农业保守 | .12 | {.80,.10,.10} | -2 | .08 | .03 | .04 | .3 |
| revolutionary | 激进革命 | .35 | {.10,.30,.60} | +2 | .10 | .08 | .15 | 0 |
| isolationist | 孤立主义 | .15 | {.50,.25,.25} | -1 | .12 | .05 | .05 | .6 |
| theocracy | 神权统治 | .20 | {.40,.30,.30} | -2 | .10 | .04 | .06 | .5 |
| welfare | 福利国家 | .32 | {.40,.20,.40} | +1 | .04 | .15 | .10 | 0 |
| enlightenment | 科技启蒙 | .22 | {.20,.30,.50} | +1 | .05 | .05 | .20 | 0 |

IG 亲和度（`ig_affinity`，7 列 = rural_folk / trade_unions / intelligentsia / landowners / church / industrialists / military）：

```
industrialize : -0.2, +0.6, +0.5, -0.5, -0.4, +0.8, -0.1
stabilize     : +0.3, -0.4, -0.2, +0.5, +0.4, -0.1, +0.5
reform        : +0.2, +0.7, +0.7, -0.6, -0.5, +0.3, -0.3
balance       : +0.1, +0.2, +0.2, +0.1,  0.0, +0.2,  0.0
military      :  0.0, -0.3, -0.1, +0.2, +0.2, +0.1, +0.9
mercantilist  : -0.1, +0.3, +0.2, -0.2, -0.1, +0.7, +0.2
agrarian      : +0.8, -0.5, -0.4, +0.7, +0.3, -0.5, -0.1
revolutionary : +0.5, +0.9, +0.6, -0.8, -0.6, -0.3, -0.5
isolationist  : +0.4, -0.2, -0.3, +0.3, +0.3, -0.2, +0.2
theocracy     : +0.2, -0.7, -0.6, +0.2, +0.9, -0.4,  0.0
welfare       : +0.3, +0.7, +0.4, -0.4, -0.1, +0.1, -0.2
enlightenment : -0.1, +0.5, +0.8, -0.5, -0.6, +0.4, -0.1
```
> 用途：AI 决策会偏向亲和度高的 IG（如 reform 倾向 trade_unions/intelligentsia），
> 亲和度也作为"目标对某 IG 的隐性支持"加入该 IG 的 stance 微调。

---

## 12. 关键事件（A11）

### 12.1 阶级流动事件
- `first_clerk_appears`：某国首次出现 `clerks`（size > 0）。
- `class_mobility_start`：某国累计向上流动人数超阈值（如总人口 5%）。
- `labor_crisis`：laborers 满意度 < 0.2 且改革压力 > 0.4。

### 12.2 利益集团事件
- `ig_formed`：某 IG 影响力从 0 变 > 0（首次出现）。
- `ig_dominant`：某 IG 影响力 > 0.35 成为主导。
- `ig_government_change`：执政联盟发生变化。
- `ig_agitation_crisis`：任一 IG agitation > 0.7。

### 12.3 乡村民众事件
- `rural_folk_dominant`：rural_folk 影响力 > 0.35。
- `rural_folk_decline`：rural_folk 影响力较峰值下降 > 50%。
- `peasant_uprising`：触发 §6 农民起义。
- `rural_urban_alliance`：rural_folk 与 trade_unions 形成同盟（双方 satisfaction < 0.3 且均 > 影响力阈值）。

### 12.4 制度事件
- `first_election`：首次进入 republic/democracy 选举。
- `trade_unions_legalized`：trade_unions 首次进入执政联盟或影响力 > 0.25。
- `theocracy_established`：制度变为 theocracy。

### 12.5 保留原有检测
- `industrial_revolution`（工业产出/GDP ≥ 0.30）
- `worker_awakening`（laborers 平均意识 ≥ 0.5）
- `reform_movement`（reform_pressure > 0.6）
- `system_change`（political_system 改变，记录 old→new + 年份）
- `revolution`（stability < REVOLT_THRESH 或农民起义）
- `tech_leader_change`（全球技术第一国易主）
- `economic_crisis`（国库连续 3 年为负）

---

## 13. 报告格式（A12）

### 13.1 多国报告表格（report.txt）
```
国家名    目标           GDP     最大IG                第二IG               制度
Valoria   industrialize 50000    trade_unions(0.32)    intelligentsia(0.25) constitutional
Kandor    stabilize     8000     rural_folk(0.45)      landowners(0.28)     monarchy
```

### 13.2 单国报告新增 IG 演变
```
【利益集团影响力演变】
IG                1830    1880    变化
rural_folk        0.52    0.18    ↓↓
landowners        0.20    0.08    ↓
church            0.12    0.06    ↓
trade_unions      0.00    0.28    ↑↑
intelligentsia    0.05    0.22    ↑↑
industrialists    0.06    0.12    ↑
military          0.05    0.06    -
```
（箭头：变化 > +0.10 记 ↑↑，+0.03~0.10 记 ↑，-0.03~+0.03 记 -，对称地 ↓/↓↓。）

### 13.3 CSV 列（B3）
```
year, country_id, country_name, goal,
treasury, tax_rate, stability, reform_level, reform_pressure,
total_pop, <8 职业人数>, <7 IG 影响力>,
total_factories, total_farms, total_mines,
avg_awareness, gdp, political_system, event
```

## 14. 参数化要求（A13）

所有规模参数从命令行传入，`config.py` 只存默认值。**禁止硬编码魔法数字**。

### 14.1 run_sim.py 参数
```
--goal GOAL          默认 "reform"
--years N            默认 50
--provinces N        默认 8
--seed N             默认 42
--tax-rate F         初始税率
--treasury F         初始国库
--initial-pop N      每省初始总人口
--initial-tech F     初始技术水平（默认 0.1）
```

### 14.2 run_world.py 参数
```
--nations N              默认 6
--years N                默认 50
--provinces-per-nation N 默认 4
--seed N                 默认 42
--goal-mode MODE         "random" | "cycle" | "explicit"
--goals G1 G2 G3 ...     显式指定目标（数量必须等于 nations）
```

### 14.3 输出文件名（含关键参数避免覆盖）
```
output/sim_<goal>_y<years>_s<seed>_<timestamp>.csv
output/world_n<nations>_y<years>_s<seed>_<timestamp>.csv
```
同时生成对应 `.txt` 报告（头部打印全部运行参数）。

### 14.4 可复现
- 主 RNG = `np.random.default_rng(seed)`。
- 国家名、省份属性、初始人口、目标分配各自用 `rng.spawn(n)` 派生子 RNG，与调用顺序解耦，保证同 seed 同参数结果一致。

---

## 15. 国家名生成（A14）

不用 A/B/C。音节表随机组合，同 seed 可复现，不重复：
```
PREFIXES = ["Val","Kan","Est","Mor","Ath","Bel","Cor","Dun","Fen","Gor",
            "Hal","Ith","Jor","Kel","Lor","Mar","Nor","Ond","Pel","Quor",
            "Riv","Sar","Tor","Ulv","Vor","Wen","Xan","Yor","Zan","Thal"]   # 30 个
SUFFIXES = ["ia","or","mark","land","gard","helm","dor","heim","stad",
            "burg","ton","wick","vale","mere","crest","fall","hold","reach",
            "shire","wyn"]                                                   # 20 个
国家名 = PREFIXES[rng] + SUFFIXES[rng]，查重，冲突则重抽。
省份名 = "<国家名>-P<数字>"
```

---

## 16. 风险与对策（A15）

| # | 风险 | 对策 |
|---|---|---|
| 1 | **阶级流动失控**（一年内农民全变工人） | 所有流动设最大速率上限（3%/1%/0.5%/…）；触发强度 clamp 到 [0,1]；`migration ≤ 源职业 50%`；高税抑制向上流动。 |
| 2 | **经济发散**（正反馈膨胀/崩溃） | 建造受岗位、煤、国库三重约束；`new_factories` 每年设上限；wealth/GDP/price 全程 clamp；treasury 允许负但不无限累积。 |
| 3 | **结局趋同**（最后全民主化） | 压制型目标（agrarian/theocracy/isolationist）让压力持续累积、stability 快速衰减，制造"改革 or 崩溃"分岔；`diffuse_resist` 差异化技术。 |
| 4 | **农民起义过猛**（每次都触发） | 触发需 agitation>0.85 且 influence>0.35 双条件；起义后 agitation 部分重置 + rural_folk 影响力永久下降，避免连环触发；概率分支分散结局。 |
| 5 | **技术扩散同质化** | 扩散量 ∝ (最高tech - 本国tech)，差距缩小则扩散衰减；`diffuse_resist` 高者长期落后；邻接限制避免全员同步。 |
| 6 | 除零 / 负人口 | 小职业设最小人数下限；`log`/`min` 用 `max(x, ε)`；比例迁移后 clamp ≥ 0。 |
| 7 | IG 影响力分母为 0 | 初始化保证所有 IG 至少有 1 个成员（servicemen/clergymen/bureaucrats 初始>0）；若某 IG 成员趋 0，影响力记 0 不参与归一化分母。 |
| 8 | 可复现性被破坏 | 禁用全局 `np.random`/`random`，统一派生 RNG；代码评审重点检查随机调用点。 |
| 9 | 改革压力震荡（制度反复横跳） | 制度改革设冷却期（如制度变化后 N 年内不再变）；倒退需压力持续 < -0.3。 |
| 10 | 量纲混乱 | 人口/财富/产值/国库单位在 config 注释统一声明，调参前先看量纲表。 |

---

## 17. 已确认决策（Q1~Q7）

- **Q1（size 类型）**：内部用 float，报告 round 成 int；迁移时某职业剩余人数 < 1 则累积到下回合，不归零。
- **Q2（servicemen）**：随 `military_spending` 从 lower 阶层招募（≤0.5%/年）；规模约束 上限 ≤ total_pop×0.05、下限 ≥ total_pop×0.01（财政危机 treasury<0 可突破）。
- **Q3（地租压迫阈值）**：相对判定，`aristocrats 抽走地租 / peasants 税前收入 > 0.35`。
- **Q4（世界市场基准）**：用首年全球（各类）总产出作基准。
- **Q5（邻接）**：环形邻接，国 N-1 与国 0 相邻。
- **Q6（市场粒度）**：分农/矿/工三类独立定价，基础价 工业 > 矿 > 农（剪刀差）。
- **Q7（tech 初值）**：`tech_level = 0.1`，新增 `--initial-tech` 命令行参数。

---

## 18. 阶段 B 实现计划（确认后执行）

### 18.1 技术栈（B1）
Python 3.10+；仅 numpy + pandas；dataclass；类型注解；中文注释；argparse；`numpy.random.default_rng(seed)`。禁止 matplotlib/pygame/UI/LLM/Web。

### 18.2 文件结构（B2）
见 §1（`historia/sim/*` + `scripts/*` + `main.py` + `output/`）。

### 18.3 实现顺序（B6）
```
1  config.py + models/pop/province/nation/interest_group 数据结构
2  names.py
3  economy.py
4  politics.py（含 IG 影响力计算）
5  阶级流动 update_pop_promotion
6  农民起义 check_peasant_uprising
7  ai.py + goals.py
8  events.py
9  simulate.py
10 report.py
11 scripts/run_sim.py + run_world.py
12 README.md
```

### 18.4 冒烟测试（B4）
实现完成后仅跑：
```
python scripts/run_sim.py --goal reform --years 10
python scripts/run_world.py --nations 3 --years 10
```
确认不崩溃、输出文件生成。**不自行跑 50 年完整验证、不自行判断数据合理性**（交给用户）。

### 18.5 提交策略（B7，中文提交信息，不 push）
```
chore: 初始化 historia 项目结构 → docs: 补充设计文档 → feat: 实现数据结构
→ feat: 实现国家名生成 → feat: 实现经济结算 → feat: 实现政治结算与利益集团
→ feat: 实现阶级流动 → feat: 实现农民起义机制 → feat: 实现 AI 决策与目标库
→ feat: 实现关键事件检测 → feat: 实现年度推演 → feat: 实现单国入口与参数化
→ feat: 实现多国世界模拟 → docs: 补充 README 与使用说明
```

---

## 19. 实现时决策（阶段 B 中自行拍板的默认值）

> 实现过程中如遇文档未明确之处，采用合理默认值并在本节记录，不中断提问。

- （待实现过程中逐条补充）






