# 项目现状与迁移到 Linux 指南

本文档说明**当前项目完成状态**以及**将项目迁移到 Linux 服务器并运行 6-max 子游戏 CFR 训练**需要做的事情。

---

## 一、项目现状

### 1.1 目标与技术路线

- **游戏**：6-max No-Limit Texas Hold'em。
- **场景**：真实人类对局（含非 GTO、非常规下注尺度）。
- **目标水平**：接近公开 SOTA，在人类分布下稳健且可剥削。
- **技术路线**：OpenSpiel 环境 + GTO 基础（CFR/抽象）+ 策略网络化 + 对手建模与在线适应。

### 1.2 已完成内容

| 类别 | 内容 |
|------|------|
| **阶段 A** | 6-max 环境（`env/six_max.py`）、pokerkit、requirements.txt、验收脚本（verify_openspiel / verify_6max_env / verify_env_wrapper）。 |
| **阶段 B** | Leduc CFR+ 训练与评估（`train_leduc_cfr.py`、`evaluate_leduc.py`）、策略 IO（`policy_io.py`）。 |
| **抽象与管线** | 6-max 信息抽象与行动抽象（`abstraction.py`）、子游戏策略对接（`subgame_strategy.py`）、`get_abstract_state_key_from_env`、`map_abstract_to_legal`、JSON 策略加载（`JsonAbstractStrategyLookup`）。 |
| **Step 1–4** | env 暴露 pot/stacks/action_id_to_info；抽象状态键生成；抽象→合法动作映射；`run_six_max_with_strategy.py` 在 6-max 中用 JSON 策略运行。 |
| **6-max 子游戏 CFR** | BTN vs BB flop→river 抽象子游戏（`six_max_subgame.py`）、3 尺度/无 flop-turn raise/仅 river all-in raise（`six_max_cfr_config.py`）、收益表（`payoff_table.py`）、CFR+ 求解与 169 键导出、训练脚本 `train_six_max_subgame_cfr.py`、6-max 子游戏策略范围可视化 `six_max_range_viewer.py`、GTO 开池范围占位 `data/gto_open_range_btn.json`。 |

### 1.3 当前缺口与后续方向

- **真实 6-max 子游戏 CFR**：已实现管线与脚本，需在 Linux 上长时间运行（如 20 万次迭代，目标一周内）。
- **抽象动作序列**：对局中尚未自动追踪并填入 `action_sequence`。
- **策略网络与实时决策**：未实现。
- **阶段 C**：对手建模、exploit、真实 HH、offline 评估、A/B 测试未启动。

更细的现状与下一步见 **`docs/CURRENT_STATE_AND_NEXT_STEPS.md`**、**`docs/PROJECT.md`**。

---

## 二、迁移到 Linux 需要做的事情

### 2.1 迁移前准备（本地）

1. **确认可提交/拷贝内容**
   - 代码：`env/`、`algorithms/`、`scripts/`、`docs/`、`README.md`、`requirements.txt`。
   - 数据（建议保留在版本库）：`data/subgame_strategy_example.json`、`data/gto_open_range_btn.json`；可选 `data/leduc_cfr_policy.json`（阶段 B 验收用）。
   - 若使用 git：确保 `.gitignore` 已更新（见下），生成的大文件（如 `data/subgame_strategy_cfr.json`）可不提交。

2. **不要拷贝**
   - 虚拟环境 `.venv/`（在 Linux 上重建）。
   - 本地构建产物（如 `open_spiel/build/`），若 OpenSpiel 在 Linux 上重新构建。

### 2.2 将项目拷贝到 Linux 服务器

- **方式一**：git clone（若项目在远程仓库）。
  ```bash
  git clone <repo_url> poker && cd poker
  ```
- **方式二**：打包上传。
  ```bash
  # 本地（PowerShell）打包（排除 .venv、__pycache__ 等）
  Compress-Archive -Path env, algorithms, scripts, docs, data, README.md, requirements.txt, .gitignore -DestinationPath poker.zip
  # 上传 poker.zip 到服务器后
  unzip poker.zip -d poker && cd poker
  ```
- 建议使用单卡 5090 或同等算力机器；当前 CFR 训练以 CPU 为主，GPU 未使用。

### 2.3 在 Linux 上配置环境

