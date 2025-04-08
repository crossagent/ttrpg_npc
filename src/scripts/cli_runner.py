from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import TextMessage
import asyncio
from typing import Optional, List, Dict, Any, TextIO # Added TextIO
import logging
import os # Added os
from datetime import datetime # Added datetime
import argparse # +++ Import argparse +++
import json # +++ Import json +++

from src.utils.logging_utils import setup_logging
from src.engine.game_engine import GameEngine
# +++ Import necessary managers and models for loading +++
from src.engine.game_state_manager import GameStateManager
from src.engine.chat_history_manager import ChatHistoryManager
from src.engine.scenario_manager import ScenarioManager
from src.models.game_state_models import GameRecord, GameState # Import GameRecord
from src.models.message_models import Message, MessageType # Added Message, MessageType
from src.config.color_utils import gray_text, yellow_text, red_text # Import color utils if needed for commands
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

    # +++ Argument Parsing +++
    parser = argparse.ArgumentParser(description="运行 TTRPG NPC 游戏引擎")
    parser.add_argument("--load-record", type=str, help="指定要加载的游戏记录文件路径 (.json)")
    parser.add_argument("--load-round", type=int, help="指定要从记录文件中加载的回合数")
    args = parser.parse_args()
    # --- End Argument Parsing ---

    # --- Initialize variables ---
    record_dir = "game_records" # Keep default record dir
    log_file = None # For the .log file (separate from .json record)
    record_filename_log = None # For the .log filename
    record_path_json = args.load_record # Path for the .json record file (from args)
    load_mode = bool(args.load_record and args.load_round is not None)
    target_round = args.load_round if load_mode else -1
    start_round_engine = 1 # Default for new game
    loaded_state: Optional[GameState] = None
    chat_history_manager: Optional[ChatHistoryManager] = None
    game_state_manager: Optional[GameStateManager] = None
    scenario_manager: Optional[ScenarioManager] = None
    # --- End variable initialization ---

    try:
        # --- Setup .log file (always create a new one for runner logs) ---
        os.makedirs(record_dir, exist_ok=True)
        timestamp_str_log = datetime.now().strftime("%Y%m%d_%H%M%S")
        record_filename_log = os.path.join(record_dir, f"runner_{timestamp_str_log}.log")
        log_file = open(record_filename_log, 'a', encoding='utf-8')
        logging.info(f"CLI Runner 日志文件已打开: {record_filename_log}")
        # --- End .log file setup ---

        # --- Create Input Handler ---
        cli_input_handler = CliInputHandler()
        # --- End Input Handler Creation ---

        # --- Create Game Engine ---
        # We create the engine instance first, then decide how to start it
        engine = GameEngine(
            max_rounds=5, # Or load from config/record later if needed
            record_handler=game_record_handler, # Pass the .log handler
            record_file_handle=log_file,        # Pass the .log file handle
            input_handler=cli_input_handler
        )
        # --- End Engine Creation ---

        if load_mode:
            # --- Load Game from Record ---
            print(f"尝试从记录 '{record_path_json}' 加载回合 {target_round}...")
            log_file.write(f"--- Loading Game from Record: {record_path_json}, Round: {target_round} ---\n")

            if not os.path.exists(record_path_json):
                print(red_text(f"错误：找不到指定的记录文件 '{record_path_json}'"))
                log_file.write(f"Error: Record file not found '{record_path_json}'\n")
                return # Exit if record file doesn't exist

            # 1. Read scenario_id from the record file first
            scenario_id_from_record = None
            try:
                with open(record_path_json, 'r', encoding='utf-8') as f_record:
                    record_data = json.load(f_record)
                # Validate basic structure and get scenario_id
                if isinstance(record_data, dict) and 'scenario_id' in record_data:
                     scenario_id_from_record = record_data['scenario_id']
                else:
                    raise ValueError("记录文件缺少 'scenario_id' 字段或格式无效")
            except Exception as read_err:
                 print(red_text(f"错误：读取或解析记录文件 '{record_path_json}' 以获取 scenario_id 时出错: {read_err}"))
                 log_file.write(f"Error reading/parsing record for scenario_id: {read_err}\n")
                 return

            # 2. Initialize ScenarioManager and load the correct scenario
            scenario_manager = ScenarioManager()
            try:
                scenario = scenario_manager.load_scenario(scenario_id_from_record)
                if not scenario:
                     raise ValueError(f"无法从 ScenarioManager 加载剧本 ID: {scenario_id_from_record}")
                print(f"已加载记录中的剧本: {scenario_id_from_record}")
                log_file.write(f"Loaded scenario from record: {scenario_id_from_record}\n")
            except Exception as scenario_err:
                print(red_text(f"错误：加载记录文件 '{record_path_json}' 中指定的剧本 '{scenario_id_from_record}' 失败: {scenario_err}"))
                log_file.write(f"Error loading scenario '{scenario_id_from_record}': {scenario_err}\n")
                return

            # 3. Initialize Managers
            game_state_manager = GameStateManager(scenario_manager=scenario_manager)
            chat_history_manager = ChatHistoryManager()

            # 4. Load State and History
            state_loaded = game_state_manager.load_state(record_path_json, target_round)
            history_loaded = chat_history_manager.load_history(record_path_json, target_round)

            if not state_loaded or not history_loaded:
                print(red_text(f"错误：从记录 '{record_path_json}' 加载回合 {target_round} 失败。请检查日志。"))
                log_file.write(f"Error loading state or history from '{record_path_json}' for round {target_round}\n")
                return # Exit if loading failed

            loaded_state = game_state_manager.get_state()
            start_round_engine = target_round + 1 # Start from the next round

            # 5. Start Engine from Loaded State (Method to be added in GameEngine)
            print(f"加载成功。将从回合 {start_round_engine} 继续游戏...")
            log_file.write(f"Load successful. Starting engine from round {start_round_engine}\n")
            log_file.flush()
            # We need to pass the initialized managers and the loaded state
            # This requires modifying GameEngine to accept these
            await engine.start_from_loaded_state(
                loaded_state=loaded_state,
                game_state_manager=game_state_manager,
                chat_history_manager=chat_history_manager,
                scenario_manager=scenario_manager, # Pass scenario manager too
                start_round=start_round_engine,
                record_path=record_path_json # Pass the path for continued saving
            )
            # --- End Load Game ---
        else:
            # --- Start New Game ---
            print("未指定加载参数，开始新游戏...")
            log_file.write(f"--- Starting New Game: {timestamp_str_log} ---\n")
            log_file.flush()
            # Call the original run_game which handles all initializations
            await engine.run_game()
            # --- End Start New Game ---


        # Write end message to log file
        end_message = f"--- Game Session Ended ---\n"
        log_file.write(end_message)
        log_file.flush()

        logging.info("=== 游戏会话正常结束 (CLI Runner) ===")

    except KeyboardInterrupt:
        logging.warning("游戏被用户中断 (CLI Runner)")
        print("\n游戏被用户中断")
        if log_file:
            log_file.write("\n--- Game Interrupted by User ---\n")
    except Exception as e:
        logging.exception(f"游戏出错 (CLI Runner): {str(e)}")
        print(red_text(f"\n游戏出错: {str(e)}")) # Use red_text helper
        if log_file:
            log_file.write(f"\n--- Game Error: {str(e)} ---\n")
    finally:
        if log_file:
            try:
                log_file.close()
                logging.info(f"CLI Runner 日志文件已关闭: {record_filename_log}")
            except Exception as close_err:
                 logging.error(f"关闭 CLI Runner 日志文件时出错: {close_err}")
        logging.info("CLI Runner main function finished.")

if __name__ == "__main__":
    # 启动异步事件循环
    asyncio.run(main())
