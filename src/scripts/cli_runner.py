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
    log_dir = "logs" # <<< Directory for internal runner logs
    game_output_dir = "game_records" # <<< Directory for game message output (.log)
    save_dir = "game_saves" # <<< Directory for .json save files
    game_output_log_file = None # Handle for the game message output .log file
    game_output_filename = None # Filename for the game message output .log file
    load_path_json = args.load_record # Path to load .json from (if specified)
    save_path_json = None # Path to save .json to (will be generated)
    load_mode = bool(args.load_record and args.load_round is not None)
    target_round = args.load_round if load_mode else -1
    start_round_engine = 1 # Default for new game
    loaded_state: Optional[GameState] = None
    chat_history_manager: Optional[ChatHistoryManager] = None
    game_state_manager: Optional[GameStateManager] = None
    scenario_manager: Optional[ScenarioManager] = None
    # --- End variable initialization ---

    try:
        # --- Setup internal runner .log file directory (in logs/) ---
        os.makedirs(log_dir, exist_ok=True)
        # Internal logging setup remains the same (using logging module)
        # setup_logging(level=logging.INFO) # This configures the root logger

        # --- Setup game message output .log file directory (in game_records/) ---
        os.makedirs(game_output_dir, exist_ok=True)
        timestamp_str_game_output = datetime.now().strftime("%Y%m%d_%H%M%S")
        game_output_filename = os.path.join(game_output_dir, f"record_{timestamp_str_game_output}.log")
        game_output_log_file = open(game_output_filename, 'a', encoding='utf-8')
        print(f"游戏消息记录将保存至: {game_output_filename}")
        # --- End game message output .log file setup ---

        # --- Setup .json save file directory (in game_saves/) ---
        os.makedirs(save_dir, exist_ok=True)
        # --- End .json save file setup ---

        # --- Create Input Handler ---
        cli_input_handler = CliInputHandler()
        # --- End Input Handler Creation ---

        # --- Create Game Engine ---
        # We create the engine instance first, then decide how to start it
        engine = GameEngine(
            max_rounds=5, # Or load from config/record later if needed
            record_handler=game_record_handler, # Pass the handler function
            record_file_handle=game_output_log_file, # <<< Pass the game message .log file handle
            input_handler=cli_input_handler
        )
        # --- End Engine Creation ---

        if load_mode:
            # --- Load Game from Record ---
            # Construct full path assuming load_path_json might be relative or just filename
            full_load_path = os.path.abspath(load_path_json) # Get absolute path first
            # Basic check if it's likely within the intended directory (optional but safer)
            if not full_load_path.startswith(os.path.abspath(save_dir)):
                 print(yellow_text(f"警告：加载路径 '{load_path_json}' 不在预期的 '{save_dir}' 目录下。请确保路径正确。"))
                 # Decide if you want to proceed or exit
                 # return

            print(f"尝试从存档 '{full_load_path}' 加载回合 {target_round}...")
            game_output_log_file.write(f"--- Loading Game from Save: {full_load_path}, Round: {target_round} ---\n")

            if not os.path.exists(full_load_path):
                print(red_text(f"错误：找不到指定的存档文件 '{full_load_path}'"))
                game_output_log_file.write(f"Error: Save file not found '{full_load_path}'\n")
                return # Exit if save file doesn't exist

            # 1. Read scenario_id from the save file first
            scenario_id_from_record = None
            try:
                with open(full_load_path, 'r', encoding='utf-8') as f_record:
                    record_data = json.load(f_record)
                # Validate basic structure and get scenario_id
                if isinstance(record_data, dict) and 'scenario_id' in record_data:
                    scenario_id_from_record = record_data['scenario_id']
                else:
                    raise ValueError("存档文件缺少 'scenario_id' 字段或格式无效")
            except Exception as read_err:
                 print(red_text(f"错误：读取或解析存档文件 '{full_load_path}' 以获取 scenario_id 时出错: {read_err}"))
                 game_output_log_file.write(f"Error reading/parsing save file for scenario_id: {read_err}\n")
                 return

            # 2. Initialize ScenarioManager and load the correct scenario
            scenario_manager = ScenarioManager()
            try:
                scenario = scenario_manager.load_scenario(scenario_id_from_record)
                if not scenario:
                     raise ValueError(f"无法从 ScenarioManager 加载剧本 ID: {scenario_id_from_record}")
                print(f"已加载存档中的剧本: {scenario_id_from_record}")
                game_output_log_file.write(f"Loaded scenario from save: {scenario_id_from_record}\n")
            except Exception as scenario_err:
                print(red_text(f"错误：加载存档文件 '{full_load_path}' 中指定的剧本 '{scenario_id_from_record}' 失败: {scenario_err}"))
                game_output_log_file.write(f"Error loading scenario '{scenario_id_from_record}': {scenario_err}\n")
                return

            # 3. Initialize Managers
            game_state_manager = GameStateManager(scenario_manager=scenario_manager)
            chat_history_manager = ChatHistoryManager()

            # 4. Load State and History from the specified load path
            state_loaded = game_state_manager.load_state(full_load_path, target_round)
            history_loaded = chat_history_manager.load_history(full_load_path, target_round)

            if not state_loaded or not history_loaded:
                print(red_text(f"错误：从存档 '{full_load_path}' 加载回合 {target_round} 失败。请检查日志。"))
                game_output_log_file.write(f"Error loading state or history from '{full_load_path}' for round {target_round}\n") # Log to runner log
                return # Exit if loading failed

            loaded_state = game_state_manager.get_state()
            start_round_engine = target_round + 1 # Start from the next round

            # +++ Generate NEW save path for this loaded session +++
            timestamp_str_save = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_filename = os.path.basename(full_load_path).replace('.json', '')
            save_filename = f"{original_filename}_resumed_{timestamp_str_save}.json"
            save_path_json = os.path.join(save_dir, save_filename)
            print(f"本次加载后的游戏将保存至新存档文件: {save_path_json}")
            game_output_log_file.write(f"--- Session Resumed (Loaded from: {full_load_path}) ---\n") # Log resume to game output log
            game_output_log_file.write(f"--- Saving subsequent rounds to: {save_path_json} ---\n")
            game_output_log_file.flush()
            # --- End generating new save path ---

            # 5. Start Engine from Loaded State
            print(f"加载成功。将从回合 {start_round_engine} 继续游戏...")
            # log_file.write(f"Load successful. Starting engine from round {start_round_engine}\n") # Redundant with above
            # log_file.flush() # Flushed above
            await engine.start_from_loaded_state(
                loaded_state=loaded_state,
                game_state_manager=game_state_manager,
                chat_history_manager=chat_history_manager,
                scenario_manager=scenario_manager,
                start_round=start_round_engine,
                record_path=save_path_json # <<< Pass the NEW save path
            )
            # --- End Load Game ---
        else:
            # --- Start New Game ---
            print("未指定加载参数，开始新游戏...")
            game_output_log_file.write(f"--- Starting New Game: {timestamp_str_game_output} ---\n") # Log to game output log

            # +++ Generate save path for the new game +++
            timestamp_str_save = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_filename = f"record_{timestamp_str_save}.json"
            save_path_json = os.path.join(save_dir, save_filename)
            print(f"本局新游戏将保存至存档文件: {save_path_json}")
            game_output_log_file.write(f"--- Saving game state to: {save_path_json} ---\n") # Log to game output log
            # --- End generating save path ---

            game_output_log_file.flush()
            # Set the record path on the engine instance before running
            engine._record_path = save_path_json # Assuming GameEngine uses this internal var now
            # Call the original run_game which handles all initializations
            await engine.run_game()
            # --- End Start New Game ---


        # Write end message to game output log file
        end_message = f"--- Game Session Ended ---\n"
        game_output_log_file.write(end_message)
        game_output_log_file.flush()

        logging.info("=== 游戏会话正常结束 (CLI Runner) ===")

    except KeyboardInterrupt:
        logging.warning("游戏被用户中断 (CLI Runner)")
        print("\n游戏被用户中断")
        if game_output_log_file: # Log interruption to game output log
            game_output_log_file.write("\n--- Game Interrupted by User ---\n")
    except Exception as e:
        logging.exception(f"游戏出错 (CLI Runner): {str(e)}")
        print(red_text(f"\n游戏出错: {str(e)}")) # Use red_text helper
        if game_output_log_file: # Log error to game output log
            game_output_log_file.write(f"\n--- Game Error: {str(e)} ---\n")
    finally:
        # Close the game message output log file
        if game_output_log_file:
            try:
                game_output_log_file.close()
                logging.info(f"游戏消息记录文件已关闭: {game_output_filename}")
            except Exception as close_err:
                logging.error(f"关闭游戏消息记录文件时出错: {close_err}")
        # Internal runner logging is handled by the logging module itself
        logging.info("CLI Runner main function finished.")

if __name__ == "__main__":
    # 启动异步事件循环
    asyncio.run(main())