**Python 版本**：核心与 OpenSpiel/Leduc 管线需 **Python 3.10+**；**6-max 环境（pokerkit）需 Python 3.11+**。若仅跑 Leduc 与阶段 B 验收，3.10 即可；完整 6-max 与 `verify_6max_env`/`verify_env_wrapper` 建议使用 3.11+。

```bash
cd /path/to/poker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

若系统创建 venv 时提示 `ensurepip is not available`，可先安装 `python3.10-venv`（或 `python3.11-venv`）再创建；或使用无 pip 的 venv 后手动安装 pip：

```bash
python3 -m venv .venv --without-pip
curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py && .venv/bin/python3 get-pip.py && rm get-pip.py
.venv/bin/pip install -r requirements.txt
```

若 OpenSpiel 使用本地源码安装（替代 PyPI 的 `open-spiel`）：

```bash
pip uninstall open-spiel  # 若已通过 pip 安装
pip install -e ./open_spiel
```

依赖：Python 3.10+（3.11+ 建议，以使用 pokerkit）、`numpy`、`absl-py`、`open-spiel`（见上）。6-max 环境需额外安装 `pokerkit>=0.4.0`（仅支持 Python 3.11+）：`pip install 'pokerkit>=0.4.0'`。

### 2.4 验收（可选但建议）

在 Linux 上跑通以下命令，确认环境与管线正常：

```bash
# 1) 基础与 6-max 环境
python scripts/verify_openspiel.py
python scripts/verify_6max_env.py
python scripts/verify_env_wrapper.py

# 2) 阶段 B（需已有 data/leduc_cfr_policy.json，或先运行下方训练）
python scripts/verify_phase_b.py --skip_train

# 3) 6-max 子游戏 CFR 快速自检（约 3 桶 × 50 迭代）
python scripts/train_six_max_subgame_cfr.py --quick_test --output data/subgame_strategy_cfr_test.json
python scripts/run_six_max_with_strategy.py --strategy data/subgame_strategy_cfr_test.json --hands 2
```

上述脚本均**退出码 0** 即表示迁移成功、可进行正式训练。

### 2.5 正式训练 6-max 子游戏策略

```bash
python scripts/train_six_max_subgame_cfr.py \
  --output data/subgame_strategy_cfr.json \
  --max_iterations 200000 \
  --print_interval 10000
```

- 输出：`data/subgame_strategy_cfr.json`（与 `subgame_strategy_example.json` 格式一致）。
- 训练完成后，可用该策略在 6-max 中运行：
  ```bash
  python scripts/run_six_max_with_strategy.py --strategy data/subgame_strategy_cfr.json --hands N
  ```

若希望一周内跑完，可酌情将 `--max_iterations` 调小（如 100000），或在 `algorithms/six_max_cfr_config.py` 中将 `REDUCED_BUCKET_COUNT` 调小（如 30）以加快单次迭代。

### 2.6 注意事项

- **路径**：脚本均假设在项目根目录执行（`scripts/` 为相对路径）。
- **编码**：策略 JSON 为 UTF-8；终端与编辑器保持一致即可。
- **数据**：`data/gto_open_range_btn.json` 为 BTN GTO 开池范围占位，可替换为自有 GTO 表；当前 6-max 策略管线主要使用 postflop 策略，preflop 开池逻辑可后续接入该表。

---

## 三、相关文档

| 文档 | 说明 |
|------|------|
| [README.md](../README.md) | 快速开始、验收脚本、项目结构 |
| [PROJECT.md](PROJECT.md) | 项目目标、技术栈、阶段 A/B 完成表 |
| [CURRENT_STATE_AND_NEXT_STEPS.md](CURRENT_STATE_AND_NEXT_STEPS.md) | 现状详解、缺口、下一步建议顺序 |
| [OPENSPIEL_ACCEPTANCE_AND_NEXT_STEPS.md](OPENSPIEL_ACCEPTANCE_AND_NEXT_STEPS.md) | OpenSpiel 验收与阶段 A/B/C 清单 |
| [ABSTRACTION_6MAX.md](ABSTRACTION_6MAX.md) | 6-max 抽象设计 |
| [RUN_ON_LINUX.md](RUN_ON_LINUX.md) | Linux 上训练命令速查 |
