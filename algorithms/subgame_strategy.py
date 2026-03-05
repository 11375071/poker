# Copyright 2025 Poker AI Project. 子游戏策略与 6-max 环境对接。
"""
将子游戏 CFR/求解器产出的策略在 6-max 中使用：
- 根据当前状态得到抽象状态键（见 abstraction.py）
- 查询策略得到抽象动作上的分布
- 将抽象动作映射回 env.legal_actions() 中的具体动作（含非标准尺度插值/舍入）
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import abstraction


class AbstractStrategyLookup:
    """
    抽象策略查询接口：给定抽象状态键，返回抽象动作上的概率分布。
    实现可从 JSON/网络/子游戏 CFR 结果加载。
    """

    def action_probabilities(self, abstract_state_key: str) -> Dict[str, float]:
        """
        返回 {抽象动作名: 概率}，例如 {"check_or_call": 0.7, "50%": 0.3}。
        若未知状态，返回空 dict 或均匀分布（由实现决定）。
        """
        raise NotImplementedError


class UniformAbstractStrategy(AbstractStrategyLookup):
    """占位：对所有抽象状态返回均匀分布 over 常用桶。"""

    def __init__(self, buckets: Optional[List[str]] = None):
        self._buckets = buckets or [
            abstraction.CHECK_OR_CALL_BUCKET,
            abstraction.BET_BUCKET_NAMES[0],
            abstraction.BET_BUCKET_NAMES[1],
            abstraction.BET_BUCKET_NAMES[2],
        ]

    def action_probabilities(self, abstract_state_key: str) -> Dict[str, float]:
        n = len(self._buckets)
        return {b: 1.0 / n for b in self._buckets}


class JsonAbstractStrategyLookup(AbstractStrategyLookup):
    """
    从 JSON 文件加载的抽象策略。
    JSON 格式：{ "abstract_state_key": { "bucket_name": probability, ... }, ... }
    未知键使用 fallback（默认 UniformAbstractStrategy）返回。
    """

    def __init__(self, path: str | Path, fallback: Optional[AbstractStrategyLookup] = None):
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            self._data = json.load(f)
        self._fallback = fallback or UniformAbstractStrategy()

    def action_probabilities(self, abstract_state_key: str) -> Dict[str, float]:
        probs = self._data.get(abstract_state_key)
        if not isinstance(probs, dict) or not probs:
            probs = self._data.get("default")
        if isinstance(probs, dict) and probs:
            total = sum(probs.values())
            if total > 0:
                return {k: v / total for k, v in probs.items()}
        return self._fallback.action_probabilities(abstract_state_key)


def _action_to_bucket(
    action_id: int,
    action_id_to_info: Dict[int, Dict[str, Any]],
    pot: float,
) -> str:
    """将单个 action_id 映射到抽象桶名。"""
    info = action_id_to_info.get(action_id)
    if not info:
        return abstraction.CHECK_OR_CALL_BUCKET
    t = info.get("type", "")
    if t == "fold":
        return abstraction.FOLD_BUCKET
    if t in ("check", "call"):
        return abstraction.CHECK_OR_CALL_BUCKET
    if t == "all_in":
        return abstraction.ALL_IN_BUCKET
    if t in ("bet", "raise"):
        amount = info.get("amount", 0) or 0
        return abstraction.bet_size_to_bucket(pot, float(amount), is_all_in=False)
    return abstraction.CHECK_OR_CALL_BUCKET


def map_abstract_to_legal(
    abstract_probs: Dict[str, float],
    legal_actions: List[int],
    action_id_to_info: Any,
    pot: float,
    min_raise: float,
    stack: float,
) -> Dict[int, float]:
    """
    将抽象动作上的概率分布映射到 env.legal_actions() 的 action id 上的分布。
    action_id_to_info: 由环境提供的 (action_id -> {type, amount?, total_to_put?}) 映射。
    同一抽象桶内多个合法动作均分该桶的概率；未出现在 abstract_probs 中的桶不分配。
    若映射后总和为 0，则回退为 legal_actions 上均匀分布。
    """
    if not legal_actions:
        return {}
    a2i = action_id_to_info if isinstance(action_id_to_info, dict) else {}
    pot_f = max(0.0, float(pot))

    # action_id -> bucket
    action_to_bucket: Dict[int, str] = {}
    for a in legal_actions:
        action_to_bucket[a] = _action_to_bucket(a, a2i, pot_f)

    # bucket -> list of action_ids
    bucket_to_actions: Dict[str, List[int]] = {}
    for a, b in action_to_bucket.items():
        bucket_to_actions.setdefault(b, []).append(a)

    # 按桶分配概率
    out: Dict[int, float] = {a: 0.0 for a in legal_actions}
    for bucket, prob in abstract_probs.items():
        if prob <= 0:
            continue
        actions_in_bucket = bucket_to_actions.get(bucket)
        if not actions_in_bucket:
            continue
        p_each = prob / len(actions_in_bucket)
        for a in actions_in_bucket:
            out[a] = out.get(a, 0) + p_each

    total = sum(out.values())
    if total <= 0:
        n = len(legal_actions)
        return {a: 1.0 / n for a in legal_actions}
    return {a: out[a] / total for a in legal_actions}
