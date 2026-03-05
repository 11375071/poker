#!/usr/bin/env python3
"""
6-max NLHE 环境可视化界面（Tkinter）。

牌桌风格 UI：
- Canvas 绘制椭圆形牌桌、六个座位、每座筹码与手牌
- 中央底池与公共牌（牌面）
- 底部操作区：弃牌 / 过牌或跟注 + 下注金额输入框

运行方式（在项目根目录）：
  python scripts/six_max_viewer.py
"""

import math
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox


def _ensure_project_root_on_path() -> None:
  root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  if root not in sys.path:
    sys.path.insert(0, root)


# 牌面显示：s/h/d/c -> Unicode 花色
_SUIT_SYMBOLS = {"s": "\u2660", "h": "\u2665", "d": "\u2666", "c": "\u2663"}
_SUIT_COLORS = {"s": "#000", "h": "#c00", "d": "#c00", "c": "#000"}


def _card_display(card_str: str) -> Tuple[str, str]:
  """将 'As'/'Kh' 转为显示文本与颜色。返回 (显示文本, 颜色)."""
  card_str = str(card_str).strip().lower()
  if len(card_str) >= 2:
    rank, suit = card_str[0].upper(), card_str[-1]
    sym = _SUIT_SYMBOLS.get(suit, suit)
    color = _SUIT_COLORS.get(suit, "#000")
    return f"{rank}{sym}", color
  return card_str, "#000"


def _flatten_board(board_cards: Any) -> List[Any]:
  """board_cards 可能按 street 嵌套，压平为一列。"""
  out = []
  if hasattr(board_cards, "__iter__") and not isinstance(board_cards, str):
    for x in board_cards:
      if hasattr(x, "__iter__") and not isinstance(x, str):
        out.extend(x)
      else:
        out.append(x)
  return out


def _card_to_display_str(c: Any) -> str:
  """将 pokerkit Card 或已为字符串的牌转为 'As'/'Kh' 风格供 _card_display 使用。"""
  if c is None:
    return "??"
  if isinstance(c, str):
    return c.strip()
  if hasattr(c, "__repr__"):
    r = repr(c)
    if len(r) >= 2 and r[0].upper() in "23456789TJQKA" and r[-1].lower() in "shdc":
      return r
  return str(c)


def _get_table_data(env: Any) -> Dict[str, Any]:
  """从 env.state 提取牌桌数据（筹码、底池、公共牌、手牌、街道、庄位）。"""
  data = {
    "stacks": [0] * 6,
    "bets": [0] * 6,
    "board": [],
    "hole_cards": [[] for _ in range(6)],
    "pot_total": 0,
    "current_player": -1,
    "is_terminal": False,
    "street_label": "",
    "button_index": -1,
  }
  try:
    state = env.state
    data["current_player"] = env.current_player() if not env.is_terminal() else -1
    data["is_terminal"] = env.is_terminal()
    ws = getattr(state, "_wrapped_state", None)
    if ws is None:
      return data
    if hasattr(ws, "stacks"):
      data["stacks"] = list(ws.stacks)[:6]
      data["stacks"] = [int(s) for s in data["stacks"]]
    if hasattr(ws, "bets"):
      data["bets"] = list(ws.bets)[:6]
      data["bets"] = [int(b) for b in data["bets"]]
    if hasattr(ws, "board_cards"):
      flat = _flatten_board(ws.board_cards)
      data["board"] = [_card_to_display_str(c) for c in flat]
    if hasattr(ws, "hole_cards"):
      for i, hc in enumerate(ws.hole_cards):
        if i < 6:
          lst = list(hc) if hasattr(hc, "__iter__") and not isinstance(hc, str) else [hc]
          data["hole_cards"][i] = [_card_to_display_str(c) for c in lst]
    if hasattr(ws, "total_pot_amount"):
      try:
        data["pot_total"] = int(ws.total_pot_amount)
      except Exception:
        pass
    if data["pot_total"] == 0 and hasattr(ws, "pots"):
      try:
        data["pot_total"] = sum(int(getattr(p, "amount", p)) for p in ws.pots)
      except Exception:
        pass
    if hasattr(ws, "street_index") and ws.street_index is not None:
      street_names = ["Preflop", "Flop", "Turn", "River"]
      idx = getattr(ws, "street_index", 0)
      data["street_label"] = street_names[idx] if 0 <= idx < len(street_names) else f"Street {idx}"
    if hasattr(ws, "button_index"):
      try:
        data["button_index"] = int(ws.button_index) if ws.button_index is not None else -1
      except Exception:
        pass
  except Exception:
    pass
  return data


