# Poker AI 项目说明与进度

## 一、项目目标

- **游戏**：6-max No-Limit Texas Hold'em（6 人无限制德州扑克）。
- **场景**：真实人类对局，包含非 GTO、非常规下注尺度等。
- **目标水平**：接近当前公开 SOTA，在人类分布下保持稳健与可剥削性。

技术路线概览：**OpenSpiel 环境 + GTO 基础（CFR/抽象）+ 策略网络化 + 对手建模与在线适应**。

---

## 二、技术栈与依赖

| 组件 | 说明 |
|------|------|
| **OpenSpiel** | 博弈/强化学习框架，本地 C++ 构建 + Python 绑定 |
| **python_pokerkit_wrapper** | OpenSpiel 内基于 pokerkit 的扑克游戏，支持 2–10 人 NLHE 等 |
| **pokerkit** | Python 扑克规则与状态实现（pip install pokerkit） |
| **env** | 本项目 `env/` 包，对 6-max NLHE 的封装，供算法层统一调用 |

当前**未**使用 C++ `universal_poker`（未编译进本机 OpenSpiel）；6-max 完全由 `python_pokerkit_wrapper` 支撑。

---

## 三、阶段 A 完成情况（环境与 6-max）

阶段 A 已全部完成，验收标准均满足。

| 序号 | 任务 | 完成内容 | 验收 |
|------|------|----------|------|
| A1 | 安装 pokerkit | 在 .venv 中 `pip install pokerkit` | `verify_openspiel.py` 通过，`python_pokerkit_wrapper` 已注册 |
| A2 | requirements.txt | 项目根目录 `requirements.txt`，含 numpy/absl/scipy/ml-collections/pokerkit | `pip install -r requirements.txt` 可复现环境 |
| A3 | 项目目录结构 | `env/`、`algorithms/` 包及 `__init__.py` | 可从项目根 `from env import create_six_max_env` |
| A4 | 6-max 环境验收脚本 | `scripts/verify_6max_env.py`：6 人 NLHE 随机 3 手，输出 returns | 退出码 0，每手 6 维 returns |
| A5 | 6-max 封装接口 | `env/six_max.py`：`SixMaxEnv`、`create_six_max_env`；reset/step、current_player、legal_actions、is_terminal、returns、观察 dict | `scripts/verify_env_wrapper.py` 通过，可供算法层调用 |

### 3.1 env 包接口摘要

- **创建环境**：`create_six_max_env(num_players=6, small_blind=50, big_blind=100, stack_bb=100, seed=None)`  
  或直接 `SixMaxEnv(...)`。
- **reset()**：开始新的一手，推进 chance 节点后返回第一个决策点的观察（dict：`current_player`, `legal_actions`, `info_state_string`, `is_terminal`, `returns`；非终局时含 `pot`, `stacks`, `action_id_to_info`）。
- **step(action)**：执行动作并推进至下一决策点或终局，返回同上结构的观察。
- **current_player()**、**legal_actions()**、**is_terminal()**、**returns()**：与 OpenSpiel 风格一致。
- **抽象与策略映射支撑（Step 1）**：`pot()`、`stacks()`、`stack_for_player(player)`、`min_raise_to()`、`action_id_to_info()`；`get_current_street_name()`、`get_hole_cards_str(player)`、`get_board_cards_str()` 供抽象层生成状态键。

详见 `env/six_max.py` 文档字符串。

---

## 四、阶段 B 完成情况（算法与策略）

阶段 B 已全部完成，验收标准均满足。

| 序号 | 任务 | 完成内容 | 验收 |
|------|------|----------|------|
| B1 | Leduc CFR 闭环 | `algorithms/leduc_cfr.py`：CFR+ 训练至 exploitability &lt; 目标值并导出；`algorithms/policy_io.py` 序列化 TabularPolicy | `scripts/train_leduc_cfr.py` 产出 `data/leduc_cfr_policy.json`；加载后与随机/自身对战 EV 合理 |
| B2 | Leduc 策略导出与评估脚本 | `scripts/evaluate_leduc.py`：加载策略 + vs 随机 / vs 自身，输出 exploitability、期望值、采样均值 | 可复现 Leduc 策略的 EV 与 exploitability |
| B3 | 6-max 抽象设计 | `docs/ABSTRACTION_6MAX.md`：手牌/公共牌聚类与行动抽象（下注尺度桶）；`algorithms/abstraction.py`：BET_POT_RATIOS、bet_size_to_bucket、PREFLOP_HAND_BUCKETS、get_abstract_state_key | 文档与代码明确定义，可供 CFR/求解器使用 |
| B4 | 子游戏 CFR 与 6-max 对接 | Leduc 子游戏 CFR+ 跑通；`algorithms/subgame_strategy.py`：AbstractStrategyLookup、UniformAbstractStrategy、**map_abstract_to_legal 真实逻辑**、**JsonAbstractStrategyLookup**；`data/subgame_strategy_example.json`；`scripts/run_six_max_with_strategy.py` 在 6-max 中按抽象策略运行 | 子游戏策略可加载；抽象→6-max 映射与 JSON 策略管线可用 |

### 4.1 阶段 B 脚本与入口

- **训练**：`scripts/train_leduc_cfr.py`（`--output`、`--max_iterations`、`--target_exploitability`）
- **评估**：`scripts/evaluate_leduc.py`（策略路径、`--num_playouts`）
- **验收**：`scripts/verify_phase_b.py`（可选 `--skip_train`）
- **6-max 抽象策略运行**：`scripts/run_six_max_with_strategy.py`（`--strategy`、`--hands`），依赖 `data/subgame_strategy_example.json` 或自备 JSON 策略

---

## 五、后续阶段（简要）

- **抽象与策略管线（Step 1–4）**：已完成。env 暴露 pot/stack/action_id_to_info；信息抽象（hand/board bucket、get_abstract_state_key_from_env）；map_abstract_to_legal 真实逻辑；JSON 策略加载与 6-max 运行脚本。详见 **CURRENT_STATE_AND_NEXT_STEPS.md**。
- **可选**：真实 6-max 子游戏 CFR 训练（长时间）、策略网络与实时决策、对手建模与 exploit。
- **阶段 C**：对手建模与 exploit；真实手牌历史与 offline 评估、A/B 测试。

具体任务与验收标准见 **`OPENSPIEL_ACCEPTANCE_AND_NEXT_STEPS.md`** 第四节、第五节。

---

## 六、参考文档

- **CURRENT_STATE_AND_NEXT_STEPS.md**：项目现状详解、Step 1–4 完成情况与下一步工作分析。
- **OPENSPIEL_ACCEPTANCE_AND_NEXT_STEPS.md**：OpenSpiel 验收报告、可用游戏列表、阶段 A/B/C 可执行清单与建议执行顺序。
- **ABSTRACTION_6MAX.md**：6-max 信息抽象与行动抽象设计。
- **README.md**：快速开始、验收脚本用法、项目结构、当前进度摘要。
