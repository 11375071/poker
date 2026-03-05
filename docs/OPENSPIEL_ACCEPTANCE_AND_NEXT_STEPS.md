# OpenSpiel 环境验收报告与下一步工作

## 〇、本次验收运行结果（复验用）

在项目根目录执行：

```powershell
.venv\Scripts\python.exe scripts\verify_openspiel.py
```

- **退出码 0**：验收通过。
- 若使用 PowerShell，请用 `Set-Location c:\Users\user\Desktop\poker` 后执行上述命令，不要使用 `cd /d` 与 `&&`。

当前状态（与下表一致）：pyspiel/CFR/Leduc/Kuhn/RL 环境均可用；`python_pokerkit_wrapper` 已可用（需已安装 `pokerkit`）；`universal_poker` 未注册（未编译 C++ universal_poker）。

---

## 一、验收结果摘要

| 项目 | 状态 | 说明 |
|------|------|------|
| pyspiel / Python API 导入 | 通过 | 可正常使用 `pyspiel`、`rl_environment`、`cfr`、`exploitability`、`policy` |
| 扑克相关游戏 | 部分可用 | 见下表 |
| Kuhn Poker 对局 | 通过 | 可创建状态、随机打完一局并得到 returns |
| Leduc Poker 对局 | 通过 | 同上 |
| Python CFR (Leduc) | 通过 | 20 次迭代可跑通，exploitability 约 0.45（未收敛） |
| universal_poker | 未注册 | 当前安装中未编译 C++ universal_poker，仅 Python 扑克游戏可用 |
| RL Environment | 通过 | `rl_environment.Environment("kuhn_poker")` 可用 |
| pokerkit（6-max 需） | 已安装 | 安装后 `python_pokerkit_wrapper` 可用，支撑 6-max 环境与 Step 1–4 管线 |

### 当前可用的扑克类游戏

- **kuhn_poker**：2–10 人，默认可加载，适合算法验证。
- **leduc_poker**：2–10 人，默认可加载，适合 CFR/RL 实验。
- **python_kuhn_poker**：2 人，Python 实现。
- **python_liars_poker**：2–10 人。
- **repeated_leduc_poker**：重复 Leduc，多手。

**说明**：当前环境**没有** 6-max 德州（universal_poker 未注册，python_pokerkit_wrapper 依赖未安装）。要支撑 6-max，需要二选一或同时做：  
① 从源码编译 OpenSpiel 并启用 `universal_poker`；  
② 安装 `pokerkit` 并使用 `python_pokerkit_wrapper`（若 OpenSpiel 已注册该游戏）。

---

## 二、验收脚本使用方式

```bash
# 在项目根目录下，使用已安装 OpenSpiel 的 venv
.venv\Scripts\python.exe scripts\verify_openspiel.py
```

退出码 0 表示验收通过。

---

## 三、下一步工作具体内容（按优先级）

### 阶段 A：环境与 6-max 支撑（必做）

