# Copyright 2025 Poker AI Project. BTN vs BB 抽象子游戏（flop→river）与 CFR+。
"""
约束：flop/turn 不 raise（仅 check 或 3 个 bet 尺度，面对 bet 只能 fold/call）；
river 面对 bet 可 fold/call/raise_allin。每条街最多 3 个下注尺度。
状态用 (street, board_bucket, action_sequence)，与 get_abstract_state_key 兼容。
"""
from __future__ import annotations

import itertools
import random
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from . import abstraction
from .six_max_cfr_config import (
    ACTIONS_FACING_BET_FLOP_TURN,
    ACTIONS_FACING_BET_RIVER,
    ACTIONS_FIRST_TO_ACT,
    ALL_IN_BUCKET,
    BET_NAMES_3,
    BOARD_BUCKETS,
    CHECK_OR_CALL,
    FOLD,
    PLAYER_BB,
    PLAYER_BTN,
    REDUCED_BUCKET_COUNT,
    USE_REDUCED_HAND_BUCKETS,
)

# ---------- 手牌桶：训练用 169 或合并为 50 ----------
if USE_REDUCED_HAND_BUCKETS:
    # 将 169 合并为 50：按强度分组
    _REDUCED_MAP: Dict[str, str] = {}
    _all_169 = list(abstraction.PREFLOP_HAND_BUCKETS)
    for i, h in enumerate(_all_169):
        _REDUCED_MAP[h] = f"G{i % REDUCED_BUCKET_COUNT}"
    HAND_BUCKETS_TRAIN = tuple(sorted(set(_REDUCED_MAP.values())))
    # 反向：G -> 属于该 G 的 169 桶列表（导出 JSON 时用）
    _TRAIN_TO_169: Dict[str, List[str]] = {}
    for h169, g in _REDUCED_MAP.items():
        _TRAIN_TO_169.setdefault(g, []).append(h169)
else:
    HAND_BUCKETS_TRAIN = abstraction.PREFLOP_HAND_BUCKETS
    _TRAIN_TO_169 = {h: [h] for h in HAND_BUCKETS_TRAIN}


def hand_bucket_for_cfr(hole_bucket_169: str) -> str:
    """训练用：169 桶映射到 50 桶（若 USE_REDUCED_HAND_BUCKETS）。"""
    if not USE_REDUCED_HAND_BUCKETS:
        return hole_bucket_169
    return _REDUCED_MAP.get(hole_bucket_169, HAND_BUCKETS_TRAIN[0])


# ---------- 子游戏状态解析 ----------
def _street_complete_length(seq: List[str]) -> int:
    """当前序列中「本街」结束需要的动作数。"""
    if not seq:
        return 0
    first = seq[0]
    if first == CHECK_OR_CALL:
        if len(seq) >= 2 and seq[1] == CHECK_OR_CALL:
            return 2
        if len(seq) >= 3 and seq[1] in BET_NAMES_3 and seq[2] == CHECK_OR_CALL:
            return 3
        return 1
    if first in BET_NAMES_3 or first == ALL_IN_BUCKET:
        if len(seq) >= 2:
            return 2
        return 1
    return 1


def _street_starts(action_sequence: List[str]) -> List[int]:
    """返回每街的起始下标 [flop_start, turn_start, river_start, end]. """
    starts = [0]
    i = 0
    for _ in range(3):
        n = _street_complete_length(action_sequence[i:])
        i += n
        starts.append(i)
    return starts


def _actions_this_street(action_sequence: List[str], street: str) -> List[str]:
    """当前街已执行的动作。"""
    streets = ["flop", "turn", "river"]
    if street not in streets:
        return []
    idx = streets.index(street)
    starts = _street_starts(action_sequence)
    if idx + 1 >= len(starts):
        return []
    return action_sequence[starts[idx] : starts[idx + 1]]


def _first_to_act(street: str) -> int:
    """每街先动者：flop/turn/river 均为 BB。"""
    return PLAYER_BB


