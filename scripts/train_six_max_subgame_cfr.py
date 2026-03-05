#!/usr/bin/env python3
"""
6-max 子游戏 CFR+ 训练：BTN vs BB，flop→river，约束（3 尺度、flop/turn 不 raise、river 仅 all-in raise）。
输出策略 JSON 与现有 subgame_strategy_example 格式兼容，可被 run_six_max_with_strategy 使用。

用法（项目根目录）：
  python scripts/train_six_max_subgame_cfr.py --output data/subgame_strategy_cfr.json
  python scripts/train_six_max_subgame_cfr.py --max_iterations 100000 --output data/subgame_strategy_cfr.json

建议在 Linux 服务器（如单卡 5090）上运行，总体训练时长目标一周以内。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 项目根
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.payoff_table import build_payoff_table_fast_heuristic
from algorithms.six_max_cfr_config import (
    BOARD_BUCKETS,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_PRINT_INTERVAL,
)
from algorithms.six_max_subgame import (
    HAND_BUCKETS_TRAIN,
    export_policy_to_169_keys,
    run_cfr_plus,
)


def main() -> int:
    p = argparse.ArgumentParser(description="6-max 子游戏 CFR+ 训练（BTN vs BB flop→river）")
    p.add_argument(
        "--output",
        default="data/subgame_strategy_cfr.json",
        help="输出策略 JSON 路径",
    )
    p.add_argument(
        "--max_iterations",
        type=int,
        default=DEFAULT_MAX_ITERATIONS,
        help="CFR+ 迭代次数",
    )
    p.add_argument(
        "--print_interval",
        type=int,
        default=DEFAULT_PRINT_INTERVAL,
        help="打印进度间隔",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--quick_test",
        action="store_true",
        help="极少量桶与迭代，仅验证脚本可跑通",
    )
    args = p.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.quick_test:
        hand_buckets = ("G0", "G1", "G2")
        board_buckets = ("rainbow", "twotone")
        args.max_iterations = min(args.max_iterations, 50)
        args.print_interval = 10
        print("Quick test mode: 3 hand buckets, 2 board buckets.")
    else:
        hand_buckets = HAND_BUCKETS_TRAIN
        board_buckets = tuple(BOARD_BUCKETS)

    print("Building payoff table (fast heuristic)...")
    payoff_table = build_payoff_table_fast_heuristic(hand_buckets, board_buckets)
    print(f"  Payoff table size: {len(payoff_table)}")

    print("Running CFR+...")
    avg_policy = run_cfr_plus(
        payoff_table=payoff_table,
        hand_buckets=hand_buckets,
        board_buckets=board_buckets,
        max_iterations=args.max_iterations,
        print_interval=args.print_interval,
        rng=None,
    )
    print(f"  Infosets in policy: {len(avg_policy)}")

    print("Exporting to 169 hand keys...")
    policy_169 = export_policy_to_169_keys(avg_policy)

    # 写入 JSON：与 subgame_strategy_example 格式一致，保留 default 占位
    out_data = {
        "default": {
            "fold": 0.05,
            "check_or_call": 0.70,
            "33%": 0.15,
            "75%": 0.05,
            "150%": 0.05,
            "all_in": 0.0,
        }
    }
    for k, v in policy_169.items():
        out_data[k] = v

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2, ensure_ascii=False)

    print(f"Wrote {out_path} ({len(out_data)} keys).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