1. **确认 6-max 游戏来源**
   - **方案 1**：从 [OpenSpiel 源码](https://github.com/google-deepmind/open_spiel) 本地编译，打开 `universal_poker`，并确认是否支持 `numPlayers=6`（需查文档或源码）。
   - **方案 2**：安装 `pokerkit`（`pip install pokerkit`），在 OpenSpiel 中注册/使用 `python_pokerkit_wrapper`，用其 No-Limit Texas Hold’em 支持 6 人。
   - 建议：先用方案 2 快速打通 6-max 环境；若需与 C++ 求解器/ACPC 格式一致，再补方案 1。

2. **项目结构**
   - 在仓库根目录建立清晰模块，例如：
     - `env/` 或 `game/`：封装 OpenSpiel/pokerkit 的 6-max 接口（创建对局、步进、获取观察等）。
     - `scripts/`：保留验收脚本、评估脚本、训练入口。
     - `algorithms/`：CFR/MCCFR、RL 等，与 OpenSpiel 的 `algorithms` 区分或包装。
   - 增加 `requirements.txt`，写明 `open_spiel` 与（若用方案 2）`pokerkit` 的版本。

3. **6-max 环境封装与验收**
   - 实现“创建 6 人 NLHE 对局 → 步进 → 获取当前玩家观察与合法动作 → 判断终局与 returns”的接口。
   - 写一个类似 `verify_openspiel.py` 的脚本：跑若干随机 6-max 手牌，不报错并输出每手 returns，作为 6-max 环境验收。

### 阶段 B：算法与策略（在 6-max 可用后）

4. **在 Leduc 上打通完整管线（建议先做）**
   - 用 OpenSpiel 自带的 `cfr` 或 `cfr_plus` 在 Leduc 上训练到 exploitability 足够低（如 &lt; 0.01）。
   - 将得到的 TabularPolicy 导出/序列化，并写一个“加载策略 + 与随机/简单 bot 对战”的评估脚本，确认 EV 与 exploitability 一致。
   - 目的：在 6-max 之前，先在一款小游戏上跑通“训练 → 保存 → 加载 → 评估”的闭环，便于后续复用到 6-max 或抽象子游戏。

5. **6-max 抽象与子游戏**
   - 设计 6-max 的**信息抽象**（手牌/公共牌聚类）与**行动抽象**（下注尺度离散化）。
   - 选择少量关键子游戏（如 BTN open vs BB defend、单挑底池 flop）用 CFR/MCCFR 求解，或接入现有求解器（若使用 universal_poker + ACPC 格式）。
   - 将子游戏策略与 6-max 环境对接：根据当前状态映射到抽象，查询策略并映射回具体动作（含非标准尺度时的插值/舍入策略）。

6. **策略网络与实时决策（可选，为 SOTA 做准备）**
   - 用 Leduc/简化 6-max 子游戏上得到的 (info_state, action_dist) 或 (state, value) 作为监督数据，训练一个策略网络（或策略+价值双头）。
   - 在 6-max 环境中用该网络做实时动作采样，并做自博弈或与规则 bot 对战，验证稳定性和 EV。

### 阶段 C：对手建模与实战（后续）

7. **对手建模与 exploit**
   - 在 6-max 环境中记录对手的统计（VPIP/PFR/3bet/CB 等）或轨迹，输入到策略网络或单独模块，输出“针对该对手的调整策略”。
   - 与固定策略 bot（如 GTO 或人工设计的偏差 bot）对战，评估 exploit 带来的 EV 提升。

8. **真实人类对局与数据**
   - 若有手牌历史（HH），解析为与当前 6-max 环境一致的状态/动作序列，做 offline 分析或 offline RL 微调。
   - 设计 A/B 测试或人机对战流程，用长期 BB/100 与方差评估是否达到目标水平。

---

## 四、下一步工作具体内容（可执行清单）

按优先级与依赖关系执行，每项带验收标准。

### 阶段 A：环境与 6-max 支撑（必做） — **已完成**

| 序号 | 任务 | 具体操作 | 验收标准 |
|------|------|----------|----------|
| A1 | 安装 pokerkit | `pip install pokerkit`（在 .venv 中） | `python -c "import pokerkit; from open_spiel.python.games import pokerkit_wrapper"` 不报错；`scripts\verify_openspiel.py` 中不再提示 "No module named 'pokerkit'" |
| A2 | 项目根目录 requirements.txt | 新建 `requirements.txt`，包含 open_spiel（或本地路径）、numpy、absl 等；可选 pokerkit | `pip install -r requirements.txt` 可复现环境 |
| A3 | 项目目录结构 | 新建 `env/`（或 `game/`）、`algorithms/` 包目录，`__init__.py` 占位 | 可从项目根 `from env import ...` 或等价方式导入 |
| A4 | 6-max 环境验收脚本 | 编写脚本：用 `python_pokerkit_wrapper` 创建 6 人 NLHE（如 100BB），随机打 N 手，输出每手 returns | 运行不报错，每手有 6 维 returns，终局状态正确 |
| A5 | 6-max 封装接口 | 在 `env/` 中封装：创建对局、step、当前玩家观察、合法动作、是否终局、returns | 可供后续算法层调用，接口与 OpenSpiel `Environment` 或 `Game` 风格一致 |

### 阶段 B：算法与策略（6-max 可用后） — **已完成**

| 序号 | 任务 | 具体操作 | 验收标准 |
|------|------|----------|----------|
| B1 | Leduc CFR 闭环 | `scripts/train_leduc_cfr.py`、`algorithms/leduc_cfr.py`、`policy_io.py` | 策略保存至 `data/leduc_cfr_policy.json`；`evaluate_leduc.py` 可复现 EV |
| B2 | Leduc 策略导出与评估脚本 | `scripts/evaluate_leduc.py`：加载策略、vs 随机/自身、exploitability + 采样均值 | 可复现 Leduc 收敛策略的 EV |
| B3 | 6-max 抽象设计 | `docs/ABSTRACTION_6MAX.md`、`algorithms/abstraction.py`（下注桶、手牌桶、抽象状态键） | 明确定义，供 CFR/求解器使用 |
| B4 | 子游戏 CFR/求解器 | Leduc CFR+ 跑通；`algorithms/subgame_strategy.py`（含 map_abstract_to_legal、JsonAbstractStrategyLookup）；`scripts/run_six_max_with_strategy.py` | 子游戏策略可加载；抽象→6-max 对接就绪；6-max 可使用 JSON 策略运行 |

**抽象与策略管线（Step 1–4）**：env 已暴露 pot/stack/action_id_to_info；信息抽象（hand/board bucket、get_abstract_state_key_from_env）与 map_abstract_to_legal 已实现；JSON 策略加载与 `run_six_max_with_strategy.py` 可验收。详见 `docs/CURRENT_STATE_AND_NEXT_STEPS.md`。

### 阶段 C：对手建模与实战（后续）

- 对手统计与 embedding；策略网络 + 实时决策；真实 HH 解析与 offline 评估。见第三节阶段 C 描述。

---

## 五、建议的近期执行顺序

1. **本周**：完成阶段 A（A1→A2→A3→A4→A5）  
   - 先安装 pokerkit 并复跑 `verify_openspiel.py`，再建 requirements.txt 与目录结构，最后实现 6-max 验收脚本与封装。

2. **接下来 1–2 周**：完成阶段 B 中的 Leduc 闭环（B1、B2）  
   - Leduc CFR 训练至收敛 → 导出策略 → 评估脚本。  
   - 并行或随后做 6-max 抽象与子游戏（B3、B4）。

3. **之后**：按阶段 B 的 B3/B4 与阶段 C 迭代，逐步逼近 6-max SOTA 与人类对局表现。

---

## 六、参考

- **项目总览与快速开始**：根目录 `README.md`
- **项目说明与阶段 A 完成情况**：`docs/PROJECT.md`
- 验收脚本：`scripts/verify_openspiel.py`（基础 OpenSpiel + Leduc/Kuhn/CFR）
- 6-max 验收脚本：`scripts/verify_6max_env.py`（需先 `pip install pokerkit`）
- 封装接口验收：`scripts/verify_env_wrapper.py`（阶段 A5）
- 阶段 B 验收：`scripts/verify_phase_b.py`（可选 `--skip_train`）
- OpenSpiel 文档与游戏列表：[OpenSpiel Docs](https://github.com/google-deepmind/open_spiel/blob/master/docs/README.md)
- 若使用 pokerkit：[pokerkit](https://github.com/niclan/pokerkit) 支持多种扑克变体与人数。
