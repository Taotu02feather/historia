# historia

无头历史模拟沙盒。

## 核心命题

**经济基础决定上层建筑。**

工业化会导致社会结构变化（农民→工人），工人政治意识上升，
进而产生改革压力，最终改变政治制度。

本项目通过多国自主模拟，验证这一命题是否成立。

## 当前状态

- [ ] 数据结构（POP / Province / Nation）
- [ ] 经济结算
- [ ] 政治结算
- [ ] AI 决策（规则版）
- [ ] 年度推演
- [ ] 多国世界模拟
- [ ] 输出 CSV + TXT 报告

## 快速开始

```bash
pip install -r requirements.txt

# 单国快速测试
python scripts/run_sim.py --goal reform

# 多国世界模拟
python scripts/run_world.py