def _is_facing_bet(actions_this_street: List[str]) -> bool:
    """本街是否「面对下注」（上一动作为 bet）。"""
    if len(actions_this_street) < 1:
        return False
    last = actions_this_street[-1]
    return last in BET_NAMES_3 or last == ALL_IN_BUCKET


def _street_done(action_sequence: List[str], street: str) -> bool:
    """该街是否已结束。"""
    acts = _actions_this_street(action_sequence, street)
    if not acts:
        return False
    n = _street_complete_length(acts)
    return len(acts) >= n


def get_current_player_and_legal(
    street: str, board_bucket: str, action_sequence: List[str]
) -> Tuple[Optional[int], List[str]]:
    """
    返回 (current_player, legal_actions)。
    若已终局返回 (None, [])；若本街已结束需进入下一街则由调用方先推进 street。
    """
    acts = _actions_this_street(action_sequence, street)
    first = _first_to_act(street)
    if not acts:
        return (first, list(ACTIONS_FIRST_TO_ACT))
    if _street_complete_length(acts) > len(acts):
        # 本街未结束
        if _is_facing_bet(acts):
            # 对方刚下注，当前玩家为「先动者」（需回应 bet 的是先动的那位）
            cur = first
            if street == "river":
                return (cur, list(ACTIONS_FACING_BET_RIVER))
            return (cur, list(ACTIONS_FACING_BET_FLOP_TURN))
        else:
            # 当前玩家先动或跟注后新的一动
            n = len(acts)
            if n == 1:
                cur = PLAYER_BTN if first == PLAYER_BB else PLAYER_BB
            else:
                cur = first
            return (cur, list(ACTIONS_FIRST_TO_ACT))
    return (None, [])


def _advance_street(street: str) -> Optional[str]:
    if street == "flop":
        return "turn"
    if street == "turn":
        return "river"
    return None


def is_terminal(street: str, action_sequence: List[str]) -> bool:
    """是否终局：有人 fold 或 river 结束后。"""
    acts_flop = _actions_this_street(action_sequence, "flop")
    acts_turn = _actions_this_street(action_sequence, "turn")
    acts_river = _actions_this_street(action_sequence, "river")
    if FOLD in acts_flop or FOLD in acts_turn or FOLD in acts_river:
        return True
    if street != "river":
        return False
    if not acts_river:
        return False
    return _street_complete_length(acts_river) <= len(acts_river)


def _terminal_fold_winner(action_sequence: List[str]) -> Optional[int]:
    """谁 fold 了则对方赢。返回赢家 player id。"""
    for street in ["flop", "turn", "river"]:
        acts = _actions_this_street(action_sequence, street)
        if FOLD in acts:
            first = _first_to_act(street)
            # 若只有 1 个动作且是 fold，则 first 弃牌 -> 对方赢
            # 若 2 个动作且第二个是 fold，则 second 弃牌
            if len(acts) >= 2 and acts[-1] == FOLD:
                return first  # 后动者 fold，先动者赢
            if len(acts) == 1 and acts[0] == FOLD:
                return PLAYER_BTN if first == PLAYER_BB else PLAYER_BB
    return None


def get_infoset_key(street: str, board_bucket: str, hand_bucket: str, action_sequence: List[str]) -> str:
    """与 get_abstract_state_key 一致。"""
    actions_str = "_".join(action_sequence) if action_sequence else "none"
    return f"{street}_{hand_bucket}_{board_bucket}_{actions_str}"


