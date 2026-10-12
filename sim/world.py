"""world.py — 多国世界：世界市场定价（三类独立）+ 技术扩散（环形邻接）。"""

from typing import Dict, List, Optional

import numpy as np

from .config import Config
from .models import Nation


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


class World:
    """多国世界状态：价格、基准产出、技术扩散。"""

    def __init__(self, nations: List[Nation], cfg: Config,
                 rng: np.random.Generator) -> None:
        self.nations = nations
        self.cfg = cfg
        self.rng = rng
        self.base_outputs: Optional[tuple] = None
        self.prices = {"farm": cfg.PRICE_FARM, "mine": cfg.PRICE_MINE,
                       "factory": cfg.PRICE_FACTORY}
        self.last_outputs: Dict[int, tuple] = {}

    def compute_prices(self, nations: List[Nation], outputs: Dict[int, tuple],
                       cfg: Config) -> Dict[str, float]:
        """三类商品独立定价：price = base × (1 - 全球产出/基准产出 × 0.5)。"""
        g_farm = sum(o[0] for o in outputs.values())
        g_mine = sum(o[1] for o in outputs.values())
        g_factory = sum(o[2] for o in outputs.values())
        if self.base_outputs is None:
            # 首年全球产出作为基准（可复现）
            self.base_outputs = (g_farm, g_mine, g_factory)
        b_farm, b_mine, b_factory = self.base_outputs
        eps = 1e-9
        self.prices = {
            "farm": _clamp(cfg.PRICE_FARM * (1 - cfg.PRICE_RESPONSE * g_farm / max(b_farm, eps)),
                           cfg.PRICE_MIN, cfg.PRICE_MAX),
            "mine": _clamp(cfg.PRICE_MINE * (1 - cfg.PRICE_RESPONSE * g_mine / max(b_mine, eps)),
                           cfg.PRICE_MIN, cfg.PRICE_MAX),
            "factory": _clamp(cfg.PRICE_FACTORY * (1 - cfg.PRICE_RESPONSE * g_factory / max(b_factory, eps)),
                              cfg.PRICE_MIN, cfg.PRICE_MAX),
        }
        self.last_outputs = outputs
        return self.prices

    def diffuse_tech(self, nations: List[Nation], cfg: Config,
                     goal_map: Optional[Dict] = None) -> None:
        """技术扩散：自主研发 + 基础扩散 + 环形邻接扩散。"""
        goal_map = goal_map or {}
        n = len(nations)
        for i, nation in enumerate(nations):
            left = nations[(i - 1) % n]
            right = nations[(i + 1) % n]
            neighbor_max = max(left.tech_level, right.tech_level)
            goal = goal_map.get(nation.goal)
            resist = goal.diffuse_resist if goal else 0.0

            # 邻接扩散
            nation.tech_level += cfg.DIFFUSE_RATE \
                * max(0.0, neighbor_max - nation.tech_level) * (1.0 - resist)
            # 基础扩散（概率）
            if self.rng.random() < cfg.BASE_DIFFUSE_PROB:
                nation.tech_level += cfg.BASE_DIFFUSE_STEP * (1.0 - resist)
            # 自主研发（工业占比越高越快）
            out = self.last_outputs.get(nation.id, (0.0, 0.0, 0.0))
            total = out[0] + out[1] + out[2]
            indu_share = out[2] / max(total, 1e-9)
            tech_bias = goal.tech_bias if goal else 0.1
            nation.tech_level += cfg.TECH_SPEED * tech_bias * (0.5 + 0.5 * indu_share)

            nation.tech_level = _clamp(nation.tech_level, 0.0, 1.0)
