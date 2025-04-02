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
from src.utils.display_utils import format_message_display_parts # Import the new util function
from src.io.input_handler import CliInputHandler # Import CliInputHandler

# --- Game Record Handler ---
# This function remains the same, defining the desired log format.
def game_record_handler(message: Message, log_file_handle: TextIO) -> None:
    """
    处理消息并将其以指定格式记录到游戏记录文件。

    格式: Name(ID): (行动) Content  或  Name: Content
    """
    content = message.content if hasattr(message, 'content') else str(message)

    # Call the utility function to get formatted parts
    source_display_log, prefix_log = format_message_display_parts(message)

    # Construct the log line using the parts from the utility function
    log_line = f"{source_display_log}: {prefix_log}{content}\n"

    # Write to log file
    try:
        log_file_handle.write(log_line)
        log_file_handle.flush() # Ensure it's written immediately
    except Exception as e:
        # Avoid crashing the runner if logging fails
        logging.error(f"写入游戏记录时出错: {e}")
        print(yellow_text(f"警告: 无法写入游戏记录: {e}"))

# --- End Game Record Handler ---


async def get_user_input() -> str:
    """
    获取命令行输入

    Returns:
        str: 用户输入的文本
    """
    # Keep this function as it's used by GameEngine indirectly via input()
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
    record_filename = None # Initialize filename
    try:
        os.makedirs(record_dir, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        record_filename = os.path.join(record_dir, f"record_{timestamp_str}.log")
        log_file = open(record_filename, 'a', encoding='utf-8')
        logging.info(f"游戏记录文件已打开: {record_filename}")
        # --- End Game Record Setup ---

        # --- Create Input Handler ---
        cli_input_handler = CliInputHandler()
        # --- End Input Handler Creation ---

        # --- Create Game Engine and Pass Handlers ---
        # Pass the record handler, file handle, and input handler to the engine
        engine = GameEngine(
            max_rounds=5,
            record_handler=game_record_handler,
            record_file_handle=log_file,
            input_handler=cli_input_handler # Pass the input handler
        )
        # --- End Engine Creation ---

        # --- Remove Direct Handler Registration ---
        # The following block is removed as registration now happens inside GameEngine
        # if engine.message_dispatcher:
        #     # Use lambda to pass the log_file handle to the handler
        #     engine.message_dispatcher.register_message_handler(
        #         lambda msg: game_record_handler(msg, log_file),
        #         list(MessageType) # Register for all message types
        #     )
        #     logging.info(f"游戏记录处理器已注册到文件: {record_filename}")
        # else:
        #     logging.error("无法获取 MessageDispatcher，游戏记录将不会被保存。")
        #     print(yellow_text("错误：无法初始化游戏记录功能。"))
        # --- End Handler Registration Removal ---

        # Write start message to log file (still done here for immediate feedback)
        start_message = f"--- Game Started: {timestamp_str} ---\n"
        log_file.write(start_message)
        log_file.flush()

        # 启动游戏 - GameEngine handles the main loop and command input
        # GameEngine will print its own start message to console
        await engine.run_game()

        # Write end message to log file
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
            try:
                log_file.close()
                logging.info(f"游戏记录文件已关闭: {record_filename}")
            except Exception as close_err:
                 logging.error(f"关闭游戏记录文件时出错: {close_err}")
        logging.info("CLI Runner main function finished.")

if __name__ == "__main__":
    # 启动异步事件循环
    asyncio.run(main())
