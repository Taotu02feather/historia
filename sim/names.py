"""names.py — 国家名音节随机生成。

同 seed 可复现，国家名不重复。省份名 = "<国家名>-P<数字>"。
"""

from typing import List

import numpy as np

# 30 个前缀
PREFIXES: List[str] = [
    "Val", "Kan", "Est", "Mor", "Ath", "Bel", "Cor", "Dun", "Fen", "Gor",
    "Hal", "Ith", "Jor", "Kel", "Lor", "Mar", "Nor", "Ond", "Pel", "Quor",
    "Riv", "Sar", "Tor", "Ulv", "Vor", "Wen", "Xan", "Yor", "Zan", "Thal",
]

# 20 个后缀
SUFFIXES: List[str] = [
    "ia", "or", "mark", "land", "gard", "helm", "dor", "heim", "stad",
    "burg", "ton", "wick", "vale", "mere", "crest", "fall", "hold", "reach",
    "shire", "wyn",
]


def generate_nation_names(rng: np.random.Generator, count: int) -> List[str]:
    """生成 count 个不重复的国家名。"""
    names: List[str] = []
    seen = set()
    while len(names) < count:
        prefix = PREFIXES[int(rng.integers(0, len(PREFIXES)))]
        suffix = SUFFIXES[int(rng.integers(0, len(SUFFIXES)))]
        name = prefix + suffix
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def province_name(nation_name: str, index: int) -> str:
    """省份名 = "<国家名>-P<数字>"（index 从 1 开始）。"""
    return f"{nation_name}-P{index}"