class TableCanvas(tk.Canvas):
  """绘制牌桌、六座、筹码与牌面的 Canvas。"""

  def __init__(self, parent, **kwargs):
    super().__init__(parent, **kwargs)
    self._table_data: Dict[str, Any] = {}
    self._seat_radius = 42
    # 手牌画在座位旁，尺寸略小避免挤；公共牌在中心略大
    self._hole_card_w, self._hole_card_h = 36, 50
    self._hole_card_gap = 10
    self._board_card_w, self._board_card_h = 44, 62
    self._board_gap = 12
    self._seat_positions: List[Tuple[float, float]] = []

  def set_table_data(self, data: Dict[str, Any]) -> None:
    self._table_data = data
    self.draw()

  def _seat_angles(self) -> List[float]:
    """6 个座位角度（度），从顶部顺时针。"""
    return [90 + i * 60 for i in range(6)]  # 90, 150, 210, 270, 330, 30

  def _get_center_and_radius(self) -> Tuple[float, float, float]:
    w = self.winfo_reqwidth() or 400
    h = self.winfo_reqheight() or 320
    cx, cy = w / 2, h / 2
    r = min(w, h) * 0.38
    return cx, cy, r

  def draw(self) -> None:
    self.delete("all")
    w = int(self.winfo_reqwidth() or 400)
    h = int(self.winfo_reqheight() or 320)
    cx, cy = w / 2, h / 2
    rx, ry = w * 0.42, h * 0.38
    # 椭圆牌桌（绿色）
    self.create_oval(
        cx - rx, cy - ry, cx + rx, cy + ry,
        fill="#0d6b0d", outline="#0a520a", width=3,
        tags="table",
    )
    # 内圈（桌面）
    self.create_oval(
        cx - rx * 0.85, cy - ry * 0.85, cx + rx * 0.85, cy + ry * 0.85,
        fill="#1a7a1a", outline="#0d6b0d", width=1,
        tags="table",
    )

    data = self._table_data
    stacks = data.get("stacks", [0] * 6)
    bets = data.get("bets", [0] * 6)
    hole_cards = data.get("hole_cards", [[]] * 6)
    board = data.get("board", [])
    pot_total = data.get("pot_total", 0)
    current_player = data.get("current_player", -1)
    seat_r = self._seat_radius
    hw, hh = self._hole_card_w, self._hole_card_h
    hgap = self._hole_card_gap
    bw, bh = self._board_card_w, self._board_card_h
    bgap = self._board_gap
    # 座位到中心距离加大，人与人更疏朗（原 0.72 -> 0.88）
    seat_radius_place = min(rx, ry) * 0.88

    angles = self._seat_angles()
    self._seat_positions = []
    for i in range(6):
      rad = math.radians(angles[i])
      sx = cx + seat_radius_place * math.cos(rad)
      sy = cy + seat_radius_place * math.sin(rad)
      self._seat_positions.append((sx, sy))
      # 座位圈（当前玩家高亮）
      fill = "#ffd966" if i == current_player else "#8b7355"
      outline = "#333" if i == current_player else "#5c4a3a"
      self.create_oval(
          sx - seat_r, sy - seat_r, sx + seat_r, sy + seat_r,
          fill=fill, outline=outline, width=2, tags="seat",
      )
      # Player 标签
      self.create_text(
          sx, sy - seat_r - 6,
          text=f"P{i}" + (" (行动)" if i == current_player else ""),
          font=("Segoe UI", 10, "bold"), fill="#fff",
          tags="seat",
      )
      # 本街下注：画在座位与桌心之间（朝向底池），避免与外侧手牌重合
      bet_str = f"{bets[i]}" if (i < len(bets) and bets[i] > 0) else ""
      if bet_str:
        bet_offset = seat_r + 22
        bet_x = sx - math.cos(rad) * bet_offset
        bet_y = sy - math.sin(rad) * bet_offset
        self.create_text(
            bet_x, bet_y,
            text=bet_str,
            font=("Segoe UI", 9, "bold"), fill="#ffcc00",
            tags="seat",
        )
      # 筹码（座位下方）
      self.create_text(
          sx, sy + seat_r + 10,
          text=f"🪙 {stacks[i]}",
          font=("Segoe UI", 9), fill="#fff",
          tags="seat",
      )
      # 手牌：画在各自座位外侧（沿半径方向再往外一点），避免挤在中间
      # 牌中心在 座位 -> 桌缘 方向，距座位约 1.2 个座位半径，这样 P0~P5 的牌分别在六个方向
      hand_dist = seat_r * 1.35
      hcx = sx + math.cos(rad) * hand_dist
      hcy = sy + math.sin(rad) * hand_dist
      hc = hole_cards[i] if i < len(hole_cards) else []
      total_hw = 2 * hw + hgap
      start_hx = hcx - total_hw / 2
      for k, c in enumerate(hc[:2]):
        disp, color = _card_display(c)
        card_x = start_hx + k * (hw + hgap)
        card_y = hcy - hh / 2
        self.create_rectangle(
            card_x, card_y, card_x + hw, card_y + hh,
            fill="#fff", outline="#333", width=1, tags="card",
        )
        self.create_text(
            card_x + hw / 2, card_y + hh / 2,
            text=disp, font=("Segoe UI", 9, "bold"), fill=color, tags="card",
        )

    # 中央只放：街道名、底池、公共牌
    street_label = data.get("street_label", "")
    self.create_text(cx, cy - 42, text=street_label or "—", font=("Segoe UI", 11), fill="#ddd", tags="street")
    self.create_text(cx, cy - 22, text=f"底池 Pot: {pot_total}", font=("Segoe UI", 13, "bold"), fill="#fff", tags="pot")
    board_flat = board[:5] if isinstance(board, list) else []
    if board_flat:
      total_bw = len(board_flat) * bw + (len(board_flat) - 1) * bgap
      start_bx = cx - total_bw / 2
      for k, c in enumerate(board_flat):
        disp, color = _card_display(c)
        bx = start_bx + k * (bw + bgap) + bw / 2
        by = cy + 8
        self.create_rectangle(
            bx - bw / 2, by, bx + bw / 2, by + bh,
            fill="#fff", outline="#333", width=1, tags="board",
        )
        self.create_text(bx, by + bh / 2, text=disp, font=("Segoe UI", 10, "bold"), fill=color, tags="board")


