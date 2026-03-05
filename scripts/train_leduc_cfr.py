#!/usr/bin/env python3
"""
Leduc CFR+ 训练入口：训练至 exploitability < 0.01 并保存策略。
用法（项目根目录）：
  .venv\\Scripts\\python.exe scripts\\train_leduc_cfr.py
  .venv\\Scripts\\python.exe scripts\\train_leduc_cfr.py --max_iterations 100000 --output data/leduc.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 项目根加入 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from algorithms.leduc_cfr import train_and_save


def main():
    p = argparse.ArgumentParser(description="Leduc CFR+ 训练并保存策略")
    p.add_argument("--output", default="data/leduc_cfr_policy.json", help="策略输出路径")
    p.add_argument("--max_iterations", type=int, default=500_000, help="最大迭代次数")
    p.add_argument("--target_exploitability", type=float, default=0.01, help="目标 exploitability")
    p.add_argument("--print_interval", type=int, default=10_000, help="打印间隔")
    args = p.parse_args()

    train_and_save(
        output_path=args.output,
        max_iterations=args.max_iterations,
        target_exploitability=args.target_exploitability,
        print_interval=args.print_interval,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
