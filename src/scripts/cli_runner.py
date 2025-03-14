from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import TextMessage
import asyncio
from typing import Optional, List, Dict, Any

# 导入我们的游戏引擎
from src.engine.game_engine import GameEngine
from src.models.gameSchema import GameState

async def get_user_input() -> str:
    """
    获取命令行输入
    
    Returns:
        str: 用户输入的文本
    """
    return input("玩家输入 > ")

async def display_output(message: TextMessage) -> None:
    """
    将消息输出到终端
    
    Args:
        message: 要显示的消息
    """
    print(f"{message.source}: {message.content}")

async def show_player_history(round_manager, player_name: str) -> None:
    """
    显示指定玩家的历史记录
    
    Args:
        round_manager: 回合管理器
        player_name: 玩家名称
    """
    history = round_manager.get_player_history(player_name)
    if not history:
        print(f"找不到玩家 '{player_name}' 的历史记录")
        return
    
    print(f"\n--- {player_name} 的历史记录 ---")
    for i, entry in enumerate(history):
        print(f"\n回合 {i+1} ({entry['timestamp']})")
        print(f"观察: {entry['observation']}")
        print(f"状态: 目标={entry['character_state']['goal']}, " +
             f"计划={entry['character_state']['plan']}, " +
             f"心情={entry['character_state']['mood']}, " +
             f"血量={entry['character_state']['health']}")
        print(f"思考: {entry['thinking']}")
        print(f"行动: {entry['action']}")
        print("-" * 50)

async def main() -> None:
    """
    CLI入口，管理整个游戏流程
    """
    print("=== TTRPG NPC游戏系统启动 ===")
    print("这是一个多人角色扮演游戏，包含3个AI玩家和1个人类玩家")
    print("每回合DM会描述场景，然后所有玩家依次行动")
    print("可用命令:")
    print("  /history [玩家名称] - 查看指定玩家的内部状态历史")
    print("  /quit - 退出游戏\n")
    
    # 创建游戏引擎
    engine = GameEngine(max_rounds=5)
    
    try:
        # 启动游戏
        final_state = await engine.start_game()
        print("\n=== 游戏结束 ===")
        print(f"共进行了{final_state.round_number}回合")
    except KeyboardInterrupt:
        print("\n游戏被用户中断")
    except Exception as e:
        print(f"\n游戏出错: {str(e)}")

if __name__ == "__main__":
    # 启动异步事件循环
    asyncio.run(main())
