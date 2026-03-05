#!/usr/bin/env python3
"""
6-max 子游戏策略范围可视化（类似 GTO Wizard 的 169 格子图）。

功能：
- 加载子游戏 CFR 导出的 JSON 策略（如 data/subgame_strategy_cfr.json 或 data/subgame_strategy_example.json）
- 选择 street / board 桶 / 行动序列，展示当前行动玩家的 169 手牌范围
- 每个格子用颜色标记该手牌在该 infoset 下的主导动作：Fold / Check-Call / Bet-Raise / Mixed

用法（项目根目录）：
  python scripts/six_max_range_viewer.py \
      --strategy data/subgame_strategy_cfr.json \
      --street flop \
      --board_bucket rainbow \
      --actions none

说明：
- street 目前主要关注 "flop" / "turn" / "river"
- board_bucket 可选 "rainbow" / "twotone" / "monotone"
- actions 需与抽象动作名一致（用下划线连接），例如：
    - none
    - check_or_call
    - 33%_check_or_call
    - 75%_check_or_call
    - 33%_check_or_call_75%_check_or_call
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import tkinter as tk
from tkinter import ttk, messagebox


def _ensure_project_root_on_path() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)


_ensure_project_root_on_path()

from algorithms import abstraction  # noqa: E402


FOLD_BUCKET = abstraction.FOLD_BUCKET
CHECK_BUCKET = abstraction.CHECK_OR_CALL_BUCKET
BET_BUCKETS = list(abstraction.BET_BUCKET_NAMES)
ALL_IN_BUCKET = abstraction.ALL_IN_BUCKET


@dataclass
class StrategyInfo:
    """封装单个 infoset 的策略分布。"""

    probs: Dict[str, float]

    def dominant_bucket(self) -> str:
        if not self.probs:
            return ""
        return max(self.probs.items(), key=lambda kv: kv[1])[0]


class RangeGrid(tk.Canvas):
    """13x13 手牌范围网格。"""

    def __init__(self, parent, cell_size: int = 32, **kwargs):
        super().__init__(parent, **kwargs)
        self.cell_size = cell_size
        self._labels: List[str] = list(abstraction.PREFLOP_HAND_BUCKETS)
        if len(self._labels) != 169:
            # 若不是 169，仍然按行绘制，只是不是标准 GTO 169 排列
            messagebox.showwarning(
                "手牌桶数量异常",
                f"PREFLOP_HAND_BUCKETS 大小为 {len(self._labels)}，并非 169，将按顺序排布。",
            )
        self._cell_to_label: Dict[Tuple[int, int], str] = {}
        self._label_to_cell: Dict[str, Tuple[int, int]] = {}
        self._cell_colors: Dict[Tuple[int, int], str] = {}
        self._cell_infos: Dict[Tuple[int, int], StrategyInfo] = {}
        self._build_mapping()
        self.bind("<Button-1>", self._on_click)

    def _build_mapping(self) -> None:
        self._cell_to_label.clear()
        self._label_to_cell.clear()
        labels = self._labels
        for idx, name in enumerate(labels):
            row = idx // 13
            col = idx % 13
            self._cell_to_label[(row, col)] = name
            self._label_to_cell[name] = (row, col)

    def set_cell_info(
        self,
        label_to_info: Dict[str, StrategyInfo],
        label_to_color: Dict[str, str],
    ) -> None:
        self._cell_colors.clear()
        self._cell_infos.clear()
        for label, info in label_to_info.items():
            cell = self._label_to_cell.get(label)
            if cell is None:
                continue
            color = label_to_color.get(label, "#666666")
            self._cell_colors[cell] = color
            self._cell_infos[cell] = info
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        size = self.cell_size
        labels = self._labels
        # 绘制格子
        for idx, name in enumerate(labels):
            row = idx // 13
            col = idx % 13
            x0 = col * size
            y0 = row * size
            x1 = x0 + size
            y1 = y0 + size
            cell = (row, col)
            color = self._cell_colors.get(cell, "#333333")
            self.create_rectangle(x0, y0, x1, y1, fill=color, outline="#222222")
            # 文本：手牌名
            self.create_text(
                (x0 + x1) / 2,
                (y0 + y1) / 2,
                text=name,
                font=("Consolas", 7),
                fill="#ffffff",
            )

    def _on_click(self, event) -> None:  # type: ignore[override]
        size = self.cell_size
        col = event.x // size
        row = event.y // size
        cell = (row, col)
        label = self._cell_to_label.get(cell)
        if not label:
            return
        info = self._cell_infos.get(cell)
        if info is None:
            messagebox.showinfo("无策略", f"{label}: 当前 infoset 下未找到策略（使用 default 或均匀分布）。")
            return
        lines = [f"{label} 策略分布:"]
        for k, v in sorted(info.probs.items(), key=lambda kv: -kv[1]):
            lines.append(f"  {k}: {v:.3f}")
        messagebox.showinfo("策略详情", "\n".join(lines))


class RangeViewer(tk.Tk):
    """范围可视化主窗口。"""

    def __init__(self, strategy_path: Path, street: str, board_bucket: str, actions: str):
        super().__init__()
        self.title("6-max 子游戏策略范围可视化")
        self.geometry("900x650")

        self.strategy_path = strategy_path
        self.strategy = self._load_strategy(strategy_path)

        self.street_var = tk.StringVar(value=street)
        self.board_var = tk.StringVar(value=board_bucket)
        self.actions_var = tk.StringVar(value=actions)

        self._build_widgets()
        self._refresh_range()

    def _load_strategy(self, path: Path) -> Dict[str, Dict[str, float]]:
        if not path.exists():
            messagebox.showerror("策略文件不存在", f"未找到策略 JSON：{path}")
            raise SystemExit(1)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            messagebox.showerror("格式错误", f"策略文件不是 JSON 对象：{path}")
            raise SystemExit(1)
        return data

    def _build_widgets(self) -> None:
        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=8, pady=4)

        ttk.Label(top, text=f"策略文件: {self.strategy_path}").pack(side=tk.TOP, anchor="w")

        ctrl = ttk.Frame(top)
        ctrl.pack(side=tk.TOP, fill=tk.X, pady=4)

        # street
        ttk.Label(ctrl, text="Street:").grid(row=0, column=0, sticky="w", padx=2, pady=2)
        cmb_street = ttk.Combobox(
            ctrl,
            textvariable=self.street_var,
            values=["flop", "turn", "river"],
            width=8,
            state="readonly",
        )
        cmb_street.grid(row=0, column=1, sticky="w", padx=2, pady=2)

        # board
        ttk.Label(ctrl, text="Board 桶:").grid(row=0, column=2, sticky="w", padx=8, pady=2)
        cmb_board = ttk.Combobox(
            ctrl,
            textvariable=self.board_var,
            values=["rainbow", "twotone", "monotone"],
            width=10,
            state="readonly",
        )
        cmb_board.grid(row=0, column=3, sticky="w", padx=2, pady=2)

        # actions
        ttk.Label(ctrl, text="Action 序列:").grid(row=1, column=0, sticky="w", padx=2, pady=2)
        entry_actions = ttk.Entry(ctrl, textvariable=self.actions_var, width=40)
        entry_actions.grid(row=1, column=1, columnspan=3, sticky="w", padx=2, pady=2)
        ttk.Label(
            ctrl,
            text="使用下划线连接，如 none, check_or_call, 33%_check_or_call 等",
        ).grid(row=2, column=0, columnspan=4, sticky="w", padx=2, pady=2)

        btn_refresh = ttk.Button(ctrl, text="更新范围", command=self._refresh_range)
        btn_refresh.grid(row=0, column=4, rowspan=2, sticky="nsw", padx=8, pady=2)

        # 色标
        legend = ttk.Frame(self)
        legend.pack(side=tk.TOP, fill=tk.X, padx=8, pady=4)
        for text, color in [
            ("Fold 主导", "#b00020"),
            ("Check/Call 主导", "#0a7f2e"),
            ("Bet/Raise 主导", "#1565c0"),
            ("Mixed（无明显主导）", "#7b7b7b"),
        ]:
            swatch = tk.Canvas(legend, width=18, height=18, bg=color, highlightthickness=0)
            swatch.pack(side=tk.LEFT, padx=3)
            ttk.Label(legend, text=text).pack(side=tk.LEFT, padx=3)

        # 范围网格
        grid_frame = ttk.Frame(self)
        grid_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=4)
        self.range_grid = RangeGrid(
            grid_frame,
            cell_size=32,
            width=32 * 13 + 2,
            height=32 * 13 + 2,
            bg="#111111",
            highlightthickness=0,
        )
        self.range_grid.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

        # 右侧说明
        right = ttk.Frame(grid_frame)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        self.txt_info = tk.Text(right, height=10, width=40, wrap=tk.WORD, font=("Consolas", 9))
        self.txt_info.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self._update_info_text()

    def _update_info_text(self) -> None:
        self.txt_info.configure(state=tk.NORMAL)
        self.txt_info.delete("1.0", tk.END)
        self.txt_info.insert(
            tk.END,
            (
                "说明：\n"
                "- 选择 street / board 桶 / action 序列 后点击“更新范围”。\n"
                "- 每个格子代表一类起手牌（PREFLOP_HAND_BUCKETS）。\n"
                "- 颜色表示该手牌在当前 infoset 下的主导动作：\n"
                "    红色 = Fold 主导\n"
                "    绿色 = Check/Call 主导\n"
                "    蓝色 = Bet/Raise 主导\n"
                "    灰色 = Mixed 或未知\n"
                "- 点击某个格子可查看该手牌的完整概率分布。\n"
            ),
        )
        self.txt_info.configure(state=tk.DISABLED)

    def _build_infoset_key(self, street: str, hand_bucket: str, board_bucket: str, actions: str) -> str:
        actions = (actions or "").strip()
        if not actions or actions.lower() == "none":
            actions_part = "none"
        else:
            actions_part = actions
        return f"{street}_{hand_bucket}_{board_bucket}_{actions_part}"

    def _refresh_range(self) -> None:
        street = self.street_var.get().strip() or "flop"
        board_bucket = self.board_var.get().strip() or "rainbow"
        actions = self.actions_var.get().strip() or "none"

        labels = list(abstraction.PREFLOP_HAND_BUCKETS)
        label_to_info: Dict[str, StrategyInfo] = {}
        label_to_color: Dict[str, str] = {}

        for hb in labels:
            key = self._build_infoset_key(street, hb, board_bucket, actions)
            probs = self.strategy.get(key)
            if not isinstance(probs, dict) or not probs:
                # 尝试 default
                probs = self.strategy.get("default", {})
                if not isinstance(probs, dict) or not probs:
                    continue
            # 归一化
            total = float(sum(float(v) for v in probs.values()))
            if total > 0:
                norm = {k: float(v) / total for k, v in probs.items()}
            else:
                continue
            info = StrategyInfo(norm)
            dom = info.dominant_bucket()
            color = self._bucket_to_color(dom, norm)
            label_to_info[hb] = info
            label_to_color[hb] = color

        self.range_grid.set_cell_info(label_to_info, label_to_color)

    def _bucket_to_color(self, bucket: str, probs: Dict[str, float]) -> str:
        if not bucket:
            return "#7b7b7b"
        # 若最大概率也很均匀，则视为 Mixed
        max_p = max(probs.values())
        if max_p < 0.45:
            return "#7b7b7b"
        if bucket == FOLD_BUCKET:
            return "#b00020"
        if bucket == CHECK_BUCKET:
            return "#0a7f2e"
        if bucket in BET_BUCKETS or bucket == ALL_IN_BUCKET:
            return "#1565c0"
        return "#7b7b7b"


def main() -> int:
    parser = argparse.ArgumentParser(description="6-max 子游戏 CFR 策略范围可视化")
    parser.add_argument(
        "--strategy",
        default="data/subgame_strategy_example.json",
        help="策略 JSON 路径（train_six_max_subgame_cfr.py 输出或示例）",
    )
    parser.add_argument(
        "--street",
        default="flop",
        help='街道：flop / turn / river（默认 flop）',
    )
    parser.add_argument(
        "--board_bucket",
        default="rainbow",
        help='公共牌桶：rainbow / twotone / monotone（默认 rainbow）',
    )
    parser.add_argument(
        "--actions",
        default="none",
        help='行动序列（用 "_" 连接；例如 none, check_or_call, 33%_check_or_call 等）',
    )
    args = parser.parse_args()

    path = Path(args.strategy)
    app = RangeViewer(path, street=args.street, board_bucket=args.board_bucket, actions=args.actions)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

