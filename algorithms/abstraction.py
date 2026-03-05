# Copyright 2025 Poker AI Project. 6-max 信息抽象与行动抽象定义。
"""
与 docs/ABSTRACTION_6MAX.md 对应：下注尺度桶、手牌/公共牌聚类接口。
供 CFR 子游戏、策略表与 6-max 环境对接使用。
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

# ---------- 行动抽象：Postflop 下注尺度（占 pot 比例） ----------
# 非 all-in 的 bet/raise 按占 pot 比例落入以下桶
BET_POT_RATIOS: Tuple[float, ...] = (0.25, 0.33, 0.5, 0.75, 1.0, 1.5)
BET_BUCKET_NAMES: Tuple[str, ...] = (
    "25%",
    "33%",
    "50%",
    "75%",
    "100%",
    "150%",
)
ALL_IN_BUCKET = "all_in"
CHECK_OR_CALL_BUCKET = "check_or_call"
FOLD_BUCKET = "fold"


def bet_size_to_bucket(
    pot: float,
    bet_amount: float,
    is_all_in: bool,
) -> str:
    """
    将实际下注额映射到抽象桶名。
    Args:
        pot: 当前底池大小（下注前）。
        bet_amount: 本动作的下注/加注总额（相对于当前 pot 的增量部分，或总 bet）。
        is_all_in: 是否全下。
    Returns:
        桶名：ALL_IN_BUCKET, CHECK_OR_CALL_BUCKET, 或 "25%"～"150%"。
    """
    if is_all_in:
        return ALL_IN_BUCKET
    if pot <= 0:
        return CHECK_OR_CALL_BUCKET
    ratio = bet_amount / pot
    if ratio <= 0:
        return CHECK_OR_CALL_BUCKET
    best = CHECK_OR_CALL_BUCKET
    best_diff = float("inf")
    for i, r in enumerate(BET_POT_RATIOS):
        diff = abs(ratio - r)
        if diff < best_diff:
            best_diff = diff
            best = BET_BUCKET_NAMES[i]
    return best


def bucket_to_approx_ratio(bucket_name: str) -> float | None:
    """
    抽象桶名 -> 近似 pot 比例（用于将策略反映射到具体金额）。
    """
    if bucket_name == ALL_IN_BUCKET:
        return None  # 由 stack 决定
    if bucket_name == CHECK_OR_CALL_BUCKET or bucket_name == FOLD_BUCKET:
        return 0.0
    try:
        idx = BET_BUCKET_NAMES.index(bucket_name)
        return BET_POT_RATIOS[idx]
    except ValueError:
        return None


# ---------- 信息抽象：Preflop 手牌桶（简化 169 类） ----------
# 仅作示例：实际可替换为 E[HS] 聚类或更细划分
PREFLOP_HAND_BUCKETS = (
    "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
    "AKs", "AKo", "AQs", "AQo", "AJs", "AJo", "ATs", "ATo", "A9s", "A9o", "A8s", "A8o", "A7s", "A7o", "A6s", "A5s", "A4s", "A3s", "A2s",
    "KQs", "KQo", "KJs", "KJo", "KTs", "KTo", "K9s", "K9o", "K8s", "K7s", "K6s", "K5s", "K4s", "K3s", "K2s",
    "QJs", "QJo", "QTs", "QTo", "Q9s", "Q9o", "Q8s", "Q7s", "Q6s", "Q5s", "Q4s", "Q3s", "Q2s",
    "JTs", "JTo", "J9s", "J9o", "J8s", "J7s", "J6s", "J5s", "J4s", "J3s", "J2s",
    "T9s", "T9o", "T8s", "T8o", "T7s", "T6s", "T5s", "T4s", "T3s", "T2s",
    "98s", "98o", "97s", "96s", "95s", "94s", "93s", "92s",
    "87s", "86s", "85s", "84s", "83s", "82s",
    "76s", "75s", "74s", "73s", "72s",
    "65s", "64s", "63s", "62s",
    "54s", "53s", "52s",
    "43s", "42s",
    "32s",
)


# 牌面字符 -> 点数（A=14, K=13, ..., 2=2），用于排序
_RANK_ORDER = {"A": 14, "K": 13, "Q": 12, "J": 11, "T": 10}
for _r in "98765432":
    _RANK_ORDER[_r] = int(_r)


def _parse_hole_cards(hole_cards_str: str) -> List[Tuple[str, str]]:
    """解析 'AsKh' 或 'As Kh' 为 [(rank, suit), ...]，每张牌 rank+suit 两字符。"""
    s = (hole_cards_str or "").replace(" ", "").strip()
    if len(s) < 4:
        return []
    out = []
    i = 0
    while i + 2 <= len(s):
        r, suit = s[i], s[i + 1]
        if r in _RANK_ORDER and suit in "shdc":
            out.append((r, suit))
        i += 2
    return out[:2]


def hand_to_preflop_bucket(hole_cards_str: str) -> str:
    """
    将手牌字符串映射到 preflop 桶名（169 类）。
    输入如 'AsKh'（两张牌，rank+suit）。返回 PREFLOP_HAND_BUCKETS 中的桶名。
    """
    cards = _parse_hole_cards(hole_cards_str)
    if len(cards) != 2:
        return "22"
    (r1, s1), (r2, s2) = cards
    v1, v2 = _RANK_ORDER.get(r1, 0), _RANK_ORDER.get(r2, 0)
    high_r, low_r = (r1, r2) if v1 >= v2 else (r2, r1)
    suited = s1 == s2
    if high_r == low_r:
        name = f"{high_r}{low_r}"
    else:
        name = f"{high_r}{low_r}{'s' if suited else 'o'}"
    return name if name in PREFLOP_HAND_BUCKETS else "22"


# ---------- 公共牌抽象 ----------
def board_to_flop_bucket(board_cards_str: str) -> str:
    """
    将 flop 三张牌面映射到 board 桶（同花性）。
    输入如 'AsKhQd'（至少三张）。返回 'rainbow' | 'twotone' | 'monotone'。
    """
    s = (board_cards_str or "").replace(" ", "").strip()
    if len(s) < 6:
        return "rainbow"
    suits = []
    i = 1
    while i < len(s):
        suits.append(s[i])
        i += 2
    if len(suits) < 3:
        return "rainbow"
    suits = suits[:3]
    n_suits = len(set(suits))
    if n_suits == 1:
        return "monotone"
    if n_suits == 2:
        return "twotone"
    return "rainbow"


def get_abstract_state_key(
    street: str,
    hand_bucket: str,
    board_bucket: str,
    action_sequence: List[str],
) -> str:
    """
    生成抽象状态键，供策略表或网络查询。
    street: "preflop" | "flop" | "turn" | "river"
    action_sequence: 本手牌到当前决策点为止的抽象动作序列（如 ["open_2.5", "call"]）。
    """
    actions = "_".join(action_sequence) if action_sequence else "none"
    return f"{street}_{hand_bucket}_{board_bucket}_{actions}"


def get_abstract_state_key_from_env(env: Any, action_sequence: Optional[List[str]] = None) -> str:
    """
    从 6-max 环境当前状态生成抽象状态键。
    env 需提供：get_current_street_name(), current_player(), get_hole_cards_str(player), get_board_cards_str()。
    action_sequence 未提供时用 []（子游戏内可后续由历史追踪补齐）。
    """
    street = env.get_current_street_name()
    cur = env.current_player()
    hole = env.get_hole_cards_str(cur)
    board = env.get_board_cards_str()
    hand_bucket = hand_to_preflop_bucket(hole)
    board_bucket = "none" if street == "preflop" else board_to_flop_bucket(board)
    return get_abstract_state_key(
        street, hand_bucket, board_bucket, action_sequence or []
    )
