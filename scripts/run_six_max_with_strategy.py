#!/usr/bin/env python3
"""
使用抽象策略在 6-max 环境中运行若干手牌。
用法（项目根目录）：
  .venv\\Scripts\\python.exe scripts\\run_six_max_with_strategy.py
  .venv\\Scripts\\python.exe scripts\\run_six_max_with_strategy.py --strategy data/subgame_strategy_example.json --hands 5
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from env import create_six_max_env
from algorithms.abstraction import get_abstract_state_key_from_env
from algorithms.subgame_strategy import JsonAbstractStrategyLookup, map_abstract_to_legal


def sample_action(legal_actions: list, dist: dict) -> int:
    """按分布 dist 在 legal_actions 上采样；若 dist 未覆盖则均匀采样。"""
    weights = [dist.get(a, 0.0) for a in legal_actions]
    total = sum(weights)
    if total <= 0:
        return random.choice(legal_actions)
    return random.choices(legal_actions, weights=weights, k=1)[0]


def main():
    p = argparse.ArgumentParser(description="6-max 使用抽象策略运行")
    p.add_argument("--strategy", default="data/subgame_strategy_example.json", help="策略 JSON 路径")
    p.add_argument("--hands", type=int, default=3, help="运行手数")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    path = Path(args.strategy)
    if not path.exists():
        print(f"策略文件不存在: {path}")
        return 1

    lookup = JsonAbstractStrategyLookup(path)
    env = create_six_max_env(num_players=6, seed=args.seed)
    rng = random.Random(args.seed)

    total_returns = [0.0] * 6
    for h in range(args.hands):
        obs = env.reset()
        while not env.is_terminal():
            legal = env.legal_actions()
            if not legal:
                break
            key = get_abstract_state_key_from_env(env)
            abstract_probs = lookup.action_probabilities(key)
            pot = env.pot()
            stack = env.stack_for_player(env.current_player())
            a2i = env.action_id_to_info()
            dist = map_abstract_to_legal(
                abstract_probs, legal, a2i, pot, env.min_raise_to() or 0, stack
            )
            action = sample_action(legal, dist)
            obs = env.step(action)
        ret = env.returns()
        for i in range(6):
            total_returns[i] += ret[i]
        print(f"  手 {h+1}: returns = {[round(r, 1) for r in ret]}")

    print(f"\n{args.hands} 手总收益: {[round(r, 1) for r in total_returns]}")
    print("Step 4 验收: 6-max 已能使用 JSON 抽象策略完成对局。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
