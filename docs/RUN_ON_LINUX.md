# 在 Linux 上运行 6-max 子游戏 CFR 训练（速查）

完整说明（**项目现状** + **迁移到 Linux 的步骤**）见 **[STATE_AND_LINUX_MIGRATION.md](STATE_AND_LINUX_MIGRATION.md)**。

**环境**：6-max 与 pokerkit 需 **Python 3.11+**；仅 OpenSpiel/Leduc 可用 3.10。若 `python3 -m venv` 报 ensurepip 不可用，先安装 `python3.11-venv` 或用 `--without-pip` + get-pip.py 引导 pip（见 STATE_AND_LINUX_MIGRATION.md 2.3 节）。

---

## 快速命令

```bash
cd /path/to/poker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 自检：6-max 子游戏 CFR 快速自检（约 3 桶 × 50 迭代）
python scripts/train_six_max_subgame_cfr.py --quick_test --output data/subgame_strategy_cfr_test.json
python scripts/run_six_max_with_strategy.py --strategy data/subgame_strategy_cfr_test.json --hands 2

# 正式训练
python scripts/train_six_max_subgame_cfr.py --output data/subgame_strategy_cfr.json --max_iterations 200000 --print_interval 10000

# 训练后可视化策略范围（在有图形界面的机器上运行）
python scripts/six_max_range_viewer.py \
  --strategy data/subgame_strategy_cfr.json \
  --street flop \
  --board_bucket rainbow \
  --actions none
```
