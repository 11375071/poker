# Poker AI — 6-max 德州扑克

面向 6-max No-Limit Texas Hold'em 的 AI 项目，基于 OpenSpiel 与 C++ 工具链，目标为在真实人类对局场景下达到接近 SOTA 的表现（含非 GTO 下注尺度下的稳健性）。

---

## 环境要求

- **Python** 3.10+
- **C++ 工具链**（已用于本地构建 OpenSpiel）
- **OpenSpiel**：通过本地源码编译并安装（见 `open_spiel/`）
- **pokerkit**：用于 6-max NLHE 的 `python_pokerkit_wrapper`

---

## 快速开始

### 1. 创建虚拟环境并安装依赖

```powershell
cd c:\Users\user\Desktop\poker
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# OpenSpiel 若为本地构建: pip install -e ./open_spiel
```

### 2. 验收脚本

| 脚本 | 说明 |
|------|------|
| `scripts\verify_openspiel.py` | OpenSpiel + Leduc/Kuhn/CFR 基础验收 |
| `scripts\verify_6max_env.py` | 6-max NLHE 环境（需已安装 pokerkit） |
| `scripts\verify_env_wrapper.py` | 阶段 A5：`env` 包封装接口验收 |
| `scripts\verify_phase_b.py` | 阶段 B：Leduc 策略 IO、抽象、子游戏对接验收 |
| `scripts\run_six_max_with_strategy.py` | 6-max 使用 JSON 抽象策略运行（Step 1–4 管线验收） |
| `scripts\train_six_max_subgame_cfr.py` | 6-max 子游戏 CFR+ 训练（BTN vs BB flop→river），输出策略 JSON |
| `scripts\six_max_viewer.py` | 6-max 牌桌可视化（Tkinter），可选运行 |

在项目根目录执行（PowerShell）：

```powershell
.venv\Scripts\python.exe scripts\verify_openspiel.py
.venv\Scripts\python.exe scripts\verify_6max_env.py
.venv\Scripts\python.exe scripts\verify_env_wrapper.py
.venv\Scripts\python.exe scripts\verify_phase_b.py --skip_train
```

阶段 B 训练与评估：

```powershell
.venv\Scripts\python.exe scripts\train_leduc_cfr.py --output data/leduc_cfr_policy.json
.venv\Scripts\python.exe scripts\evaluate_leduc.py data/leduc_cfr_policy.json --num_playouts 2000
```

6-max 抽象策略管线（Step 1–4）：

```powershell
.venv\Scripts\python.exe scripts\run_six_max_with_strategy.py --strategy data/subgame_strategy_example.json --hands 3
```

退出码均为 0 即表示通过。阶段 B 使用 `--skip_train` 时需已存在 `data/leduc_cfr_policy.json`（可先运行上方训练命令生成）。

### 3. 使用 6-max 环境

```python
import sys
sys.path.insert(0, ".")
from env import create_six_max_env

env = create_six_max_env(num_players=6, seed=42)
obs = env.reset()
while not env.is_terminal():
    legal = env.legal_actions()
    action = legal[0]  # 或由策略选择
    obs = env.step(action)
print(env.returns())
```

---

## 项目结构

```
poker/
├── README.md                 # 本文件
├── requirements.txt          # Python 依赖（含 pokerkit）
├── docs/
│   ├── README.md              # 文档索引
│   ├── ABSTRACTION_6MAX.md    # 6-max 抽象设计
│   ├── OPENSPIEL_ACCEPTANCE_AND_NEXT_STEPS.md  # 验收报告与阶段清单
│   └── PROJECT.md             # 项目说明与进度
├── env/                      # 6-max 环境封装
│   ├── __init__.py
│   └── six_max.py
├── algorithms/               # policy_io, leduc_cfr, abstraction, subgame_strategy
├── data/                     # 策略与测试数据（leduc_cfr_policy.json、subgame_strategy_example.json）
├── scripts/
│   ├── verify_openspiel.py   # OpenSpiel 验收
│   ├── verify_6max_env.py    # 6-max 环境验收
│   ├── verify_env_wrapper.py # 封装接口验收
│   ├── verify_phase_b.py     # 阶段 B 验收
│   ├── train_leduc_cfr.py    # Leduc CFR+ 训练
│   ├── evaluate_leduc.py     # Leduc 策略评估
│   ├── run_six_max_with_strategy.py  # 6-max 使用 JSON 抽象策略运行（Step 1–4 管线）
│   └── six_max_viewer.py     # 6-max 牌桌可视化（Tkinter）
└── open_spiel/               # OpenSpiel 源码与构建（子仓库或拷贝）
```

---

## 验收评估

在本地执行上述 4 个验收脚本（`verify_openspiel`、`verify_6max_env`、`verify_env_wrapper`、`verify_phase_b --skip_train`）均**退出码 0** 即表示环境与阶段 A/B 通过。阶段 B 验收会检查：抽象模块、子游戏策略接口、Leduc 策略加载与 exploitability、可选短时 CFR 训练。  
可选：执行 `run_six_max_with_strategy.py --hands 2` 退出码 0 即表示 Step 1–4 抽象策略管线通过。

---

## 当前进度

- **阶段 A（环境与 6-max 支撑）**：已完成  
  - A1–A5：pokerkit、requirements.txt、env/、6-max 验收与封装；env 已暴露 pot、stacks、action_id_to_info 及街/手牌/公共牌接口。
- **阶段 B（算法与策略）**：已完成  
  - B1 Leduc CFR+ 训练与导出；B2 策略加载与评估脚本；B3 6-max 抽象设计（`docs/ABSTRACTION_6MAX.md` + `algorithms/abstraction.py`）；B4 子游戏策略对接（`algorithms/subgame_strategy.py`）。
- **抽象与策略管线（Step 1–4）**：已完成  
  - Step 1 env 暴露 pot/stack/action_id_to_info；Step 2 信息抽象（hand_to_preflop_bucket、board_to_flop_bucket、get_abstract_state_key_from_env）；Step 3 map_abstract_to_legal 真实逻辑；Step 4 JSON 策略加载（`JsonAbstractStrategyLookup`）+ `run_six_max_with_strategy.py` 在 6-max 中运行。

**6-max 子游戏 CFR 训练**：项目现状与迁移到 Linux 的完整说明见 **`docs/STATE_AND_LINUX_MIGRATION.md`**，命令速查见 **`docs/RUN_ON_LINUX.md`**。  
更多细节见 **`docs/PROJECT.md`**、**`docs/CURRENT_STATE_AND_NEXT_STEPS.md`** 与 **`docs/OPENSPIEL_ACCEPTANCE_AND_NEXT_STEPS.md`**。
