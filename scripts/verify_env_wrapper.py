#!/usr/bin/env python3
"""
阶段 A5 验收：使用 env 包中的 SixMaxEnv 封装跑若干手牌，检查接口可用性。
在项目根目录执行: python scripts/verify_env_wrapper.py
"""
import sys
import os

# 保证从项目根目录可导入 env
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("=" * 60)
    print("阶段 A5: 6-max 封装接口验收")
    print("=" * 60)

    try:
        from env import create_six_max_env
    except ImportError as e:
        print("FAIL: 无法导入 env:", e)
        return 1

    env = create_six_max_env(num_players=6, seed=42)
    print("\n[1] create_six_max_env(6) 创建成功")

    obs = env.reset()
    print("[2] reset() 返回 obs 含 current_player, legal_actions, is_terminal, returns")
    assert "current_player" in obs and "legal_actions" in obs
    assert "is_terminal" in obs and "returns" in obs
    print(f"     current_player={obs['current_player']}, legal_actions 数量={len(obs['legal_actions'])}")

    # Step 1 验收：pot、stacks、action_id_to_info
    assert "pot" in obs and "stacks" in obs and "action_id_to_info" in obs
    assert obs["pot"] >= 0 and len(obs["stacks"]) == 6
    a2i = obs["action_id_to_info"]
    for aid in obs["legal_actions"]:
        assert aid in a2i and "type" in a2i[aid]
    print(f"     pot={obs['pot']}, stacks[:2]={obs['stacks'][:2]}..., action_id_to_info 覆盖全部 legal_actions")

    step_count = 0
    while not env.is_terminal() and step_count < 400:
        legal = env.legal_actions()
        action = legal[0]  # 选第一个合法动作
        obs = env.step(action)
        step_count += 1
    ret = env.returns()
    print(f"[3] 打完一手: returns={ret}, 步数={step_count}")

    # 再打 2 手
    for _ in range(2):
        env.reset()
        n = 0
        while not env.is_terminal() and n < 400:
            legal = env.legal_actions()
            env.step(legal[0])
            n += 1
    print("[4] 再打 2 手完成，接口正常")

    print("\n" + "=" * 60)
    print("阶段 A5 验收通过: 6-max 封装可供算法层调用。")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
