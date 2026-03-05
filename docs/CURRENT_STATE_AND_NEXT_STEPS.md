# 项目现状与下一步工作

本文档在阅读 README、PROJECT、OPENSPIEL_ACCEPTANCE、代码与抽象设计后整理，用于说明**当前项目具体情况**与**下一步工作内容**。

---

## 一、项目目标（回顾）

- **游戏**：6-max No-Limit Texas Hold'em。
- **场景**：真实人类对局（含非 GTO、非常规下注尺度）。
- **目标水平**：接近公开 SOTA，在人类分布下稳健且可剥削。

技术路线：**OpenSpiel 环境 + GTO 基础（CFR/抽象）+ 策略网络化 + 对手建模与在线适应**。

---

## 二、当前项目具体情况

### 2.1 已完成的模块与能力

#### 环境层（阶段 A + Step 1）

| 组件 | 位置 | 说明 |
|------|------|------|
| 6-max 环境 | `env/six_max.py` | 基于 OpenSpiel `python_pokerkit_wrapper`，100BB 默认，支持 reset/step、current_player、legal_actions、is_terminal、returns，观察中含 `info_state_string`；**已暴露** `pot`、`stacks`、`action_id_to_info`（Step 1）。 |
| 工厂函数 | `env/__init__.py` | `create_six_max_env(num_players, small_blind, big_blind, stack_bb, seed)`，供算法层统一调用。 |

**接口要点**：

- 动作空间为 OpenSpiel 的 **整数 action ID**（如 fold=0, call=1, 以及大量 bet/raise 具体金额对应的 ID）。
- 观察 dict 包含：`current_player`、`legal_actions`、`info_state_string`、`is_terminal`、`returns`；非终局时含 **`pot`**、**`stacks`**、**`action_id_to_info`**（每条合法动作的 type/amount）。
- **pot()**、**stacks()**、**stack_for_player(player)**、**min_raise_to()**、**action_id_to_info()**；**get_current_street_name()**、**get_hole_cards_str(player)**、**get_board_cards_str()** 供抽象层生成状态键。

#### 算法层（阶段 B + Step 2–4）

| 组件 | 位置 | 说明 |
|------|------|------|
| Leduc CFR+ | `algorithms/leduc_cfr.py` | 使用 OpenSpiel CFR+ 在 Leduc 上训练至 exploitability < 目标值，支持进度条与提前终止。 |
| 策略 IO | `algorithms/policy_io.py` | TabularPolicy ↔ JSON（含 game 名与参数），供 Leduc 保存/加载；**格式仅适用于 OpenSpiel 标准游戏**，不能直接用于 6-max 抽象策略表。 |
| 抽象定义 | `algorithms/abstraction.py` | **行动抽象**：BET_POT_RATIOS、all_in/check_or_call/fold 桶；`bet_size_to_bucket`、`bucket_to_approx_ratio`。**信息抽象**：PREFLOP_HAND_BUCKETS；**`hand_to_preflop_bucket(hole_cards_str)`**（169 类）、**`board_to_flop_bucket(board_cards_str)`**（rainbow/twotone/monotone）；**`get_abstract_state_key_from_env(env, action_sequence)`**（Step 2）。 |
| 子游戏策略对接 | `algorithms/subgame_strategy.py` | `AbstractStrategyLookup`、`UniformAbstractStrategy`；**`map_abstract_to_legal` 真实逻辑**（按 action_id_to_info 将抽象桶映射到 legal action 分布）（Step 3）；**`JsonAbstractStrategyLookup`** 从 JSON 加载策略，支持 `default` 键（Step 4）。 |

#### 脚本与数据

| 类型 | 脚本/文件 | 说明 |
|------|------------|------|
| 验收 | `verify_openspiel.py`、`verify_6max_env.py`、`verify_env_wrapper.py`、`verify_phase_b.py` | 四者均通过（退出码 0）即表示环境与阶段 A/B 达标；`verify_env_wrapper.py` 含 Step 1 的 pot/stacks/action_id_to_info 检查。 |
| 训练 | `train_leduc_cfr.py` | Leduc CFR+ 训练，输出 `data/leduc_cfr_policy.json`。 |
| 评估 | `evaluate_leduc.py` | 加载 Leduc 策略，计算 exploitability、vs 随机/自身期望值与采样均值。 |
| 6-max 策略管线 | `run_six_max_with_strategy.py` | 使用 JSON 抽象策略在 6-max 中运行 N 手（Step 1–4 管线验收）。 |
| 可视化 | `six_max_viewer.py` | Tkinter 6-max 牌桌 UI，使用 `action_to_string` 显示动作。 |
| 数据 | `data/leduc_cfr_policy.json` | 阶段 B 验收与评估所需；`data/subgame_strategy_example.json` 为 6-max 抽象策略示例；`leduc_test.json` 未被引用，可视为历史产物。 |

