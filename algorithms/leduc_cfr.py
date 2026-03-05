# Copyright 2025 Poker AI Project. Leduc 上的 CFR+ 训练与导出。
"""
在 Leduc Poker 上运行 CFR+，训练至 exploitability 低于目标后导出 TabularPolicy。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pyspiel

from open_spiel.python.algorithms import cfr, exploitability
from open_spiel.python import policy

from . import policy_io


def _progress_bar(current: int, total: int, width: int = 40, expl: float | None = None) -> str:
    """生成一行进度条文本。"""
    if total <= 0:
        pct = 0.0
    else:
        pct = current / total
    filled = int(width * pct)
    bar = "=" * filled + ">" * (1 if filled < width else 0) + " " * (width - filled - 1)
    expl_str = f" expl={expl:.6f}" if expl is not None else ""
    return f"  [{bar}] {pct*100:5.1f}% iter {current}{expl_str}\r"


def train_leduc_cfr(
    max_iterations: int = 500_000,
    target_exploitability: float = 0.01,
    print_interval: int = 10_000,
    game_params: Optional[dict] = None,
) -> policy.TabularPolicy:
    """
    在 Leduc 上运行 CFR+，直到 exploitability < target_exploitability 或达到 max_iterations。
    返回平均策略（TabularPolicy）。
    """
    params = game_params or {}
    game = pyspiel.load_game("leduc_poker", params)
    solver = cfr.CFRPlusSolver(game)

    last_expl: float | None = None
    for i in range(max_iterations):
        solver.evaluate_and_update_policy()
        k = i + 1
        if k % print_interval == 0:
            last_expl = exploitability.exploitability(game, solver.average_policy())
            print(_progress_bar(k, max_iterations, expl=last_expl), end="", flush=True)
            if last_expl < target_exploitability:
                print()
                print(f"  达到目标 exploitability < {target_exploitability}，提前结束")
                break
        elif k % 500 == 0 or k == max_iterations:
            print(_progress_bar(k, max_iterations, expl=last_expl), end="", flush=True)

    print()
    return solver.average_policy()


def train_and_save(
    output_path: str | Path = "data/leduc_cfr_policy.json",
    max_iterations: int = 500_000,
    target_exploitability: float = 0.01,
    print_interval: int = 10_000,
    game_params: Optional[dict] = None,
) -> policy.TabularPolicy:
    """
    训练 Leduc CFR+ 并将策略保存到 output_path。
    返回平均策略。
    """
    game_params = game_params or {}
    game = pyspiel.load_game("leduc_poker", game_params)
    print("Leduc CFR+ 训练 (目标 exploitability < {})".format(target_exploitability))
    average_policy = train_leduc_cfr(
        max_iterations=max_iterations,
        target_exploitability=target_exploitability,
        print_interval=print_interval,
        game_params=game_params,
    )
    # 最终 exploitability
    expl = exploitability.exploitability(game, average_policy)
    print(f"最终 exploitability = {expl:.6f}")

    output_path = Path(output_path)
    policy_io.save_tabular_policy(
        average_policy,
        output_path,
        game_name="leduc_poker",
        game_params=game_params,
    )
    print(f"策略已保存: {output_path}")
    return average_policy
