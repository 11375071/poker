# 在 Linux 上运行 6-max 子游戏 CFR 训练（速查）

完整说明（**项目现状** + **迁移到 Linux 的步骤**）见 **[STATE_AND_LINUX_MIGRATION.md](STATE_AND_LINUX_MIGRATION.md)**。

---

## 快速命令

```bash
cd /path/to/poker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 自检
python scripts/train_six_max_subgame_cfr.py --quick_test --output data/subgame_strategy_cfr_test.json
python scripts/run_six_max_with_strategy.py --strategy data/subgame_strategy_cfr_test.json --hands 2

# 正式训练
python scripts/train_six_max_subgame_cfr.py --output data/subgame_strategy_cfr.json --max_iterations 200000 --print_interval 10000
```
