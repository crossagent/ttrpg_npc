from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import TextMessage
import asyncio
from typing import Optional, List, Dict, Any

# 导入我们的游戏引擎
from src.engine.game_engine import GameEngine

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
    # 检查 message 是否有 source_id 属性 (因为它是 Optional)
    source_display = message.source
    if hasattr(message, 'source_id') and message.source_id:
        # 排除非角色ID的情况，例如 "dm_agent" 或 "referee_agent"
        # 假设角色ID通常包含下划线或数字，而代理ID不包含
        # 或者更可靠地，检查 source 是否与 source_id 不同 (对于玩家/NPC)
        if message.source != message.source_id: # 简单的区分方式
             source_display = f"{message.source}({message.source_id})"
        # else: # 如果 source 和 source_id 相同，或者 source_id 是 'dm_agent' 等，只显示 source
        #     source_display = message.source

    # 根据 subtype 添加前缀
    prefix = ""
    if hasattr(message, 'message_subtype') and message.message_subtype == "action_description":
        prefix = "(行动) "

    print(f"{source_display}: {prefix}{message.content}")


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
    
    # 按回合分组
    rounds = {}
    for entry in history:
        round_num = entry.get("round", 0)
        if round_num not in rounds:
            rounds[round_num] = []
        rounds[round_num].append(entry)
    
    # 按回合显示历史记录
    for round_num in sorted(rounds.keys()):
        if round_num == 0:  # 跳过回合为0的记录
            continue
            
        print(f"\n————第{round_num}回合————")
        entries = rounds[round_num]
        
        # 按时间戳排序
        entries.sort(key=lambda x: x.get("timestamp", ""))
        
        # 显示该回合的所有记录
        for entry in entries:
            character_name = entry.get("character_name", "")
            message = entry.get("message", "")
            print(f"{character_name}: {message}")

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
        await engine.run_game()
        print("\n=== 游戏结束 ===")
    except KeyboardInterrupt:
        print("\n游戏被用户中断")
    except Exception as e:
        print(f"\n游戏出错: {str(e)}")

if __name__ == "__main__":
    # 启动异步事件循环
    asyncio.run(main())
