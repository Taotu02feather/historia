"""models.py — 核心数据结构（dataclass）。

字段定义与 docs/design.md §2 对齐。所有字段均为模块间接口。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ============ 8 职业 ============
PROFESSIONS: List[str] = [
    "peasants", "laborers", "servicemen", "clerks",
    "clergymen", "bureaucrats", "aristocrats", "capitalists",
]

# 职业 → 阶层
STRATA: Dict[str, str] = {
    "peasants": "lower", "laborers": "lower", "servicemen": "lower",
    "clerks": "middle", "clergymen": "middle", "bureaucrats": "middle",
    "aristocrats": "upper", "capitalists": "upper",
}

# 职业 → 所属利益集团
PROFESSION_IG: Dict[str, str] = {
    "peasants": "rural_folk",
    "laborers": "trade_unions",
    "servicemen": "military",
    "clerks": "intelligentsia",
    "clergymen": "church",
    "bureaucrats": "intelligentsia",
    "aristocrats": "landowners",
    "capitalists": "industrialists",
}

# ============ 7 个利益集团 ============
IG_IDS: List[str] = [
    "rural_folk", "trade_unions", "intelligentsia",
    "landowners", "church", "industrialists", "military",
]

IG_NAMES: Dict[str, str] = {
    "rural_folk": "乡村民众", "trade_unions": "工会",
    "intelligentsia": "知识分子", "landowners": "地主贵族",
    "church": "教会", "industrialists": "工业家", "military": "军方",
}

# ============ 政治制度 ============
SYSTEM_ORDER: List[str] = [
    "absolute_monarchy", "constitutional_monarchy", "republic", "democracy",
]
SOCIALIST_REPUBLIC: str = "socialist_republic"
THEOCRACY: str = "theocracy"

# 执政联盟（制度 → 执政 IG 集合）
GOVERNMENT_COALITION: Dict[str, List[str]] = {
    "absolute_monarchy": ["landowners", "church", "military"],
    "constitutional_monarchy": [
        "landowners", "church", "military", "industrialists", "intelligentsia",
    ],
    "republic": list(IG_IDS),
    "democracy": list(IG_IDS),
    "theocracy": ["church"],
    "socialist_republic": ["trade_unions", "intelligentsia"],
}


@dataclass
class Pop:
    """单个人口阶级。size 为 float（内部），报告时 round 成 int。"""

    profession: str
    strata: str
    size: float
    wealth: float
    political_awareness: float = 0.1
    satisfaction: float = 0.6
    ig_membership: Optional[str] = None

    def __post_init__(self) -> None:
        # 自动填充所属利益集团（可由 profession 唯一决定）
        if self.ig_membership is None:
            self.ig_membership = PROFESSION_IG.get(self.profession)


@dataclass
class Province:
    id: int
    name: str
    land_quality: float
    coal_deposit: float
    factories: int = 0
    farms: int = 0
    mines: int = 0
    pops: List[Pop] = field(default_factory=list)


@dataclass
class InterestGroup:
    id: str
    name: str
    member_professions: List[str] = field(default_factory=list)
    influence: float = 0.0
    stance_on_reform: float = 0.0
    in_government: bool = False
    agitation: float = 0.0


@dataclass
class Nation:
    id: int
    name: str
    provinces: List[Province] = field(default_factory=list)
    treasury: float = 0.0
    tax_rate: float = 0.2
    stability: float = 0.6
    reform_level: float = 0.0
    reform_pressure: float = 0.0
    political_system: str = "absolute_monarchy"
    goal: str = "reform"
    tech_level: float = 0.1
    interest_groups: Dict[str, InterestGroup] = field(default_factory=dict)
    gdp: float = 0.0
    gdp_history: List[float] = field(default_factory=list)
    reform_cooldown: int = 0
    neg_profit_years: int = 0
    suppressed: bool = False
