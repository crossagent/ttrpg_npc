from autogen_agentchat.messages import TextMessage, ChatMessage
from typing import Dict, List, Any, Callable, Optional, TextIO # Re-added TextIO for type hint
import asyncio
from datetime import datetime
import uuid
# Removed os import, no longer needed here

# 导入我们的数据模型和Agent
from src.models.schema import AgentConfig
from src.models.game_state_models import GameState
from src.agents.player_agent import PlayerAgent
from src.communication.message_dispatcher import MessageDispatcher
from src.engine.agent_manager import AgentManager
from src.engine.game_state_manager import GameStateManager
from src.engine.scenario_manager import ScenarioManager
from src.engine.round_manager import RoundManager
from src.models.message_models import Message, MessageType
from src.utils.display_utils import format_message_display_parts # Import the new util function

from src.config.color_utils import (
    format_dm_message, format_player_message, format_observation,
    format_state, format_thinking, print_colored,
    Color, green_text, yellow_text, gray_text
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
                 record_file_handle: Optional[TextIO] = None):
        """
        初始化游戏引擎

        Args:
            max_rounds: 最大回合数，默认为配置中的DEFAULT_MAX_ROUNDS
            record_handler: (可选) 用于记录游戏消息的处理器函数。
            record_file_handle: (可选) 传递给记录处理器的文件句柄。
        """
        self.max_rounds = max_rounds # Store max_rounds
        self.round_manager = None
        self.message_dispatcher = None
        self._record_handler = record_handler
        self._record_file_handle = record_file_handle

    async def run_game(self) -> None:
        """
        启动游戏，执行回合流程

        Returns:
            GameState: 游戏结束后的最终状态
        """
        # --- Game Record Setup Removed - To be handled by runner ---
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S") # Keep timestamp for start message

        try:
            # 加载剧本
            scenario_manager = ScenarioManager()
            scenario = scenario_manager.load_scenario("default")

            # 初始化游戏状态
            game_state_manager = GameStateManager()
            game_state = game_state_manager.initialize_game_state(scenario)

            # 创建代理管理器
            agent_manager = AgentManager(
                game_state=game_state
            )
            agent_manager.initialize_agents_from_characters(scenario)

            # 初始化通信组件
            message_dispatcher = MessageDispatcher(
                game_state=game_state,
                agent_manager=agent_manager
            )
            self.message_dispatcher = message_dispatcher # Store reference

            # Register the simple console display handler (always active)
            message_dispatcher.register_message_handler(
                simple_console_display_handler,
                list(MessageType)
            )

            # --- Register the external record handler if provided ---
            if self._record_handler and self._record_file_handle:
                try:
                    # Use lambda to pass the file handle stored in self
                    message_dispatcher.register_message_handler(
                        lambda msg: self._record_handler(msg, self._record_file_handle),
                        list(MessageType) # Register for all message types
                    )
                    # Logging this registration might be better done in the runner
                    # print(f"External record handler registered.")
                except Exception as e:
                    # Log error if registration fails
                    print(f"Error registering external record handler: {e}")
            # --- End record handler registration ---


            # 创建回合管理器
            round_manager = RoundManager(
                game_state_manager = game_state_manager,
                message_dispatcher = message_dispatcher,
                agent_manager = agent_manager,
                scenario_manager = scenario_manager)

            # 保存回合管理器的引用，以便CLI可以访问
            self.round_manager = round_manager

            # Log game start (to console only now)
            start_message = f"--- Game Started: {timestamp_str} ---"
            print(green_text(start_message))
            # Removed log_file.write

            # 执行游戏循环
            while not round_manager.should_terminate(game_state):
                game_state = await round_manager.execute_round(game_state)

                # 检查是否有命令
                cmd_prompt = "输入命令(例如 /history warrior /chat)或按回车继续: "
                print(cmd_prompt, end="") # Print prompt without newline
                # Removed log_file.write

                cmd = input().strip()
                # Removed log_file.write

                if cmd.startswith("/"):
                    parts = cmd.split()
                    command = parts[0]
                    args = parts[1:] if len(parts) > 1 else []

                    # Log command execution attempt (to console only)
                    cmd_log_msg = f"Executing command: {cmd}"
                    print(gray_text(cmd_log_msg))
                    # Removed log_file.write

                    if command == "/history" and args:
                        # Removed log_file argument
                        await self._show_player_history(args[0])
                    elif command == "/chat":
                         # Removed log_file argument
                        await self._show_chat_history()
                    elif command == "/quit":
                        quit_msg = "Quitting game via command."
                        print(yellow_text(quit_msg))
                        # Removed log_file.write
                        break
                    else:
                        unknown_cmd_msg = "未知命令，可用命令: /history [玩家名称], /chat, /quit"
                        print(yellow_text(unknown_cmd_msg))
                        # Removed log_file.write

            end_message = f"--- Game Ended: 共进行了{game_state.round_number}回合 ---"
            print(green_text(end_message))
            # Removed log_file.write

        except KeyboardInterrupt:
            interrupt_msg = "\n游戏被用户中断"
            print(yellow_text(interrupt_msg))
            # Removed log writing attempt
        except Exception as e:
            error_msg = f"\n游戏出错: {str(e)}"
            # Assuming red_text exists or use yellow
            print(red_text(error_msg))
            # Removed log writing attempt
        finally:
            # 清理资源
            await self.cleanup()

        return

    async def cleanup(self) -> None:
        """
        清理游戏资源
        """
        # 清理消息组件
        self.round_manager = None
        self.message_dispatcher = None # Clear dispatcher reference

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
        # Or better, access via self.round_manager.message_dispatcher if it stores history
        # Let's assume dispatcher holds the full history for now
        if not self.message_dispatcher:
             no_history_msg = "全局聊天历史不可用 (无分发器)"
             print(yellow_text(no_history_msg))
             # Removed log writing
             return

        # Assuming get_message_history without player_id returns all messages
        all_messages = self.message_dispatcher.get_message_history()

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

# Helper function for red text (assuming it might be missing)
def red_text(text):
    return f"\033[91m{text}\033[0m"