#### 文档

- **README.md**：快速开始、验收脚本表、项目结构、验收评估说明、当前进度。
- **docs/PROJECT.md**：目标、技术栈、阶段 A/B 完成表、后续阶段概要。
- **docs/OPENSPIEL_ACCEPTANCE_AND_NEXT_STEPS.md**：验收报告、阶段 A/B/C 可执行清单与建议顺序。
- **docs/ABSTRACTION_6MAX.md**：6-max 信息抽象与行动抽象设计（手牌/公共牌/下注桶、抽象状态键格式、与 env 对接要点）。

### 2.2 当前缺口与后续工作

1. **真实 6-max 子游戏 CFR 训练**  
   - 当前仅使用手写/示例 JSON 策略（`data/subgame_strategy_example.json`）在 6-max 中运行；**未**对真实 6-max 子游戏（如 BTN vs BB 单挑 flop）运行 CFR/MCCFR 求解。若需运行，为长时间训练，需单独执行。

2. **抽象动作序列（action_sequence）**  
   - `get_abstract_state_key_from_env(env, action_sequence)` 中 `action_sequence` 目前由调用方传入（常为空）；尚未从对局历史自动追踪并填入已执行的抽象动作序列。

3. **策略网络与实时决策**  
   - 未实现：用 (info_state, action_dist) 或 (state, value) 训练网络、在 6-max 中实时采样动作。

4. **阶段 C（对手建模与实战）**  
   - 未启动：对手统计、exploit 模块、真实 HH 解析、offline 评估、A/B 测试。

---

## 三、下一步工作内容分析

按依赖关系与文档中的阶段划分，建议顺序如下。

### 3.1 补齐 6-max 环境对抽象与策略映射的支撑（优先） — **已完成**

**目标**：让算法层能从「当前状态」得到 pot、stack、以及每个 legal action 的语义，从而使用 `abstraction` 与 `map_abstract_to_legal`。

- **在 `env/six_max.py`（或通过 state 封装）中提供**：  
  - 当前 pot 大小（或 pot 与 effective stack）。  
  - 当前玩家有效 stack。  
  - `action_id_to_info`：`legal_actions()` 中每个 action_id 对应的 `{type: "fold"|"check"|"call"|"bet"|"raise"|"all_in", amount?: number}`（若可解析自 OpenSpiel state/action_to_string，或查阅 pokerkit_wrapper 的 action 编码）。  
- **验收**：写一小段脚本或单元测试，在 6-max 若干决策点上断言 pot/stack 与部分 action 的 type/amount 与预期一致。

**依赖**：仅依赖现有 env 与 OpenSpiel/pokerkit_wrapper，无新算法依赖。  
**产出**：env 可被抽象层与 `map_abstract_to_legal` 可靠调用。

### 3.2 实现抽象层与 env 的对接（信息抽象） — **已完成**

**目标**：从 6-max 当前状态得到「抽象状态键」，供策略表或后续网络查询。

- **实现 `hand_to_preflop_bucket(hole_cards_str)`**：  
  - 与 `info_state_string` 或底层手牌表示一致（如 "AsKh" 或 OpenSpiel 的牌编码），映射到 `PREFLOP_HAND_BUCKETS` 或更细/更粗的桶。  
- **实现 `board_to_flop_bucket(board_cards_str)`**（以及可选的 turn/river 桶）：  
  - 按 ABSTRACTION_6MAX 中的牌面特征（同花性、连接度、高牌数等）离散化。  
- **从 env 观察/state 中解析**：当前 street、手牌字符串、公共牌字符串、到当前决策点为止的「抽象动作序列」（需与 action_id_to_info 配合，把已执行动作转为抽象桶序列）。  
- **验收**：在若干典型 6-max 状态上，检查 `get_abstract_state_key(...)` 与手牌/牌面桶是否与文档一致、无越界或未覆盖。

**依赖**：建议在 3.1 之后做，以便用真实 action 语义构建 action_sequence。

### 3.3 实现 map_abstract_to_legal 的真实逻辑 — **已完成**

**目标**：给定抽象动作上的概率分布与当前 legal_actions，得到 env 的 action ID 上的分布（含非标准尺度时选最近桶或插值）。

- **实现**：  
  - 使用 env 提供的 `action_id_to_info`、pot、min_raise、stack。  
  - 将每个 legal action_id 映射到抽象桶（fold→fold，check/call→check_or_call，bet/raise→按 amount/pot 用 `bet_size_to_bucket`，all-in→all_in）。  
  - 将抽象动作上的概率分配到对应 action_id（同一桶多个 action 时按比例或选最近）。  
  - 处理「抽象策略给出某桶但 legal 中无该桶」时的 fallback（如选最近桶或 check/call）。  
