"""config.py — 默认参数与全部公式系数。

所有规模参数均可从命令行覆盖（见 scripts/run_sim.py 与 run_world.py）。
本文件只存默认值，禁止在别处硬编码魔法数字。

量纲约定（调参前务必先读）：
- 人口 size：抽象单位「千人」，内部用 float 存储
- 财富 wealth：人均产值单位
- 产出 Agri / Mine / Indu：产值单位
- 国库 treasury：产值单位
- stability / satisfaction / political_awareness / influence / agitation：0~1
- 技术水平 tech_level：0~1
"""

from dataclasses import dataclass, field


@dataclass
class Config:
    # ============ 运行参数（可被 CLI 覆盖） ============
    goal: str = "reform"               # 单国目标 key
    years: int = 50                    # 模拟年数
    provinces: int = 8                 # 单国省份数
    seed: int = 42                     # 随机种子
    tax_rate: float = 0.20             # 初始税率
    treasury: float = 10000.0          # 初始国库
    initial_pop: int = 1000            # 每省初始总人口（千人）
    initial_tech: float = 0.1          # 初始技术水平
    nations: int = 6                   # 多国国家数
    provinces_per_nation: int = 4      # 多国每国省份数
    goal_mode: str = "random"          # random | cycle | explicit
    goals: list = field(default_factory=list)   # 显式目标列表
    outdir: str = "output"             # 输出目录

    # ============ 经济 ============
    AGR_BASE: float = 12.0             # 每农场基础农业产值
    MINE_BASE: float = 9.0             # 每矿场基础矿业产值
    IND_BASE: float = 6.0              # 每工厂基础工业产值
    TECH_GAIN: float = 2.0             # 工业产出技术加成系数
    FARM_CAP: float = 100.0            # 每农场可容纳农民（千人）
    MINE_CAP: float = 100.0            # 每矿场可容纳劳工
    FACT_CAP: float = 100.0            # 每工厂可容纳劳工
    CLERK_EFF: float = 1.5             # 职员劳动效率倍数
    RENT_RATE: float = 0.30            # 地租率（农业产出 30% 归贵族）
    COAL_FACTOR: float = 0.5           # 煤供给对工业的加成强度
    ADMIN_COEF: float = 0.05           # 行政维持费系数

    # ============ 世界市场 ============
    PRICE_FARM: float = 1.0            # 农产品基础价
    PRICE_MINE: float = 1.5            # 矿产品基础价
    PRICE_FACTORY: float = 2.5         # 工业品基础价（最高，剪刀差）
    PRICE_MIN: float = 0.3
    PRICE_MAX: float = 3.0
    PRICE_RESPONSE: float = 0.5        # 价格对供需的响应系数

    # ============ 满意度 ============
    SAT_BASE: float = 0.6
    SAT_WEALTH: float = 0.15
    SAT_TAX: float = 0.4
    SAT_WELFARE: float = 0.8
    SAT_CLERGY: float = 0.3
    REF_WEALTH: dict = field(default_factory=lambda: {
        "peasants": 10.0, "laborers": 12.0, "servicemen": 11.0,
        "clerks": 15.0, "clergymen": 13.0, "bureaucrats": 14.0,
        "aristocrats": 40.0, "capitalists": 50.0,
    })

    # ============ 人口增长 ============
    GROWTH_BASE: float = 0.01
    GROWTH_MIN: float = -0.03
    GROWTH_MAX: float = 0.04

    # ============ 政治意识 ============
    AW_SPEED: float = 1.0              # 意识增长整体速率
    AW_INDUSTRY: float = 0.02          # 工业化对意识的提升
    AW_INEQUALITY: float = 0.01        # 贫富差距对意识的提升
    AW_REFORM: float = 0.02            # 已有改革释放意识
    AW_EDUCATION: float = 0.02         # 技术/教育对意识的提升
    AW_BASE: dict = field(default_factory=lambda: {
        "laborers": 0.025, "clerks": 0.015, "peasants": 0.005,
        "servicemen": 0.002, "aristocrats": 0.001, "clergymen": 0.001,
        "bureaucrats": 0.003, "capitalists": 0.010,
    })
    CLERGY_SUPPRESS: float = 2.0       # 思想控制系数

    # ============ 稳定性 / 军人 ============
    STAB_BASE: float = 0.6
    STAB_SAT: float = 0.5
    STAB_PRESS: float = 0.4
    STAB_TAX: float = 0.4
    STAB_IG: float = 0.05
    STAB_CLERGY: float = 0.1
    STAB_FLOOR_SERVICEMEN: float = 0.3 # servicemen 达 5% 时的稳定下限
    SERVICEMEN_CAP_RATIO: float = 0.05 # 军人规模上限
    SERVICEMEN_MIN_RATIO: float = 0.01 # 军人规模下限

    # ============ 改革 ============
    REFORM_THRESH: float = 0.6         # 启动制度改革
    REGRESS_THRESH: float = -0.3       # 可能倒退
    REFORM_COOLDOWN: int = 3           # 制度改革冷却年数
    REFORM_STEP: float = 0.25          # reform_level 每步增幅
    CHURCH_THEOCRACY: float = 0.5      # church 影响力 > 此值可退化为 theocracy

    # ============ 阶级流动 ============
    PROV_BUILDING_REF: float = 4.0     # 触发强度参考建筑数
    MAX_P2L: float = 0.03              # peasants→laborers 最大速率
    MAX_L2C: float = 0.01              # laborers→clerks
    MAX_P2C: float = 0.005             # peasants→clerks
    MAX_2CAP: float = 0.001            # laborers/clerks→capitalists
    MAX_L2P: float = 0.02              # laborers→peasants
    MAX_C2L: float = 0.01              # clerks→laborers
    MAX_CAP2C: float = 0.0005          # capitalists→clerks
    UP_TAX_PENALTY: float = 1.0        # 高税抑制向上流动系数
    WEALTH_CAPITALIST: float = 80.0    # 晋升资本家财富阈值
    NEG_PROFIT_YEARS: int = 3          # 资本家连续负利润年数（家败）
    MIG_CAP: float = 0.5               # 单次迁移不超过源职业比例
    SERVICEMEN_RECRUIT: float = 0.005  # 军人年招募速率（最大）

    # ============ 技术 ============
    TECH_SPEED: float = 0.01
    DIFFUSE_RATE: float = 0.1          # 邻接扩散系数
    BASE_DIFFUSE_PROB: float = 0.03    # 基础扩散概率
    BASE_DIFFUSE_STEP: float = 0.01    # 基础扩散步长

    # ============ AI ============
    TAX_MIN: float = 0.05
    TAX_MAX: float = 0.60
    AI_REFORM_PUSH: float = 0.05       # 改革立场对改革压力的推动系数
    BUILD_COST_FARM: float = 300.0
    BUILD_COST_MINE: float = 500.0
    BUILD_COST_FACTORY: float = 800.0
    MAX_NEW_BUILD: int = 5             # 每年建造总数上限
    AGITATE_BENEFIT: float = 0.02      # 决策受益 IG 躁动下降
    AGITATE_HARM: float = 0.03         # 决策受损 IG 躁动上升
    AGITATE_OPPOSITION: float = 0.05   # 在野 IG 每年躁动增长
    AGITATE_CRISIS: float = 0.7        # 躁动危机阈值
    IG_DOMINANT: float = 0.35          # 主导影响力阈值

    # ============ 农民起义 ============
    UPRISING_AGITATION: float = 0.85
    UPRISING_INFLUENCE: float = 0.35
    UPRISING_STAB_HIT: float = 0.3
    UPRISING_AGITATE_SPREAD: float = 0.1
    UPRISING_RF_DECLINE: float = 0.7   # 起义后 rural_folk 影响力保留比例
