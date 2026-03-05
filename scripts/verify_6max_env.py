#!/usr/bin/env python3
"""
6-max NLHE 环境验收脚本（依赖 pokerkit + python_pokerkit_wrapper）。
在安装 pokerkit 并确保 OpenSpiel 能加载 python_pokerkit_wrapper 后运行：
  .venv\\Scripts\\python.exe scripts\\verify_6max_env.py
"""
import sys

def main():
    print("=" * 60)
    print("6-max NLHE 环境验收 (python_pokerkit_wrapper)")
    print("=" * 60)

    try:
        import pyspiel
        from open_spiel.python.games import pokerkit_wrapper  # 注册 python_pokerkit_wrapper
    except ImportError as e:
        print("FAIL: 依赖未安装:", e)
        print("  请执行: pip install pokerkit")
        return 1
    except Exception as e:
        print("FAIL: pyspiel 或 pokerkit_wrapper 异常:", e)
        return 1

    if "python_pokerkit_wrapper" not in pyspiel.registered_names():
        print("FAIL: python_pokerkit_wrapper 未注册，请先安装 pokerkit: pip install pokerkit")
        return 1

    # 6 人 NLHE：100BB，SB=50, BB=100（与常见 100BB 一致）
    params = {
        "variant": "NoLimitTexasHoldem",
        "num_players": 6,
        "blinds": "50 100",
        "stack_sizes": "10000 10000 10000 10000 10000 10000",
    }
    print("\n[1] 加载 6-max 游戏...")
    try:
        game = pyspiel.load_game("python_pokerkit_wrapper", params)
        print(f"OK: num_players={game.num_players()}")
    except Exception as e:
        print("FAIL: 加载失败:", e)
        return 1

    print("\n[2] 随机打 3 手牌...")
    rng = __import__("random")
    for hand_idx in range(3):
        state = game.new_initial_state()
        steps = 0
        while not state.is_terminal() and steps < 500:
            if state.is_chance_node():
                outcomes = state.chance_outcomes()
                action = rng.choice([a for a, _ in outcomes])
            else:
                legal = state.legal_actions()
                action = rng.choice(legal)
            state.apply_action(action)
            steps += 1
        ret = state.returns()
        print(f"  手牌 {hand_idx + 1}: returns={ret}, 步数={steps}")
    print("OK: 3 手均正常结束")

    print("\n" + "=" * 60)
    print("6-max 环境验收通过。")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
