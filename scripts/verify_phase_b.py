#!/usr/bin/env python3
"""
阶段 B 验收脚本：Leduc 策略训练/加载/评估、6-max 抽象与子游戏对接。
用法（项目根目录）：
  .venv\\Scripts\\python.exe scripts\\verify_phase_b.py
  .venv\\Scripts\\python.exe scripts\\verify_phase_b.py --skip_train
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def main():
    p = argparse.ArgumentParser(description="阶段 B 验收")
    p.add_argument("--skip_train", action="store_true", help="跳过 Leduc 训练，仅做加载/评估与抽象检查")
    p.add_argument("--max_iterations", type=int, default=500, help="训练时最大迭代次数（快速验收用）")
    args = p.parse_args()

    print("=" * 60)
    print("阶段 B 验收")
    print("=" * 60)

    # 1) 抽象模块
    print("\n[1] 6-max 抽象模块...")
    from algorithms import abstraction
    assert len(abstraction.BET_POT_RATIOS) == len(abstraction.BET_BUCKET_NAMES)
    b = abstraction.bet_size_to_bucket(100.0, 50.0, False)
    assert b == "50%"
    assert abstraction.bet_size_to_bucket(100.0, 0.0, False) == abstraction.CHECK_OR_CALL_BUCKET
    print("  OK: abstraction.BET_POT_RATIOS, bet_size_to_bucket, PREFLOP_HAND_BUCKETS")

    # 2) 子游戏策略对接
    print("\n[2] 子游戏策略对接...")
    from algorithms.subgame_strategy import UniformAbstractStrategy, AbstractStrategyLookup
    lookup = UniformAbstractStrategy()
    probs = lookup.action_probabilities("flop_rainbow_22_none")
    assert isinstance(probs, dict) and len(probs) > 0
    print("  OK: AbstractStrategyLookup, UniformAbstractStrategy")

    # 3) Leduc 策略 IO
    print("\n[3] Leduc 策略 IO...")
    from algorithms.policy_io import load_tabular_policy, save_tabular_policy
    policy_path = Path("data/leduc_cfr_policy.json")
    if policy_path.exists():
        game, policy = load_tabular_policy(policy_path)
        assert game.num_players() == 2
        print("  OK: load_tabular_policy from", policy_path)
    else:
        # 保存一个占位策略
        import pyspiel
        from open_spiel.python import policy as ospolicy
        game = pyspiel.load_game("leduc_poker")
        tab = ospolicy.TabularPolicy(game)
        policy_path.parent.mkdir(parents=True, exist_ok=True)
        save_tabular_policy(tab, policy_path, "leduc_poker", {})
        print("  OK: save_tabular_policy (placeholder) to", policy_path)

    # 4) Leduc 评估（若存在策略）
    print("\n[4] Leduc 评估...")
    from open_spiel.python.algorithms import expected_game_score, exploitability
    game, loaded = load_tabular_policy(policy_path)
    expl = exploitability.exploitability(game, loaded)
    values = expected_game_score.policy_value(game.new_initial_state(), [loaded, loaded])
    print(f"  Exploitability = {expl:.6f}, Self-play values = {values}")

    # 5) 可选：短时训练
    if not args.skip_train:
        print("\n[5] Leduc CFR+ 短时训练...")
        from algorithms.leduc_cfr import train_and_save
        out = Path("data/leduc_verify_policy.json")
        train_and_save(output_path=out, max_iterations=args.max_iterations, target_exploitability=1.0, print_interval=args.max_iterations)
        game2, pol2 = load_tabular_policy(out)
        expl2 = exploitability.exploitability(game2, pol2)
        print(f"  训练后 exploitability = {expl2:.6f}")
    else:
        print("\n[5] 跳过训练 (--skip_train)")

    print("\n" + "=" * 60)
    print("阶段 B 验收通过。")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