class SixMaxViewer(tk.Tk):
  """6-max 环境可视化窗口（牌桌风格）。"""

  def __init__(self, seed: Optional[int] = 42) -> None:
    super().__init__()
    self.title("6-max NLHE 环境可视化")
    self.geometry("1200x780")

    try:
      from env import create_six_max_env
    except Exception as e:
      messagebox.showerror("导入失败", f"无法导入 env 包: {e}")
      raise

    self._env = create_six_max_env(num_players=6, seed=seed)
    self._obs = self._env.reset()

    self._legal_actions = []
    self._action_labels: Dict[int, str] = {}
    self._fold_actions: List[int] = []
    self._check_call_actions: List[int] = []
    self._bet_actions: List[Tuple[int, Optional[int]]] = []

    self._build_widgets()
    self._refresh_view()

  def _build_widgets(self) -> None:
    top_frame = ttk.Frame(self)
    top_frame.pack(side=tk.TOP, fill=tk.X, padx=8, pady=4)

    self.lbl_player = ttk.Label(top_frame, text="Current player: -")
    self.lbl_player.pack(side=tk.LEFT, padx=4)
    self.lbl_terminal = ttk.Label(top_frame, text="Terminal: False")
    self.lbl_terminal.pack(side=tk.LEFT, padx=12)

    ctrl_frame = ttk.Frame(top_frame)
    ctrl_frame.pack(side=tk.RIGHT)
    ttk.Button(ctrl_frame, text="新一手 (Reset Hand)", command=self._on_reset).pack(side=tk.LEFT, padx=4)
    ttk.Button(ctrl_frame, text="随机动作一步", command=self._on_random_step).pack(side=tk.LEFT, padx=4)
    ttk.Button(ctrl_frame, text="随机直到终局", command=self._on_auto_to_terminal).pack(side=tk.LEFT, padx=4)

    middle_frame = ttk.Frame(self)
    middle_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=4)

    # 牌桌 Canvas（加大尺寸，牌与座位更疏朗）
    table_container = ttk.Frame(middle_frame)
    table_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    table_container.update_idletasks()
    self.canvas = TableCanvas(
        table_container,
        width=700,
        height=460,
        bg="#2d5016",
        highlightthickness=0,
    )
    self.canvas.pack(fill=tk.BOTH, expand=True)

    right_frame = ttk.Frame(middle_frame)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=4)
    ttk.Label(right_frame, text="Raw state.to_string()：", anchor="w").pack(side=tk.TOP, anchor="w")
    self.txt_state = tk.Text(right_frame, height=22, width=52, wrap=tk.NONE, font=("Consolas", 9))
    scroll_y = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.txt_state.yview)
    scroll_x = ttk.Scrollbar(right_frame, orient=tk.HORIZONTAL, command=self.txt_state.xview)
    self.txt_state.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
    self.txt_state.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

    bottom_frame = ttk.LabelFrame(self, text="Actions")
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=4)
    basic_frame = ttk.Frame(bottom_frame)
    basic_frame.pack(side=tk.LEFT, padx=4, pady=4)
    self.btn_fold = ttk.Button(basic_frame, text="弃牌 (Fold)", command=self._on_fold)
    self.btn_fold.pack(side=tk.LEFT, padx=4)
    self.btn_call = ttk.Button(basic_frame, text="过牌/跟注 (Check/Call)", command=self._on_check_call)
    self.btn_call.pack(side=tk.LEFT, padx=4)
    bet_frame = ttk.Frame(bottom_frame)
    bet_frame.pack(side=tk.RIGHT, padx=4, pady=4)
    ttk.Label(bet_frame, text="下注筹码:").pack(side=tk.LEFT, padx=2)
    self.bet_var = tk.StringVar()
    self.entry_bet = ttk.Entry(bet_frame, width=10, textvariable=self.bet_var)
    self.entry_bet.pack(side=tk.LEFT, padx=2)
    self.btn_bet = ttk.Button(bet_frame, text="下注/加注 (Bet/Raise)", command=self._on_bet_with_amount)
    self.btn_bet.pack(side=tk.LEFT, padx=4)

  def _refresh_view(self) -> None:
    cur_player = self._obs.get("current_player", -1)
    is_terminal = self._obs.get("is_terminal", False)
    self.lbl_player.config(text=f"Current player: {cur_player}")
    self.lbl_terminal.config(text=f"Terminal: {is_terminal}")

    try:
      state_str = self._env.state.to_string()
    except Exception:
      state_str = str(self._env.state)

    self.txt_state.configure(state=tk.NORMAL)
    self.txt_state.delete("1.0", tk.END)
    self.txt_state.insert(tk.END, state_str)
    self.txt_state.configure(state=tk.DISABLED)

    table_data = _get_table_data(self._env)
    table_data["current_player"] = cur_player
    table_data["is_terminal"] = is_terminal
    if is_terminal and table_data.get("pot_total", 0) == 0:
      try:
        returns = self._obs.get("returns", [])
        table_data["pot_total"] = sum(abs(r) for r in returns) // 2
      except Exception:
        pass
    self.canvas.set_table_data(table_data)

    self._legal_actions = []
    self._action_labels = {}
    self._fold_actions = []
    self._check_call_actions = []
    self._bet_actions = []

    if is_terminal:
      self.btn_fold.configure(state=tk.DISABLED)
      self.btn_call.configure(state=tk.DISABLED)
      self.btn_bet.configure(state=tk.DISABLED)
      self.entry_bet.configure(state=tk.DISABLED)
      return

    legal_actions = list(self._env.legal_actions())
    if not legal_actions:
      self.btn_fold.configure(state=tk.DISABLED)
      self.btn_call.configure(state=tk.DISABLED)
      self.btn_bet.configure(state=tk.DISABLED)
      self.entry_bet.configure(state=tk.DISABLED)
      return

    try:
      player = self._env.current_player()
      labels = [(a, self._env.state.action_to_string(player, a)) for a in legal_actions]
    except Exception:
      labels = [(a, str(a)) for a in legal_actions]

    self._legal_actions = legal_actions
    self._action_labels = {a: label for a, label in labels}
    fold_actions = []
    check_call_actions = []
    bet_actions = []

    for action, label in labels:
      lower = label.lower()
      if "fold" in lower:
        fold_actions.append(action)
      elif "check" in lower or "call" in lower:
        check_call_actions.append(action)
      elif "bet" in lower or "raise" in lower:
        m = re.findall(r"(-?\d+)", lower)
        amount = int(m[-1]) if m else None
        bet_actions.append((action, amount))

    self._fold_actions = fold_actions
    self._check_call_actions = check_call_actions
    self._bet_actions = bet_actions
    self.btn_fold.configure(state=tk.NORMAL if fold_actions else tk.DISABLED)
    self.btn_call.configure(state=tk.NORMAL if check_call_actions else tk.DISABLED)
    self.btn_bet.configure(state=tk.NORMAL if bet_actions else tk.DISABLED)
    self.entry_bet.configure(state=tk.NORMAL if bet_actions else tk.DISABLED)

  def _on_reset(self) -> None:
    self._obs = self._env.reset()
    self._refresh_view()

  def _on_action(self, action: int) -> None:
    self._obs = self._env.step(action)
    self._refresh_view()

  def _on_fold(self) -> None:
    if not self._fold_actions:
      messagebox.showinfo("无弃牌动作", "当前状态下没有可用的 Fold 动作。")
      return
    self._on_action(self._fold_actions[0])

  def _on_check_call(self) -> None:
    if not self._check_call_actions:
      messagebox.showinfo("无过牌/跟注动作", "当前状态下没有可用的 Check/Call 动作。")
      return
    self._on_action(self._check_call_actions[0])

  def _on_bet_with_amount(self) -> None:
    if not self._bet_actions:
      messagebox.showinfo("无下注动作", "当前状态下没有可用的 Bet/Raise 动作。")
      return
    raw = self.bet_var.get().strip()
    if not raw:
      messagebox.showinfo("请输入下注筹码", "请在输入框中输入筹码数量（比如 300、500 等）。")
      return
    try:
      target = int(raw)
    except ValueError:
      messagebox.showerror("格式错误", f"无法解析筹码数: {raw}")
      return
    candidates = [(a, amt) for (a, amt) in self._bet_actions if amt is not None]
    if not candidates:
      self._on_action(self._bet_actions[0][0])
      return
    best_action, best_amt = min(candidates, key=lambda t: abs(t[1] - target))
    if best_amt != target:
      messagebox.showinfo("筹码已对齐", f"找不到精确筹码 {target}，已选择最接近的可用筹码 {best_amt}。")
    self._on_action(best_action)

  def _on_random_step(self) -> None:
    if self._env.is_terminal():
      self._obs = self._env.reset()
    else:
      legal = self._env.legal_actions()
      if legal:
        import random as _rnd
        self._obs = self._env.step(_rnd.choice(legal))
    self._refresh_view()

  def _on_auto_to_terminal(self) -> None:
    import random as _rnd
    steps = 0
    while not self._env.is_terminal() and steps < 500:
      legal = self._env.legal_actions()
      if not legal:
        break
      self._obs = self._env.step(_rnd.choice(legal))
      steps += 1
    self._refresh_view()


def main() -> int:
  _ensure_project_root_on_path()
  app = SixMaxViewer(seed=42)
  app.mainloop()
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
