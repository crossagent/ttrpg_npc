from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import TextMessage
import asyncio
from typing import Optional, List, Dict, Any
import logging # Added logging import
from src.utils.logging_utils import setup_logging # Added setup_logging import

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

    # Note: This function now only prints. Logging is handled by the handler in GameEngine.
    print(f"{source_display}: {prefix}{message.content}")


async def show_player_history(round_manager, player_name: str) -> None:
    """
    显示指定玩家的历史记录
    
    Args:
        round_manager: 回合管理器
        player_name: 玩家名称
    """
    # This function prints directly to console. It's not part of the main game flow messages.
    # If logging for this command is needed, it should be added here or handled differently.
    # The GameEngine's _show_player_history now handles logging.
    # This cli_runner version might become redundant or needs refactoring if GameEngine handles commands.
    
    # Check if round_manager is available (might be None if called before engine init or after cleanup)
    if not round_manager:
        print("回合管理器不可用，无法显示历史记录。")
        return
        
    # Assuming round_manager has access to the necessary history data or methods
    # The original implementation relied on a specific structure in round_manager.
    # Let's adapt based on GameEngine's approach, assuming round_manager has message_dispatcher
    if not hasattr(round_manager, 'message_dispatcher'):
         print("回合管理器缺少消息分发器，无法获取历史记录。")
         return

    messages = round_manager.message_dispatcher.get_message_history(player_id=player_name) # Use player_id kwarg

    if not messages:
        print(f"找不到玩家 '{player_name}' 的历史记录")
        return
    
    print(f"\n--- {player_name} 的历史记录 ---")
    
    # Simplified display based on GameEngine's _show_player_history
    for message in messages:
        sender = message.source if hasattr(message, 'source') else "未知"
        content = message.content if hasattr(message, 'content') else str(message)
        timestamp = message.timestamp if hasattr(message, 'timestamp') else "未知时间"
        print(f"\n[{timestamp}] {sender}: {content}")

    print("\n" + "-" * 50)


async def main() -> None:
    """
    CLI入口，管理整个游戏流程
    """
    # --- Setup Logging ---
    # Set level to INFO by default, or DEBUG for more details
    setup_logging(level=logging.INFO) 
    # --- End Logging Setup ---

    logging.info("=== TTRPG NPC游戏系统启动 (CLI Runner) ===") # Log start
    print("=== TTRPG NPC游戏系统启动 ===")
    # Removed redundant help messages as GameEngine handles command input now
    
    # 创建游戏引擎
    # Max rounds might be better configured elsewhere (e.g., game_config.yaml)
    engine = GameEngine(max_rounds=5) 
    
    try:
        # 启动游戏 - GameEngine now handles the main loop and command input
        await engine.run_game()
        logging.info("=== 游戏正常结束 (CLI Runner) ===") # Log normal end
        # print("\n=== 游戏结束 ===") # GameEngine prints its own end message
    except KeyboardInterrupt:
        logging.warning("游戏被用户中断 (CLI Runner)") # Log interruption
        print("\n游戏被用户中断")
    except Exception as e:
        logging.exception(f"游戏出错 (CLI Runner): {str(e)}") # Log exception
        print(f"\n游戏出错: {str(e)}")
    finally:
        logging.info("CLI Runner main function finished.")

if __name__ == "__main__":
    # 启动异步事件循环
    asyncio.run(main())
