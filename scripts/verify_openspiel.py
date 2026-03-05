#!/usr/bin/env python3
"""
OpenSpiel 环境验收脚本：
- 检查 pyspiel 与 Python API 是否可用
- 列出扑克相关游戏及 universal_poker 支持情况
- 跑通 Leduc/Kuhn 一局 + 少量 CFR 迭代（可选）
"""
import sys

def main():
    print("=" * 60)
    print("OpenSpiel 环境验收")
    print("=" * 60)

    # 1. 导入检查
    print("\n[1] 导入检查...")
    try:
        import pyspiel
        from open_spiel.python import rl_environment
        from open_spiel.python.algorithms import cfr, exploitability
        from open_spiel.python import policy
    except Exception as e:
        print("FAIL: 导入失败:", e)
        return 1
    print("OK: pyspiel, rl_environment, cfr, policy 均可导入")

    # 2. 注册游戏列表（扑克相关）
    print("\n[2] 扑克相关已注册游戏...")
    all_games = pyspiel.registered_games()
    poker_related = [g for g in all_games if "poker" in g.short_name.lower() or "leduc" in g.short_name.lower() or "kuhn" in g.short_name.lower()]
    for g in poker_related:
        loadable = "可加载" if g.default_loadable else "需参数"
        print(f"  - {g.short_name}: {loadable} (min_players={getattr(g, 'min_num_players', '?')}, max_players={getattr(g, 'max_num_players', '?')})")
    if not poker_related:
        print("  (无扑克相关游戏，可能 universal_poker 未编译)")

    # 3. Kuhn / Leduc 加载与对局
    print("\n[3] Kuhn Poker 加载与随机对局...")
    try:
        game = pyspiel.load_game("kuhn_poker")
        state = game.new_initial_state()
        rng = __import__("random")
        steps = 0
        while not state.is_terminal() and steps < 100:
            if state.is_chance_node():
                outcomes = state.chance_outcomes()
                action = rng.choice([a for a, _ in outcomes])
            else:
                action = rng.choice(state.legal_actions())
            state.apply_action(action)
            steps += 1
        ret = state.returns()
        print(f"OK: 一局结束, returns={ret}, 步数={steps}")
    except Exception as e:
        print("FAIL:", e)
        return 1

    print("\n[4] Leduc Poker 加载与随机对局...")
    try:
        game = pyspiel.load_game("leduc_poker")
        state = game.new_initial_state()
        rng = __import__("random")
        steps = 0
        while not state.is_terminal() and steps < 200:
            if state.is_chance_node():
                outcomes = state.chance_outcomes()
                action = rng.choice([a for a, _ in outcomes])
            else:
                action = rng.choice(state.legal_actions())
            state.apply_action(action)
            steps += 1
        ret = state.returns()
        print(f"OK: 一局结束, returns={ret}, 步数={steps}")
    except Exception as e:
        print("FAIL:", e)
        return 1

    # 5. CFR 少量迭代（Leduc）
    print("\n[5] Leduc 上运行 Python CFR (20 次迭代)...")
    try:
        game = pyspiel.load_game("leduc_poker")
        cfr_solver = cfr.CFRSolver(game)
        for i in range(20):
            cfr_solver.evaluate_and_update_policy()
        expl = exploitability.exploitability(game, cfr_solver.average_policy())
        print(f"OK: CFR 完成, 当前 exploitability={expl:.6f}")
    except Exception as e:
        print("FAIL:", e)
        return 1

    # 6. universal_poker 可用性（若存在）
    print("\n[6] universal_poker 检查...")
    if "universal_poker" in pyspiel.registered_names():
        try:
            # 标准 HU 配置
            game_str = (
                "universal_poker(betting=nolimit,numPlayers=2,numRounds=4,"
                "blind=100 50,firstPlayer=2 1 1 1,numSuits=4,numRanks=13,"
                "numHoleCards=2,numBoardCards=0 3 1 1,stack=20000 20000)"
            )
            game = pyspiel.load_game(game_str)
            state = game.new_initial_state()
            print("OK: universal_poker (2人) 可加载并创建初始状态")
            if hasattr(pyspiel, "hunl_game_string"):
                try:
                    _ = pyspiel.hunl_game_string("fullgame")
                    print("OK: pyspiel.hunl_game_string('fullgame') 可用")
                except Exception as e2:
                    print("WARN: hunl_game_string 不可用:", e2)
        except Exception as e:
            print("WARN: universal_poker 加载失败:", e)
    else:
        print("INFO: universal_poker 未注册（可能未编译 C++ universal_poker）")

    # 7. RL 环境
    print("\n[7] RL Environment (Kuhn)...")
    try:
        env = rl_environment.Environment("kuhn_poker")
        ts = env.reset()
        print(f"OK: env.num_players={env.num_players}, obs_spec 存在={hasattr(ts.observations, 'info_state')}")
    except Exception as e:
        print("FAIL:", e)
        return 1

    print("\n" + "=" * 60)
    print("验收通过：OpenSpiel 环境可用，可进行下一步开发。")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
