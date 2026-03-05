# 6-max NLHE 抽象设计

供 CFR/子游戏求解器与策略网络使用的信息抽象与行动抽象定义。

---

## 一、信息抽象（状态聚类）

### 1.1 手牌抽象（Hand Abstraction）

将 169 种 preflop 牌型（或 1326 种手牌组合）映射到有限个「手牌桶」，使同一桶内手牌在策略上可视为等价。

**Preflop 建议桶（示例，可按需增删）：**

| 桶名 | 说明 | 示例 |
|------|------|------|
| AA | 口袋 AA | AA |
| KK | 口袋 KK | KK |
| QQ | 口袋 QQ | QQ |
| JJ | 口袋 JJ | JJ |
| TT | 口袋 TT | TT |
| 99-22 | 其余口袋对（可再拆为 99-77, 66-22 等） | 99, 88, …, 22 |
| AKs | 同花 AK | AsKs |
| AKo | 非同花 AK | AsKh |
| AQs-A2s | 同花大牌 | AQs, AJs, … |
| AQo-A2o | 非同花大牌 | AQo, AJo, … |
| KQs-K9s | 同花 Kx | KQs, KJs, … |
| … | 其余按强度/同花/连接度聚类 | … |

实现时可用 **E[HS]（手牌强度期望）** 或 **E[HS²]** 等标量对 hand combo 聚类（k-means 或分位数），或采用现成 169 类 + 同花/非同花再合并为 ~50–100 桶。

**Postflop**：在公共牌确定后，对「手牌+公共牌」的 equity 或 hand strength 做聚类，得到每个 board 下的手牌桶（桶数可随 street 递增）。

### 1.2 公共牌抽象（Board Abstraction）

将 flop/turn/river 的牌面聚类，减少不同 board 的数量。

- **Flop**：按牌面特征（同花性、连接度、高牌数量、对子等）离散化，例如：
  - 同花 / 两同花 / 彩虹
  - 高牌数：0/1/2/3
  - 是否成对、是否顺子面
- **Turn/River**：在 flop 聚类基础上再按新牌更新特征并聚类。

代码中可用「牌面特征向量 + 离散化规则」或预计算 lookup 表。

---

## 二、行动抽象（Action Abstraction）

将连续或大量下注尺度离散化为有限个「行动桶」，便于 CFR 在有限动作空间上求解。

### 2.1 Preflop

- **开池**：fold, limping(1bb), open 2x, 2.2x, 2.5x, 3x（及可选 4x 等）。
- **面对 open**：fold, call, 2.5x 3bet, 3x 3bet, 4x 3bet, 5x 3bet, all-in。
- **面对 3bet**：fold, call, 4bet（尺度可再拆）, all-in。

具体尺度与人数、位置相关，可在 `algorithms/abstraction.py` 中以常量或配置给出。

### 2.2 Postflop（每街）

以 **pot 比例** 为主，便于不同 stack 复用：

| 桶名 | 含义（占 pot 比例） | 典型用途 |
|------|---------------------|----------|
| check | 过牌 | 无下注时 |
| 25% | 约 1/4 pot | 小额下注 |
| 33% | 约 1/3 pot | 小额/试探 |
| 50% | 半 pot | 常规 |
| 75% | 3/4 pot | 价值/诈唬 |
| 100% | pot | 大注 |
| 150% | 1.5 pot | overbet |
| all-in | 全下 | 根据 stack 与 pot 计算 |

非标准尺度（真实人类下注）在运行时映射到**最近桶**或**插值**相邻桶的策略。

### 2.3 实现要点

- 每个决策点根据 **当前 pot、有效 stack、历史动作** 计算合法「抽象动作」集合（fold / check-call / bet 若干桶 / raise 若干桶 / all-in）。
- 真实动作映射到抽象动作：按 bet/raise 占 pot 比例落入对应桶，再在策略层用该桶或插值得到具体金额。

---

## 三、抽象状态键（供策略表/网络使用）

子游戏或 CFR 产出的策略以「抽象状态」为键。建议键格式（示例）：

- **Preflop**：`preflop_{position}_{hand_bucket}_{action_history}`  
  例如 `preflop_btn_AKs_open`、`preflop_bb_99_vs_open`。
- **Postflop**：`{street}_{board_bucket}_{hand_bucket}_{pot_relative}_{action_history}`  
  例如 `flop_rainbow_strong_1c_check`、`turn_2flush_medium_2b_bet50`。

具体格式在 `algorithms/abstraction.py` 中实现，并与 6-max 环境的 `info_state_string` 或自定义观察对接。

---

## 四、与 6-max 环境对接

- **env**：`env/six_max.py` 提供 `legal_actions()`（具体金额）、`info_state_string`、`pot()`、`stacks()`、`action_id_to_info()`；以及 `get_current_street_name()`、`get_hole_cards_str(player)`、`get_board_cards_str()` 供抽象层生成状态键。
- **抽象层**：`algorithms/abstraction.py` 提供 `hand_to_preflop_bucket(hole_cards_str)`、`board_to_flop_bucket(board_cards_str)`、`get_abstract_state_key_from_env(env, action_sequence)`；将当前 state 转为 (hand_bucket, board_bucket, action_history_bucket)，再查表或网络得到「抽象动作」上的分布。
- **反映射**：`algorithms/subgame_strategy.py` 的 `map_abstract_to_legal` 根据 `action_id_to_info` 与 pot 将抽象动作分布映射到 `legal_actions()` 上的分布；若抽象动作为「bet 50% pot」，则分配到对应桶的合法动作（可多动作均分该桶概率）。

详见 `algorithms/abstraction.py` 与 `algorithms/subgame_strategy.py`。
