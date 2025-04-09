from autogen_agentchat.messages import TextMessage, ChatMessage
from typing import Dict, List, Any, Callable, Optional, TextIO # Re-added TextIO for type hint
import asyncio
from datetime import datetime
import uuid
import os # +++ Import os +++

# 导入我们的数据模型和Agent
from src.models.schema import AgentConfig
from src.models.game_state_models import GameState
from src.agents.companion_agent import CompanionAgent
from src.communication.message_dispatcher import MessageDispatcher
from src.engine.agent_manager import AgentManager
from src.engine.game_state_manager import GameStateManager
from src.engine.scenario_manager import ScenarioManager
from src.engine.round_manager import RoundManager
from src.engine.chat_history_manager import ChatHistoryManager # Import ChatHistoryManager
from src.models.message_models import Message, MessageType
from src.utils.display_utils import format_message_display_parts # Import the new util function
from src.io.input_handler import UserInputHandler # Import UserInputHandler

from src.config.color_utils import (
    format_dm_message, format_player_message, format_observation,
    format_state, format_thinking, print_colored,
    Color, green_text, yellow_text, gray_text, red_text # Added red_text import
)

# 默认配置
DEFAULT_MAX_ROUNDS = 5

# --- Simple Console Display Handler ---
def simple_console_display_handler(message: Message) -> None:
    """简单的控制台消息显示处理器，现在使用通用格式化逻辑"""
    content = message.content if hasattr(message, 'content') else str(message)

    # 调用工具函数获取格式化后的来源和前缀
    source_display, prefix = format_message_display_parts(message)

    # 组合最终的输出字符串 (无颜色)
    base_output = f"{source_display}: {prefix}{content}"

    # 根据原始来源应用颜色
    original_source = message.source if hasattr(message, 'source') else ""
    if original_source.lower() == "dm":
        print(format_dm_message(source_display, f"{prefix}{content}")) # Pass parts to color func
    elif original_source.lower() == "human_player" or original_source.lower() == "human":
        print(gray_text(base_output))
    elif original_source.lower() == "裁判":
         print(yellow_text(base_output)) # Example: Yellow for referee
    else: # Default for other players/NPCs
        # format_player_message might need adjustment if it assumes only source/content
        # Let's try passing the pre-formatted source_display and the rest
        print(format_player_message(source_display, f"{prefix}{content}"))
# --- End Simple Console Display Handler ---


