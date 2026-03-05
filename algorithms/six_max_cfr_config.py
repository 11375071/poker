# Copyright 2025 Poker AI Project. 6-max 子游戏 CFR 约束与抽象配置。
"""
约束：
- 采用 GTO 开池范围表（固定开池尺度）
- Flop/Turn 不 3-bet（面对下注只能 fold/call）
- River 3-bet 仅 all-in
- 每条街下注/raise 最多 3 个尺度
"""
from __future__ import annotations

from typing import List, Tuple

# ---------- 子游戏范围 ----------
# 从 BTN open + BB call 后的 flop 开始
SUBGAME_START_STREET = "flop"
PLAYER_BTN = 0
PLAYER_BB = 1

# ---------- 每条街最多 3 个下注尺度（占 pot 比例） ----------
BET_RATIOS_3: Tuple[float, ...] = (0.33, 0.75, 1.5)
BET_NAMES_3: Tuple[str, ...] = ("33%", "75%", "150%")

# ---------- 公共牌抽象：3 桶（与 abstraction.py 一致） ----------
BOARD_BUCKETS: Tuple[str, ...] = ("rainbow", "twotone", "monotone")

# ---------- 行动名（与现有 JSON 桶名兼容） ----------
CHECK_OR_CALL = "check_or_call"
FOLD = "fold"
ALL_IN_BUCKET = "all_in"

# 子游戏内抽象动作：check, 三个 bet 桶, fold, call, river 的 raise_allin
ACTIONS_FIRST_TO_ACT: List[str] = [CHECK_OR_CALL, BET_NAMES_3[0], BET_NAMES_3[1], BET_NAMES_3[2]]
ACTIONS_FACING_BET_FLOP_TURN: List[str] = [FOLD, CHECK_OR_CALL]  # call -> check_or_call
ACTIONS_FACING_BET_RIVER: List[str] = [FOLD, CHECK_OR_CALL, ALL_IN_BUCKET]

# ---------- 收敛与性能 ----------
DEFAULT_MAX_ITERATIONS = 200_000
DEFAULT_PRINT_INTERVAL = 10_000
# 手牌桶：训练时可用 169 或合并为更少以加速（见 six_max_subgame.py 的 REDUCED_HAND_BUCKETS）
USE_REDUCED_HAND_BUCKETS = True
REDUCED_BUCKET_COUNT = 50