# ---------- 收益：用预计算的 payoff 表 ----------
def _pot_and_investments(action_sequence: List[str], initial_pot: float = 1.0) -> Tuple[float, float, float]:
    """假设初始 pot=1，按序列累计 pot 与双方投入。返回 (pot, invest_btn, invest_bb)。"""
    pot = initial_pot
    invest_btn, invest_bb = 0.5, 0.5
    streets = ["flop", "turn", "river"]
    for st in streets:
        acts = _actions_this_street(action_sequence, st)
        for i, a in enumerate(acts):
            if a == FOLD:
                break
            if a == CHECK_OR_CALL:
                # call: 补齐到当前 bet
                # 简化：每街第一次 call 表示跟注对方下注，投入 = 对方 bet
                if i == 1 and acts[0] in BET_NAMES_3:
                    bet = pot * {"33%": 0.33, "75%": 0.75, "150%": 1.5}.get(acts[0], 0.5)
                    pot += 2 * bet
                    if _first_to_act(st) == PLAYER_BB:
                        invest_bb += bet
                        invest_btn += bet
                    else:
                        invest_btn += bet
                        invest_bb += bet
                continue
            if a in BET_NAMES_3:
                r = {"33%": 0.33, "75%": 0.75, "150%": 1.5}.get(a, 0.5)
                bet = pot * r
                pot += 2 * bet
                if _first_to_act(st) == PLAYER_BB:
                    invest_bb += bet
                else:
                    invest_btn += bet
                continue
            if a == ALL_IN_BUCKET:
                # river all-in: 用 1.5 pot 近似
                bet = pot * 1.5
                pot += 2 * bet
                invest_btn += bet
                invest_bb += bet
                break
    return (pot, invest_btn, invest_bb)


def terminal_payoff_btn(
    action_sequence: List[str],
    board_bucket: str,
    hand_btn: str,
    hand_bb: str,
    payoff_table: Dict[Tuple[str, str, str], float],
    initial_pot: float = 1.0,
) -> float:
    """BTN 的终局收益（零和，BB 收益 = -payoff_btn）。"""
    winner = _terminal_fold_winner(action_sequence)
    if winner is not None:
        pot, inv_btn, inv_bb = _pot_and_investments(action_sequence, initial_pot)
        if winner == PLAYER_BTN:
            return pot - inv_btn
        return -(pot - inv_bb)
    # showdown
    pot, inv_btn, inv_bb = _pot_and_investments(action_sequence, initial_pot)
    eq_btn = payoff_table.get((board_bucket, hand_btn, hand_bb), 0.5)
    return eq_btn * pot - inv_btn


# ---------- CFR+ 求解 ----------
def _cfr_traverse(
    street: str,
    board_bucket: str,
    action_sequence: List[str],
    hand_btn: str,
    hand_bb: str,
    reach_btn: float,
    reach_bb: float,
    payoff_table: Dict[Tuple[str, str, str], float],
    infoset_regrets: Dict[str, Dict[str, float]],
    infoset_cumulative: Dict[str, Dict[str, float]],
    rng: random.Random,
    is_update: bool,
) -> float:
    """
    一次遍历，返回当前状态对 BTN 的 counterfactual value。
    """
    cur, legal = get_current_player_and_legal(street, board_bucket, action_sequence)
    if cur is None and not legal:
        # 本街结束，进入下一街
        next_street = _advance_street(street)
        if next_street is None:
            return terminal_payoff_btn(
                action_sequence, board_bucket, hand_btn, hand_bb, payoff_table
            )
        return _cfr_traverse(
            next_street, board_bucket, action_sequence,
            hand_btn, hand_bb, reach_btn, reach_bb,
            payoff_table, infoset_regrets, infoset_cumulative, rng, is_update,
        )
    if is_terminal(street, action_sequence):
        return terminal_payoff_btn(
            action_sequence, board_bucket, hand_btn, hand_bb, payoff_table
        )

    hand_cur = hand_btn if cur == PLAYER_BTN else hand_bb
    hand_opp = hand_bb if cur == PLAYER_BTN else hand_btn
    infoset = get_infoset_key(street, board_bucket, hand_cur, action_sequence)
    if infoset not in infoset_regrets:
        infoset_regrets[infoset] = {a: 0.0 for a in legal}
        infoset_cumulative[infoset] = {a: 0.0 for a in legal}

    # 当前策略（CFR+ 用 regret matching+）
    reg = infoset_regrets[infoset]
    strategy = {}
    for a in legal:
        r = max(reg.get(a, 0.0), 0.0)
        strategy[a] = r
    s_sum = sum(strategy.values())
    if s_sum <= 0:
        strategy = {a: 1.0 / len(legal) for a in legal}
    else:
        strategy = {a: strategy[a] / s_sum for a in legal}

    util = 0.0
    action_utils = {}
    for a in legal:
        new_seq = action_sequence + [a]
        if cur == PLAYER_BTN:
            new_reach_btn = reach_btn * strategy[a]
            new_reach_bb = reach_bb
        else:
            new_reach_btn = reach_btn
            new_reach_bb = reach_bb * strategy[a]
        v = _cfr_traverse(
            street, board_bucket, new_seq,
            hand_btn, hand_bb, new_reach_btn, new_reach_bb,
            payoff_table, infoset_regrets, infoset_cumulative, rng, is_update,
        )
        action_utils[a] = v
        util += strategy[a] * v

    if is_update and cur == PLAYER_BTN:
        opp_reach = reach_bb
        for a in legal:
            infoset_regrets[infoset][a] = infoset_regrets[infoset].get(a, 0) + opp_reach * (action_utils[a] - util)
            infoset_cumulative[infoset][a] = infoset_cumulative[infoset].get(a, 0) + reach_btn * strategy[a]
    elif is_update and cur == PLAYER_BB:
        opp_reach = reach_btn
        for a in legal:
            # BB 的 utility 是 -BTN utility
            infoset_regrets[infoset][a] = infoset_regrets[infoset].get(a, 0) + opp_reach * (-action_utils[a] - (-util))
            infoset_cumulative[infoset][a] = infoset_cumulative[infoset].get(a, 0) + reach_bb * strategy[a]

    return util if cur == PLAYER_BTN else -util