class GameEngine:
    """
    游戏引擎类，负责初始化游戏配置和状态，创建并管理所有Agent，建立GroupChat，并提供游戏启动接口
    """

    def __init__(self,
                 max_rounds: int = DEFAULT_MAX_ROUNDS,
                 record_handler: Optional[Callable[[Message, TextIO], None]] = None,
                 record_file_handle: Optional[TextIO] = None,
                 input_handler: Optional[UserInputHandler] = None): # Add input_handler parameter
        """
        初始化游戏引擎

        Args:
            max_rounds: 最大回合数，默认为配置中的DEFAULT_MAX_ROUNDS
            record_handler: (可选) 用于记录游戏消息的处理器函数。
            record_file_handle: (可选) 传递给记录处理器的文件句柄。
            input_handler: (可选) 用于处理用户输入的处理器。
        """
        self.max_rounds = max_rounds # Store max_rounds
        self.round_manager = None
        self.message_dispatcher = None
        self._record_handler = record_handler
        self._record_file_handle = record_file_handle
        self._input_handler = input_handler # Store input_handler
        self._saves_path: Optional[str] = None # +++ Add instance variable for record path +++

    async def _run_game_loop(self,
                             game_state: GameState,
                             game_state_manager: GameStateManager,
                             chat_history_manager: ChatHistoryManager,
                             round_manager: RoundManager,
                             start_round: int,
                             record_path: str) -> GameState:
        """
        Internal game loop logic.

        Args:
            game_state: The initial or loaded game state.
            game_state_manager: Initialized GameStateManager.
            chat_history_manager: Initialized ChatHistoryManager.
            round_manager: Initialized RoundManager.
            start_round: The round number to start from.
            record_path: Path to the JSON record file for saving.

        Returns:
            GameState: The final game state after the loop finishes.
        """
        current_game_state = game_state
        # Adjust round number if starting from loaded state
        current_game_state.round_number = start_round - 1

        while not round_manager.should_terminate(current_game_state):
            # Execute the round logic (execute_round increments the round number internally)
            current_game_state = await round_manager.execute_round(current_game_state)

            # +++ Save state and history after round execution +++
            completed_round_number = current_game_state.round_number # Round number is updated in start_round
            # Get snapshot from memory (created by end_round)
            final_snapshot = game_state_manager.get_snapshot(completed_round_number)
            # Get messages from memory (added during the round)
            round_messages = chat_history_manager.get_messages(completed_round_number)

            if final_snapshot:
                # Save the state snapshot to the record file
                game_state_manager.save_state(record_path, final_snapshot)
                # Save the chat history for this round to the record file
                chat_history_manager.save_history(record_path, completed_round_number, round_messages)
            else:
                # Log an error if snapshot wasn't found (shouldn't happen if end_round worked)
                print(red_text(f"错误：未能获取回合 {completed_round_number} 的快照，无法保存！"))
            # --- End saving logic ---

        return current_game_state


    async def run_game(self) -> None:
        """
        启动新游戏，初始化所有内容并执行回合流程。

        Returns:
            None: This method now orchestrates setup and calls the loop.
        """
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S") # For filename and start message

        # Define record path for the new game
        save_dir = "game_saves"
        save_filename = f"record_{timestamp_str}.json"
        self._saves_path = os.path.join(save_dir, save_filename) # Store path in instance variable
        print(f"本局新游戏记录将保存至: {self._saves_path}")
        os.makedirs(save_dir, exist_ok=True)

        game_state_manager: Optional[GameStateManager] = None
        chat_history_manager: Optional[ChatHistoryManager] = None
        round_manager: Optional[RoundManager] = None
        initial_game_state: Optional[GameState] = None

        try:
            # --- Start Initialization for New Game ---
            # 1. Load Scenario
            scenario_manager = ScenarioManager()
            scenario = scenario_manager.load_scenario("default") # Assuming default for new games

            # 2. Character Selection
            playable_characters = {
                char_id: char_info
                for char_id, char_info in scenario.characters.items()
                if char_info.is_playable
            }

            if not playable_characters:
                print(red_text("错误：剧本中没有可供选择的角色！"))
                return # 或者抛出异常

            print(green_text("\n请选择你的角色:"))
            playable_list = list(playable_characters.items())
            for i, (char_id, char_info) in enumerate(playable_list):
                print(f"  {i + 1}. {char_info.name} ({char_info.public_identity})")

            chosen_id = None
            while not chosen_id:
                try:
                    choice = input(f"输入选择的角色编号 (1-{len(playable_list)}): ")
                    choice_index = int(choice) - 1
                    if 0 <= choice_index < len(playable_list):
                        chosen_id = playable_list[choice_index][0]
                        chosen_name = playable_list[choice_index][1].name
                        print(green_text(f"你选择了: {chosen_name} ({chosen_id})"))
                    else:
                        print(yellow_text("无效的选择，请输入列表中的编号。"))
                except ValueError:
                    print(yellow_text("无效的输入，请输入数字编号。"))
            # --- End Character Selection ---

            # 3. Initialize Managers
            game_state_manager = GameStateManager(scenario_manager=scenario_manager)
            initial_game_state = game_state_manager.initialize_game_state()

            # Set player character ID
            initial_game_state.player_character_id = chosen_id
            print(f"游戏状态已设置玩家角色ID: {initial_game_state.player_character_id}")

            chat_history_manager = ChatHistoryManager()

            # 4. Initialize AgentManager
            agent_manager = AgentManager(
                game_state=initial_game_state,
                scenario_manager=scenario_manager,
                chat_history_manager=chat_history_manager,
                game_state_manager=game_state_manager
            )
            agent_manager.initialize_agents_from_characters(scenario)

            # 5. Initialize MessageDispatcher
            self.message_dispatcher = MessageDispatcher(
                game_state_manager=game_state_manager,
                agent_manager=agent_manager,
                chat_history_manager=chat_history_manager
            )

            # Register console handler
            self.message_dispatcher.register_message_handler(
                simple_console_display_handler,
                list(MessageType)
            )

            # Register external .log handler
            if self._record_handler and self._record_file_handle:
                try:
                    self.message_dispatcher.register_message_handler(
                        lambda msg: self._record_handler(msg, self._record_file_handle),
                        list(MessageType)
                    )
                except Exception as e:
                    print(f"Error registering external record handler: {e}")

            # 6. Initialize RoundManager
            round_manager = RoundManager(
                game_state_manager=game_state_manager,
                message_dispatcher=self.message_dispatcher,
                agent_manager=agent_manager,
                scenario_manager=scenario_manager,
                chat_history_manager=chat_history_manager,
                input_handler=self._input_handler
            )
            self.round_manager = round_manager # Store reference
            # --- End Initialization for New Game ---

            # Log game start to console
            start_message = f"--- New Game Started: {timestamp_str} ---"
            print(green_text(start_message))

            # Execute the game loop
            final_state = await self._run_game_loop(
                game_state=initial_game_state,
                game_state_manager=game_state_manager,
                chat_history_manager=chat_history_manager,
                round_manager=round_manager,
                start_round=1,
                record_path=self._saves_path
            )

            end_message = f"--- Game Ended: 共进行了{final_state.round_number}回合 ---"
            print(green_text(end_message))

        except KeyboardInterrupt:
            print(yellow_text("\n游戏被用户中断"))
        except Exception as e:
            print(red_text(f"\n游戏运行出错: {str(e)}"))
            # Log the exception traceback for debugging
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()

        # run_game doesn't need to return state anymore
        return


    async def start_from_loaded_state(self,
                                      loaded_state: GameState,
                                      game_state_manager: GameStateManager,
                                      chat_history_manager: ChatHistoryManager,
                                      scenario_manager: ScenarioManager,
                                      start_round: int,
                                      record_path: str) -> None:
        """
        Starts the game engine with pre-loaded state and managers.

        Args:
            loaded_state: The GameState loaded from the record.
            game_state_manager: Initialized GameStateManager containing the loaded state.
            chat_history_manager: Initialized ChatHistoryManager containing loaded history.
            scenario_manager: Initialized ScenarioManager with the correct scenario loaded.
            start_round: The round number to begin execution from.
            record_path: Path to the JSON record file for continued saving.
        """
        self._saves_path = record_path # Store record path for saving
        agent_manager: Optional[AgentManager] = None
        round_manager: Optional[RoundManager] = None

        try:
            # --- Initialize components with loaded data ---
            # 1. AgentManager (needs loaded state)
            agent_manager = AgentManager(
                game_state=loaded_state,
                scenario_manager=scenario_manager,
                chat_history_manager=chat_history_manager,
                game_state_manager=game_state_manager
            )
            # Need to get scenario object to initialize agents
            scenario = scenario_manager.get_current_scenario()
            if not scenario:
                 raise ValueError("无法从 ScenarioManager 获取当前剧本以初始化 Agent")
            agent_manager.initialize_agents_from_characters(scenario)

            # 2. MessageDispatcher
            self.message_dispatcher = MessageDispatcher(
                game_state_manager=game_state_manager,
                agent_manager=agent_manager,
                chat_history_manager=chat_history_manager
            )
            # Register handlers
            self.message_dispatcher.register_message_handler(
                simple_console_display_handler, list(MessageType)
            )
            if self._record_handler and self._record_file_handle:
                try:
                    self.message_dispatcher.register_message_handler(
                        lambda msg: self._record_handler(msg, self._record_file_handle),
                        list(MessageType)
                    )
                except Exception as e:
                    print(f"Error registering external record handler in loaded game: {e}")

            # 3. RoundManager
            round_manager = RoundManager(
                game_state_manager=game_state_manager,
                message_dispatcher=self.message_dispatcher,
                agent_manager=agent_manager,
                scenario_manager=scenario_manager,
                chat_history_manager=chat_history_manager,
                input_handler=self._input_handler
            )
            self.round_manager = round_manager # Store reference
            # --- End Initialization ---

            # Log game resume
            start_message = f"--- Game Resumed from Record: {record_path}, Round: {start_round} ---"
            print(green_text(start_message))

            # Execute the game loop starting from the specified round
            final_state = await self._run_game_loop(
                game_state=loaded_state,
                game_state_manager=game_state_manager,
                chat_history_manager=chat_history_manager,
                round_manager=round_manager,
                start_round=start_round,
                record_path=self._saves_path
            )

            end_message = f"--- Game Ended: 共进行了{final_state.round_number}回合 (从回合 {start_round} 继续) ---"
            print(green_text(end_message))

        except KeyboardInterrupt:
            print(yellow_text("\n游戏被用户中断"))
        except Exception as e:
            print(red_text(f"\n游戏运行出错: {str(e)}"))
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()

        return


    async def cleanup(self) -> None:
        """
        清理游戏资源
        """
        # 清理消息组件
        self.round_manager = None
        self.message_dispatcher = None # Clear dispatcher reference
        self._saves_path = None # Clear record path

    # Removed log_file parameter
    async def _show_player_history(self, player_id: str) -> None:
        """
        显示指定玩家的聊天历史
        """
        # Use stored message_dispatcher reference
        if not self.message_dispatcher:
            no_dispatcher_msg = "消息分发器未初始化"
            print(yellow_text(no_dispatcher_msg))
            # Removed log writing
            return

        messages = self.message_dispatcher.get_message_history(player_id)

        if not messages:
            no_messages_msg = f"玩家 {player_id} 没有可见的消息"
            print(yellow_text(no_messages_msg))
            # Removed log writing
            return

        header = f"\n--- {player_id} 的消息历史 ---"
        print(header)
        # Removed log writing

        for message in messages:
            sender = message.source if hasattr(message, 'source') else "未知"
            content = message.content if hasattr(message, 'content') else str(message)
            timestamp = message.timestamp if hasattr(message, 'timestamp') else "未知时间"

            history_line_console = f"\n[{timestamp}] {sender}: {content}"
            # Removed history_line_log

            print(history_line_console.strip()) # Print without extra newline
            # Removed log writing

        footer = "\n" + "-" * 50
        print(footer)
        # Removed log writing

    # Removed log_file parameter
    async def _show_chat_history(self) -> None:
        """
        显示全局聊天历史
        """
        # Assuming self.round_manager.game_state_manager.get_state() provides state
        # Access history via the ChatHistoryManager stored in the dispatcher
        if not self.message_dispatcher or not hasattr(self.message_dispatcher, 'chat_history_manager'):
             no_history_msg = "全局聊天历史不可用 (无聊天记录管理器)"
             print(yellow_text(no_history_msg))
             # Removed log writing
             return

        # Get all messages directly from the ChatHistoryManager
        all_messages = self.message_dispatcher.chat_history_manager.get_all_messages()

        if not all_messages:
            no_history_msg = "全局聊天历史不可用或为空"
            print(yellow_text(no_history_msg))
            # Removed log writing
            return

        header = "\n--- 全局聊天历史 ---"
        print(header)
        # Removed log writing

        for message in all_messages:
            # 获取消息来源和内容
            source = message.source if hasattr(message, 'source') else "未知"
            content = message.content if hasattr(message, 'content') else str(message)
            timestamp = message.timestamp if hasattr(message, 'timestamp') else "未知时间"

            # Removed log_line
            console_line = ""

            # 根据消息来源确定颜色
            if source == "dm":
                console_line = f"\n[{timestamp}] {format_dm_message(source, content)}"
            elif source == "human_player":
                console_line = f"\n[{timestamp}] {gray_text(f'{source}: {content}')}"
            else:
                console_line = f"\n[{timestamp}] {format_player_message(source, content)}"

            print(console_line.strip()) # Print without extra newline
            # Removed log writing

        footer = "\n" + "-" * 50
        print(footer)
        # Removed log writing

# Removed red_text helper function definition, assuming it's imported from color_utils
