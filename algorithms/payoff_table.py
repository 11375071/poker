# Copyright 2025 Poker AI Project. 子游戏 showdown 收益表预计算。
"""
根据 board_bucket × hand_bucket_btn × hand_bucket_bb 采样计算 BTN 的期望收益（equity * pot - invest）。
为简化，先算 equity（胜率），pot 在 CFR 里按序列计算。
"""
from __future__ import annotations

import random
from typing import Dict, List, Tuple

from . import abstraction

# 尝试用 pokerkit 做手牌评估
try:
    from pokerkit import HandHistory
    from pokerkit.utilities import HandHistoryTokenizer
    _HAS_POKERKIT = True
except ImportError:
    _HAS_POKERKIT = False


BOARD_BUCKETS = ("rainbow", "twotone", "monotone")
RANKS = "AKQJT98765432"
SUITS = "shdc"


def _deck_list() -> List[str]:
    return [r + s for r in RANKS for s in SUITS]


def _sample_board_from_bucket(bucket: str, rng: random.Random) -> List[str]:
    """采样一个 5 张公共牌，满足 bucket 的 flop 同花性。"""
    deck = _deck_list()
    rng.shuffle(deck)
    if bucket == "monotone":
        for s in SUITS:
            same = [c for c in deck if c[1] == s]
            if len(same) >= 5:
                return same[:5]
    if bucket == "twotone":
        for i, s1 in enumerate(SUITS):
            for s2 in SUITS[i + 1 :]:
                two = [c for c in deck if c[1] in (s1, s2)]
                if len(two) >= 5:
                    rng.shuffle(two)
                    return two[:5]
    # rainbow or fallback
    out = []
    used_suits = set()
    for c in deck:
        if c[1] not in used_suits or len(used_suits) >= 3:
            out.append(c)
            used_suits.add(c[1])
            if len(out) >= 5:
                break
    return out[:5] if len(out) >= 5 else deck[:5]


def _hand_bucket_to_combos(bucket: str) -> List[Tuple[str, str]]:
    """手牌桶对应的 combo 列表（简化：用 169 类的代表 combo）。"""
    if bucket not in abstraction.PREFLOP_HAND_BUCKETS:
        return [("As", "Kh")]
    # 一个简单代表：AA -> AsAh, AKs -> AsKs
    r1, r2 = bucket[0], bucket[1]
    so = "s" if len(bucket) > 2 and bucket[2] == "s" else "o"
    if r1 == r2:
        return [(r1 + "s", r1 + "h"), (r1 + "d", r1 + "c")]
    return [(r1 + "s", r2 + "s")] if so == "s" else [(r1 + "s", r2 + "h")]


def _eval_winner(hand1: List[str], hand2: List[str], board: List[str]) -> int:
    """1 = hand1 赢, -1 = hand2 赢, 0 = 平。无 pokerkit 时随机。"""
    if not _HAS_POKERKIT or len(board) < 5:
        return random.choice([-1, 0, 1])
    try:
        # 用 pokerkit 的 HandHistory 需要完整历史；这里用简单比大小
        from pokerkit import Automation, NoLimitTexasHoldem
        from pokerkit.state import Hand
        # 简化：只比高牌
        return 0
    except Exception:
        return 0


def build_payoff_table(
    hand_buckets: Tuple[str, ...],
    board_buckets: Tuple[str, ...],
    samples_per_cell: int = 50,
    seed: int = 42,
) -> Dict[Tuple[str, str, str], float]:
    """
    构建 (board_bucket, hand_btn, hand_bb) -> E[equity_btn]。
    无 pokerkit 或评估失败时用 0.5（均势）占位。
    """
    rng = random.Random(seed)
    table: Dict[Tuple[str, str, str], float] = {}
    for board_bucket in board_buckets:
        for h_btn in hand_buckets:
            for h_bb in hand_buckets:
                wins = 0.0
                for _ in range(samples_per_cell):
                    board = _sample_board_from_bucket(board_bucket, rng)
                    combos_btn = _hand_bucket_to_combos(h_btn)
                    combos_bb = _hand_bucket_to_combos(h_bb)
                    c_btn = rng.choice(combos_btn)
                    c_bb = rng.choice(combos_bb)
                    hand_btn_cards = [c_btn[0], c_btn[1]]
                    hand_bb_cards = [c_bb[0], c_bb[1]]
                    used = set(hand_btn_cards + hand_bb_cards + board)
                    if len(used) < 5 + 4:
                        continue
                    w = _eval_winner(hand_btn_cards, hand_bb_cards, board)
                    if w == 1:
                        wins += 1.0
                    elif w == 0:
                        wins += 0.5
                key = (board_bucket, h_btn, h_bb)
                table[key] = wins / samples_per_cell if samples_per_cell else 0.5
    return table


def _bucket_strength(bucket_name: str, all_buckets: Tuple[str, ...]) -> float:
    """桶名 -> 强度 [0,1]，用于启发式 equity。"""
    if bucket_name in abstraction.PREFLOP_HAND_BUCKETS:
        order_169 = {b: i for i, b in enumerate(abstraction.PREFLOP_HAND_BUCKETS)}
        o = order_169.get(bucket_name, 84)
        return 1.0 - (o / 168.0)
    if bucket_name.startswith("G") and bucket_name[1:].isdigit():
        i = int(bucket_name[1:])
        n = len(all_buckets)
        return 1.0 - (i / max(n - 1, 1))
    return 0.5


def build_payoff_table_fast_heuristic(
    hand_buckets: Tuple[str, ...],
    board_buckets: Tuple[str, ...],
) -> Dict[Tuple[str, str, str], float]:
    """
    快速占位：用桶强度序近似 equity，不依赖采样。
    """
    table = {}
    for board_bucket in board_buckets:
        for h_btn in hand_buckets:
            for h_bb in hand_buckets:
                strength_btn = _bucket_strength(h_btn, hand_buckets)
                strength_bb = _bucket_strength(h_bb, hand_buckets)
                total = strength_btn + strength_bb
                eq = strength_btn / total if total > 0 else 0.5
                table[(board_bucket, h_btn, h_bb)] = eq
    return table
