# Copyright 2025 Poker AI Project. 6-max NLHE environment wrapper.
"""
6-max No-Limit Texas Hold'em 环境封装。
基于 OpenSpiel 的 python_pokerkit_wrapper，提供与 OpenSpiel Environment 风格一致的接口，
供算法层创建对局、步进、获取观察与合法动作、判断终局与 returns。
并暴露 pot、stack、action_id_to_info 供抽象与策略映射使用。
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

# 确保 python_pokerkit_wrapper 已注册（需已安装 pokerkit）
try:
    import pyspiel
    from open_spiel.python.games import pokerkit_wrapper  # noqa: F401
except ImportError:
    pyspiel = None
    pokerkit_wrapper = None

# 与 OpenSpiel pokerkit_wrapper 约定一致
ACTION_FOLD = 0
ACTION_CHECK_OR_CALL = 1


# 默认 6-max 参数：100BB，SB=0.5BB, BB=1
DEFAULT_NUM_PLAYERS = 6
DEFAULT_BIG_BLIND = 100
DEFAULT_SMALL_BLIND = 50
DEFAULT_STACK_BB = 100  # 每人 100BB


def _make_stack_sizes(num_players: int, stack_bb: float, big_blind: int) -> str:
    """每人 stack_bb * big_blind 筹码，空格分隔."""
    stack = int(stack_bb * big_blind)
    return " ".join(str(stack) for _ in range(num_players))


def _sample_chance(state, rng: Optional[random.Random] = None) -> None:
    """若当前为 chance 节点，则随机采样并 apply，直到非 chance。"""
    rng = rng or random
    while state.is_chance_node():
        outcomes = state.chance_outcomes()
        action = rng.choice([a for a, _ in outcomes])
        state.apply_action(action)


class SixMaxEnv:
    """
    6-max NLHE 环境：封装 OpenSpiel python_pokerkit_wrapper，
    提供 reset/step、当前玩家、合法动作、观察、终局与 returns。
    与 OpenSpiel RL Environment 风格一致，便于算法层复用。
    """

    def __init__(
        self,
        num_players: int = DEFAULT_NUM_PLAYERS,
        small_blind: int = DEFAULT_SMALL_BLIND,
        big_blind: int = DEFAULT_BIG_BLIND,
        stack_bb: float = DEFAULT_STACK_BB,
        seed: Optional[int] = None,
    ):
        if pyspiel is None:
            raise ImportError("pyspiel 未安装；请先安装 OpenSpiel。")
        if "python_pokerkit_wrapper" not in pyspiel.registered_names():
            raise ImportError(
                "python_pokerkit_wrapper 未注册；请安装 pokerkit: pip install pokerkit"
            )
        self._num_players = num_players
        self._small_blind = small_blind
        self._big_blind = big_blind
        self._stack_bb = stack_bb
        self._rng = random.Random(seed)

        stack_sizes = _make_stack_sizes(num_players, stack_bb, big_blind)
        self._game_params = {
            "variant": "NoLimitTexasHoldem",
            "num_players": num_players,
            "blinds": f"{small_blind} {big_blind}",
            "stack_sizes": stack_sizes,
        }
        self._game: Optional[Any] = None
        self._state: Optional[Any] = None
        self._game = pyspiel.load_game("python_pokerkit_wrapper", self._game_params)
        self._state = self._game.new_initial_state()
        _sample_chance(self._state, self._rng)

    @property
    def game(self):
        """底层 OpenSpiel Game."""
        return self._game

    @property
    def state(self):
        """当前 OpenSpiel State（决策节点或终局）。"""
        return self._state

    def num_players(self) -> int:
        return self._num_players

    def reset(self) -> dict[str, Any]:
        """
        开始新的一手牌，推进过 chance 节点后返回第一个决策点的观察。
        Returns:
            observation: dict，含 current_player, legal_actions, info_state_string,
                         is_terminal, returns（终局时有效）。
        """
        self._state = self._game.new_initial_state()
        _sample_chance(self._state, self._rng)
        return self._get_observation()

    def step(self, action: int) -> dict[str, Any]:
        """
        执行当前玩家的动作，并推进 chance 节点直到下一决策点或终局。
        Args:
            action: 合法动作 ID（与 state.legal_actions() 一致）。
        Returns:
            与 reset 相同结构的 observation；若 is_terminal 则 returns 有效。
        """
        if self._state.is_terminal():
            return self._get_observation()
        legal = self._state.legal_actions()
        if action not in legal:
            raise RuntimeError(f"非法动作 {action}，合法动作: {legal}")
        self._state.apply_action(action)
        _sample_chance(self._state, self._rng)
        return self._get_observation()

    def current_player(self) -> int:
        """当前行动玩家；若已终局则行为未定义，请先检查 is_terminal()."""
        return self._state.current_player()

    def legal_actions(self) -> list[int]:
        """当前玩家的合法动作 ID 列表。"""
        return list(self._state.legal_actions())

    def is_terminal(self) -> bool:
        return self._state.is_terminal()

    def returns(self) -> list[float]:
        """仅当 is_terminal() 时有效；每人收益（筹码变化）。"""
        return list(self._state.returns())

    def _get_wrapped_state(self):
        """底层 pokerkit State，供 pot/stack/action 解析。若无则返回 None。"""
        return getattr(self._state, "_wrapped_state", None)

    def pot(self) -> int:
        """当前底池总金额（决策点或终局）。终局时可为 0（已分配）。"""
        ws = self._get_wrapped_state()
        if ws is not None:
            return int(ws.total_pot_amount)
        s = self._state.to_struct()
        return int(getattr(s, "pot_size", 0))

    def stacks(self) -> List[int]:
        """当前每人筹码量（与玩家索引对应）。"""
        ws = self._get_wrapped_state()
        if ws is not None:
            return [int(s) for s in ws.stacks]
        s = self._state.to_struct()
        return list(getattr(s, "stacks", [0] * self._num_players))

    def stack_for_player(self, player: int) -> int:
        """指定玩家当前筹码。"""
        return self.stacks()[player]

    def min_raise_to(self) -> Optional[int]:
        """当前街最小合法「加注到」总额（total to put on this street）。无加注选项时返回 None。"""
        ws = self._get_wrapped_state()
        if ws is None:
            return None
        if not getattr(ws, "can_complete_bet_or_raise_to", lambda: False)():
            return None
        return int(getattr(ws, "min_completion_betting_or_raising_to_amount", None) or 0)

    def action_id_to_info(self) -> Dict[int, Dict[str, Any]]:
        """
        当前决策点每个合法动作的语义。
        Returns:
            action_id -> {"type": "fold"|"check"|"call"|"bet"|"raise"|"all_in", "amount": int?, "total_to_put": int?}
            amount: 本动作新增投入（用于 pot 比例计算）；total_to_put: 本街总投入（仅 bet/raise/all_in）。
        """
        legal = self.legal_actions()
        if not legal:
            return {}
        ws = self._get_wrapped_state()
        cur = self.current_player()
        stacks = self.stacks()
        pot = self.pot()
        stack_cur = stacks[cur] if cur < len(stacks) else 0

        # 当前玩家在本街已投入
        if ws is not None:
            bets = getattr(ws, "bets", None)
            current_bet = int(bets[cur]) if (bets is not None and cur < len(bets)) else 0
        else:
            current_bet = 0

        out: Dict[int, Dict[str, Any]] = {}
        for a in legal:
            if a == ACTION_FOLD:
                out[a] = {"type": "fold", "amount": 0}
            elif a == ACTION_CHECK_OR_CALL:
                call_amt = 0
                if ws is not None:
                    call_amt = int(getattr(ws, "checking_or_calling_amount", 0) or 0)
                out[a] = {"type": "check" if call_amt == 0 else "call", "amount": call_amt}
            else:
                # action >= 2: complete bet or raise to total `a` on this street
                total_to_put = a
                increment = total_to_put - current_bet
                is_all_in = (increment >= stack_cur) or (stack_cur <= 0)
                out[a] = {
                    "type": "all_in" if is_all_in else ("bet" if current_bet == 0 else "raise"),
                    "amount": increment,
                    "total_to_put": total_to_put,
                }
        return out

    def get_current_street_name(self) -> str:
        """当前街名：preflop / flop / turn / river。非决策点或终局时可为 preflop。"""
        ws = self._get_wrapped_state()
        if ws is None:
            return "preflop"
        idx = getattr(ws, "street_index", None)
        if idx is None:
            return "preflop"
        names = ["preflop", "flop", "turn", "river"]
        return names[idx] if 0 <= idx < len(names) else "preflop"

    def get_hole_cards_str(self, player: int) -> str:
        """指定玩家的手牌字符串，如 'AsKh'（无空格）。无手牌时返回空串。"""
        ws = self._get_wrapped_state()
        if ws is None:
            return ""
        hc = getattr(ws, "hole_cards", None)
        if not hc or player >= len(hc):
            return ""
        cards = hc[player]
        if not cards:
            return ""
        return "".join(f"{c.rank.value}{c.suit.value}" for c in cards)

    def get_board_cards_str(self) -> str:
        """当前已发的公共牌字符串，如 'AsKhQd'（按街顺序，无空格）。"""
        ws = self._get_wrapped_state()
        if ws is None:
            return ""
        board = getattr(ws, "board_cards", None)
        if not board:
            return ""
        out = []
        for street_cards in board:
            for c in street_cards:
                out.append(f"{c.rank.value}{c.suit.value}")
        return "".join(out)

    def _get_observation(self) -> dict[str, Any]:
        obs: Dict[str, Any] = {
            "current_player": self._state.current_player() if not self._state.is_terminal() else -1,
            "legal_actions": self.legal_actions() if not self._state.is_terminal() else [],
            "is_terminal": self._state.is_terminal(),
            "returns": self.returns() if self._state.is_terminal() else [0.0] * self._num_players,
        }
        if self._game.get_type().provides_information_state_string:
            pid = obs["current_player"]
            obs["info_state_string"] = (
                self._state.information_state_string(pid) if pid >= 0 else ""
            )
        else:
            obs["info_state_string"] = ""
        if not self._state.is_terminal():
            obs["pot"] = self.pot()
            obs["stacks"] = self.stacks()
            obs["action_id_to_info"] = self.action_id_to_info()
        return obs


def create_six_max_env(
    num_players: int = DEFAULT_NUM_PLAYERS,
    small_blind: int = DEFAULT_SMALL_BLIND,
    big_blind: int = DEFAULT_BIG_BLIND,
    stack_bb: float = DEFAULT_STACK_BB,
    seed: Optional[int] = None,
) -> SixMaxEnv:
    """工厂函数：创建 6-max 环境。"""
    return SixMaxEnv(
        num_players=num_players,
        small_blind=small_blind,
        big_blind=big_blind,
        stack_bb=stack_bb,
        seed=seed,
    )