def run_cfr_plus(
    payoff_table: Dict[Tuple[str, str, str], float],
    hand_buckets: Tuple[str, ...],
    board_buckets: Tuple[str, ...],
    max_iterations: int,
    print_interval: int,
    rng: Optional[random.Random] = None,
) -> Dict[str, Dict[str, float]]:
    """
    运行 CFR+，返回平均策略：infoset_key -> { action: probability }。
    """
    rng = rng or random.Random(42)
    infoset_regrets: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    infoset_cumulative: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for it in range(max_iterations):
        reach = 1.0 / (len(hand_buckets) * len(hand_buckets) * len(board_buckets))
        for (hand_btn, hand_bb, board_bucket) in itertools.product(
            hand_buckets, hand_buckets, board_buckets
        ):
            _cfr_traverse(
                "flop", board_bucket, [],
                hand_btn, hand_bb, reach, reach,
                payoff_table, infoset_regrets, infoset_cumulative, rng, is_update=True,
            )
        if (it + 1) % print_interval == 0:
            print(f"  CFR+ iter {it + 1}/{max_iterations}")

    # 平均策略
    avg_policy: Dict[str, Dict[str, float]] = {}
    for infoset, cum in infoset_cumulative.items():
        total = sum(cum.values())
        if total > 0:
            avg_policy[infoset] = {a: cum[a] / total for a in cum}
        else:
            legal = list(infoset_regrets.get(infoset, {}).keys())
            avg_policy[infoset] = {a: 1.0 / len(legal) for a in legal} if legal else {}
    return avg_policy


def export_policy_to_169_keys(
    avg_policy: Dict[str, Dict[str, float]],
) -> Dict[str, Dict[str, float]]:
    """
    将训练用的 50 桶 infoset 键展开为 169 桶键，与 get_abstract_state_key 一致，
    供 run_six_max_with_strategy 与 JsonAbstractStrategyLookup 使用。
    """
    out: Dict[str, Dict[str, float]] = {}
    for infoset_key, probs in avg_policy.items():
        parts = infoset_key.split("_", 3)
        if len(parts) < 4:
            out[infoset_key] = probs
            continue
        street, hand_train, board_bucket, rest = parts[0], parts[1], parts[2], parts[3]
        hand_169_list = _TRAIN_TO_169.get(hand_train, [hand_train])
        for h169 in hand_169_list:
            new_key = f"{street}_{h169}_{board_bucket}_{rest}"
            out[new_key] = dict(probs)
    return out
