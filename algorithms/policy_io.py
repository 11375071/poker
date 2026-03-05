# Copyright 2025 Poker AI Project. 策略序列化，供 Leduc CFR 等使用。
"""
将 OpenSpiel TabularPolicy 导出为 JSON、从 JSON 加载。
加载时需要相同 game 以重建 state_lookup，故序列化时保存 game 名称与参数。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import pyspiel

# 依赖 OpenSpiel policy（在 venv 中）
from open_spiel.python import policy


def _tabular_policy_to_serializable(tabular_policy: policy.TabularPolicy) -> Dict[str, Any]:
    """将 TabularPolicy 转为可 JSON 序列化的 dict（使用 to_dict）。"""
    d = tabular_policy.to_dict()
    # to_dict 为 infostate_key -> [(action, prob), ...]，可 JSON（key 字符串，value 列表）
    return {k: [[int(a), float(p)] for a, p in v] for k, v in d.items()}


def save_tabular_policy(
    tabular_policy: policy.TabularPolicy,
    path: str | Path,
    game_name: str = "leduc_poker",
    game_params: Optional[Dict[str, Any]] = None,
) -> None:
    """
    将 TabularPolicy 保存到 JSON 文件。
    同时保存 game 名称与参数，以便加载时重建相同游戏。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "game": game_name,
        "game_params": game_params or {},
        "policy": _tabular_policy_to_serializable(tabular_policy),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def load_tabular_policy(path: str | Path) -> tuple[pyspiel.Game, policy.TabularPolicy]:
    """
    从 JSON 文件加载策略。
    返回 (game, tabular_policy)，其中 tabular_policy 适用于该 game。
    """
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    game_name = payload["game"]
    game_params = payload.get("game_params") or {}
    game = pyspiel.load_game(game_name, game_params)
    tabular_policy = policy.TabularPolicy(game)
    policy_dict = payload["policy"]
    for infostate_key, actions_and_probs in policy_dict.items():
        if infostate_key not in tabular_policy.state_lookup:
            continue
        sorted_pairs = sorted(actions_and_probs, key=lambda x: x[0])
        probs = [float(p) for _, p in sorted_pairs]
        arr = tabular_policy.policy_for_key(infostate_key)
        n = min(len(probs), len(arr))
        arr[:n] = probs[:n]
    return game, tabular_policy