- **验收**：在若干 6-max 决策点上，给定人工构造的抽象分布，检查输出 action 分布合法、和为 1、与抽象意图一致。

**依赖**：3.1（action_id_to_info、pot、stack）。

### 3.4 第一个 6-max 子游戏 CFR 与策略加载（B4 实质化） — **管线已完成**

**目标**：选一个极小 6-max 子游戏（如 BTN open vs BB call 后的单挑 flop，或极简行动抽象），用 CFR/MCCFR 求解，并将策略接入现有接口。

**当前实现**：已实现 JSON 策略加载（`JsonAbstractStrategyLookup`）、示例策略 `data/subgame_strategy_example.json`、以及 `scripts/run_six_max_with_strategy.py` 在 6-max 中按抽象状态查询策略并执行对局。**未**在 6-max 上运行 CFR 训练；若要对真实 6-max 子游戏做 CFR 求解，将是一次长时间训练，需单独执行并等待。

- **子游戏定义**：  
  - 固定人数、位置、stack、到达 flop 的 line；flop 上限制行动抽象（如 check、bet 50%、bet 100%、all-in）。  
  - 可用当前 `abstraction.py` 的桶，或先做更粗的桶以控制状态数。  
- **求解**：  
  - 若 OpenSpiel 的 python_pokerkit_wrapper 支持从指定状态开始，则在该子游戏上跑 CFR+；否则需要自定义「子游戏状态枚举」或接入外部求解器。  
- **策略存储与加载**：  
  - 定义子游戏「抽象状态键」与「抽象动作」的格式，与 `get_abstract_state_key` 一致。  
  - 实现一个 `AbstractStrategyLookup`：从 JSON（或其它格式）加载该子游戏的 (abstract_state_key → action_probs)，供 6-max 在对应子游戏范围内查询。  
- **对接**：  
  - 在 6-max 中，当识别到「当前处于该子游戏」时，用上述 lookup + `map_abstract_to_legal` 得到 action 分布并采样；否则可回退到 `UniformAbstractStrategy` 或简单规则。  
- **验收**：  
  - 子游戏策略加载成功；在仅含该子游戏的 6-max 测试中，AI 能按策略表做出合理动作（可先与随机 bot 对比 EV）。

**依赖**：3.1、3.2、3.3；可选地先做 3.2/3.3 的简化版（例如只做 flop 单街、少量桶）。

### 3.5 策略网络与实时决策（可选，为 SOTA 铺路）

- 用 Leduc 或 3.4 子游戏的 (info_state / 抽象状态, action_dist) 作为监督数据，训练策略网络（或策略+价值双头）。  
- 在 6-max 中：将当前状态编码为网络输入，输出抽象动作分布，再经 `map_abstract_to_legal` 转为 action ID。  
- 与规则 bot 或自博弈验证稳定性和 EV。  

**依赖**：3.3、3.4 更稳后再做更高效。

### 3.6 阶段 C：对手建模与实战

- **对手建模与 exploit**：在 6-max 对局中记录 VPIP/PFR/3bet/CB 等统计或轨迹，输入到策略模块或单独网络，输出针对该对手的调整策略；与偏差 bot 对战评估 EV 提升。  
- **真实 HH 与 offline**：解析手牌历史为与当前 env 一致的状态/动作序列，做 offline 分析或 offline RL 微调；A/B 测试或人机对战，用 BB/100 与方差评估水平。  

**依赖**：至少有一条可用的 6-max 策略管线（3.4 + 3.3），再叠加对手特征与数据。

---

## 四、建议的近期执行顺序（小结）

**3.1–3.4 已完成**：env 已暴露 pot/stack/action_id_to_info；信息抽象（hand/board bucket、get_abstract_state_key_from_env）已实现；map_abstract_to_legal 已实现；JSON 策略加载与 `run_six_max_with_strategy.py` 已就绪。项目已具备「在 6-max 中使用抽象策略」的完整管线。

**后续可选方向**（无强制顺序）：  
- **3.4 深化**：对真实 6-max 子游戏运行 CFR 训练并导出策略 JSON（长时间训练）。  
- **3.5**：策略网络与实时决策。  
- **3.6**：阶段 C（对手建模与实战）。  
- **动作序列**：在对局中追踪已执行动作并填入 `action_sequence`，以支持更细的抽象状态键。

---

## 五、参考

- 项目总览与验收：根目录 **README.md**
- 阶段与技术栈：**docs/PROJECT.md**
- 阶段 A/B/C 清单：**docs/OPENSPIEL_ACCEPTANCE_AND_NEXT_STEPS.md**
- 抽象设计：**docs/ABSTRACTION_6MAX.md**
