from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import TextMessage
import asyncio
from typing import Optional, List, Dict, Any, TextIO # Added TextIO
import logging
import os # Added os
from datetime import datetime # Added datetime

from src.utils.logging_utils import setup_logging
from src.engine.game_engine import GameEngine
from src.models.message_models import Message, MessageType # Added Message, MessageType
from src.config.color_utils import gray_text, yellow_text # Import color utils if needed for commands

# --- Game Record Handler ---
def game_record_handler(message: Message, log_file_handle: TextIO) -> None:
    """
    处理消息并将其以指定格式记录到游戏记录文件。

    格式: Name(ID): (行动) Content  或  Name: Content
    """
    source = message.source if hasattr(message, 'source') else "未知来源"
    content = message.content if hasattr(message, 'content') else str(message)

    # 1. Determine source display (Name or Name(ID))
    source_display_log = source
    if hasattr(message, 'source_id') and message.source_id:
        # Only add ID if it's different from the name (typical for characters)
        # Exclude agent IDs like 'dm_agent', 'referee_agent', 'system'
        is_agent_id = message.source_id in ["dm_agent", "referee_agent", "system"] # Add more if needed
        # Also check if source is '裁判' which uses referee_agent id
        is_referee_source = source == "裁判"
        if message.source != message.source_id and not is_agent_id and not is_referee_source:
             source_display_log = f"{source}({message.source_id})"
        # Handle Referee specifically if needed (e.g., always show "裁判")
        elif is_referee_source:
             source_display_log = "裁判"


    # 2. Determine prefix (e.g., "(行动) ")
    prefix_log = ""
    if hasattr(message, 'message_subtype') and message.message_subtype == "action_description":
        prefix_log = "(行动) "

    # 3. Construct the log line
    log_line = f"{source_display_log}: {prefix_log}{content}\n"

    # Write to log file
    log_file_handle.write(log_line)
    log_file_handle.flush() # Ensure it's written immediately
# --- End Game Record Handler ---


async def get_user_input() -> str:
    """
    获取命令行输入

    Returns:
        str: 用户输入的文本
    """
    # Keep this function as it's used by GameEngine indirectly via input()
    # Although GameEngine now handles the loop, input() is called there.
    # For clarity, we can leave it, or assume GameEngine uses input() directly.
    # Let's leave it for now.
    return input("玩家输入 > ")

# Removed display_output function - console output handled by GameEngine's default handler
# Removed show_player_history function - handled by GameEngine's internal method via command


async def main() -> None:
    """
    CLI入口，管理整个游戏流程
    """
    # --- Setup Logging ---
    setup_logging(level=logging.INFO)
    # --- End Logging Setup ---

    logging.info("=== TTRPG NPC游戏系统启动 (CLI Runner) ===")
    print("=== TTRPG NPC游戏系统启动 ===")

    # --- Game Record Setup ---
    record_dir = "game_records"
    log_file = None # Initialize log_file to None
    try:
        os.makedirs(record_dir, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        record_filename = os.path.join(record_dir, f"record_{timestamp_str}.log")
        log_file = open(record_filename, 'a', encoding='utf-8')
        # --- End Game Record Setup ---

        # 创建游戏引擎
        engine = GameEngine(max_rounds=5)

        # --- Register Game Record Handler ---
        if engine.message_dispatcher:
            # Use lambda to pass the log_file handle to the handler
            engine.message_dispatcher.register_message_handler(
                lambda msg: game_record_handler(msg, log_file),
                list(MessageType) # Register for all message types
            )
            logging.info(f"游戏记录处理器已注册到文件: {record_filename}")
        else:
            logging.error("无法获取 MessageDispatcher，游戏记录将不会被保存。")
            print(yellow_text("错误：无法初始化游戏记录功能。"))
        # --- End Handler Registration ---

        # Write start message to log file
        start_message = f"--- Game Started: {timestamp_str} ---\n"
        log_file.write(start_message)
        log_file.flush()

        # 启动游戏 - GameEngine handles the main loop and command input
        # GameEngine will print its own start message to console
        await engine.run_game()

        # Write end message to log file
        # Note: GameEngine doesn't return final state here, so round number needs to be fetched if needed
        # We'll just write a generic end message.
        end_message = f"--- Game Ended ---\n"
        log_file.write(end_message)
        log_file.flush()

        logging.info("=== 游戏正常结束 (CLI Runner) ===")

    except KeyboardInterrupt:
        logging.warning("游戏被用户中断 (CLI Runner)")
        print("\n游戏被用户中断")
        if log_file:
            log_file.write("\n--- Game Interrupted by User ---\n")
    except Exception as e:
        logging.exception(f"游戏出错 (CLI Runner): {str(e)}")
        print(f"\n游戏出错: {str(e)}")
        if log_file:
            log_file.write(f"\n--- Game Error: {str(e)} ---\n")
    finally:
        if log_file:
            log_file.close()
            logging.info(f"游戏记录文件已关闭: {record_filename}")
        logging.info("CLI Runner main function finished.")

if __name__ == "__main__":
    # 启动异步事件循环
    asyncio.run(main())
