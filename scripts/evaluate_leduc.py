#!/usr/bin/env python3
"""
Leduc 策略评估：加载已保存策略，与随机 / 自身对战，输出期望收益与对局采样均值。
用法（项目根目录）：
  python scripts/evaluate_leduc.py data/leduc_cfr_policy.json
  python scripts/evaluate_leduc.py data/leduc_cfr_policy.json --num_playouts 5000
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from open_spiel.python.algorithms import expected_game_score, exploitability
from open_spiel.python import policy
import pyspiel

from algorithms.policy_io import load_tabular_policy


def sample_playout(game, policies, rng):
    """一次对局：双方按策略采样动作直到终局，返回 returns。"""
    state = game.new_initial_state()
    while not state.is_terminal():
        if state.is_chance_node():
            outcomes = state.chance_outcomes()
            action = rng.choice([a for a, _ in outcomes])
        else:
            player = state.current_player()
            probs = policies[player].action_probabilities(state)
            actions = list(probs.keys())
            weights = [probs[a] for a in actions]
            action = rng.choices(actions, weights=weights, k=1)[0]
        state.apply_action(action)
    return list(state.returns())


def main():
    p = argparse.ArgumentParser(description="加载 Leduc 策略并评估")
    p.add_argument("policy_path", nargs="?", default="data/leduc_cfr_policy.json", help="策略 JSON 路径")
    p.add_argument("--num_playouts", type=int, default=2000, help="对局采样次数（vs 随机 / vs 自身）")
    p.add_argument("--seed", type=int, default=42, help="随机种子")
    args = p.parse_args()

    path = Path(args.policy_path)
    if not path.exists():
        print(f"策略文件不存在: {path}")
        print("请先运行: python scripts/train_leduc_cfr.py")
        return 1

    game, loaded_policy = load_tabular_policy(path)
    rng = random.Random(args.seed)

    # 1) 理论 exploitability 与 self-play 期望值
    expl = exploitability.exploitability(game, loaded_policy)
    print(f"Exploitability = {expl:.6f}")
    values_self = expected_game_score.policy_value(
        game.new_initial_state(), [loaded_policy, loaded_policy]
    )
    print(f"Self-play 期望值 (player0, player1) = ({values_self[0]:.6f}, {values_self[1]:.6f})")

    # 2) vs 随机策略（期望值）
    random_policy = policy.UniformRandomPolicy(game)
    values_vs_random = expected_game_score.policy_value(
        game.new_initial_state(), [loaded_policy, random_policy]
    )
    print(f"vs 随机 期望值 (player0, player1) = ({values_vs_random[0]:.6f}, {values_vs_random[1]:.6f})")

    # 3) 对局采样：vs 随机
    returns_vs_random = [0.0, 0.0]
    for _ in range(args.num_playouts):
        ret = sample_playout(game, [loaded_policy, random_policy], rng)
        returns_vs_random[0] += ret[0]
        returns_vs_random[1] += ret[1]
    n = args.num_playouts
    returns_vs_random[0] /= n
    returns_vs_random[1] /= n
    print(f"vs 随机 采样均值 ({n} 局) = ({returns_vs_random[0]:.6f}, {returns_vs_random[1]:.6f})")

    # 4) 对局采样：self-play
    returns_self = [0.0, 0.0]
    for _ in range(args.num_playouts):
        ret = sample_playout(game, [loaded_policy, loaded_policy], rng)
        returns_self[0] += ret[0]
        returns_self[1] += ret[1]
    returns_self[0] /= n
    returns_self[1] /= n
    print(f"Self-play 采样均值 ({n} 局) = ({returns_self[0]:.6f}, {returns_self[1]:.6f})")

    print("评估完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
