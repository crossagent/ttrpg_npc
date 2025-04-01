from autogen_agentchat.messages import TextMessage, ChatMessage
from typing import Dict, List, Any, Callable, Optional, TextIO # Added TextIO
import asyncio
from datetime import datetime
import uuid
import os # Added os

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

from src.config.color_utils import (
    format_dm_message, format_player_message, format_observation,
    format_state, format_thinking, print_colored,
    Color, green_text, yellow_text, gray_text
)

# 默认配置
DEFAULT_MAX_ROUNDS = 5

# Original handler kept for reference or potential future use if needed
# def message_display_handler(message: Message) -> None:
#     """处理消息显示的函数"""
#     source = message.source
#     content = message.content
    
#     # 根据消息来源确定显示格式
#     if source.lower() == "dm":
#         print(format_dm_message(source, content))
#     elif source.lower() == "human_player" or source.lower() == "human":
#         print(gray_text(f'{source}: {content}'))
#     else:
#         print(format_player_message(source, content))

class GameEngine:
    """
    游戏引擎类，负责初始化游戏配置和状态，创建并管理所有Agent，建立GroupChat，并提供游戏启动接口
    """
    
    def __init__(self, max_rounds: int = DEFAULT_MAX_ROUNDS):
        """
        初始化游戏引擎
        
        Args:
            max_rounds: 最大回合数，默认为配置中的DEFAULT_MAX_ROUNDS
        """
        self.round_manager = None # Initialize round_manager

    async def run_game(self) -> None:
        """
        启动游戏，执行回合流程
        
        Returns:
            GameState: 游戏结束后的最终状态
        """
        # --- Game Record Setup ---
        record_dir = "game_records"
        os.makedirs(record_dir, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        record_filename = os.path.join(record_dir, f"record_{timestamp_str}.log")
        # --- End Game Record Setup ---

        try:
            with open(record_filename, 'a', encoding='utf-8') as log_file:
                
                def _message_display_and_log_handler(message: Message, log_file_handle: TextIO) -> None:
                    """处理消息显示并记录到文件"""
                    source = message.source
                    content = message.content
                    formatted_output = ""
                    
                    # 根据消息来源确定显示格式
                    if source.lower() == "dm":
                        formatted_output = format_dm_message(source, content)
                    elif source.lower() == "human_player" or source.lower() == "human":
                        formatted_output = gray_text(f'{source}: {content}') # Keep color codes for console
                        log_output = f'{source}: {content}' # Log without color codes
                    else:
                        formatted_output = format_player_message(source, content)
                        log_output = f'{source}: {content}' # Log without color codes

                    # Print to console (with potential color codes)
                    print(formatted_output)
                    
                    # Write to log file (without color codes for cleaner logs)
                    # Use log_output if defined, otherwise use formatted_output (stripping colors might be complex)
                    # A simpler approach for now: just write the formatted output, accepting color codes in the log.
                    # Or, reconstruct the basic string:
                    log_line = f"{source}: {content}\n" # Simple reconstruction
                    log_file_handle.write(log_line)
                    log_file_handle.flush() # Ensure it's written immediately

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

                # Register the new handler that also logs
                # Use lambda to pass the log_file handle to the handler
                message_dispatcher.register_message_handler(
                    lambda msg: _message_display_and_log_handler(msg, log_file), 
                    list(MessageType)
                )

                # 创建回合管理器
                round_manager = RoundManager(
                    game_state_manager = game_state_manager,
                    message_dispatcher = message_dispatcher,
                    agent_manager = agent_manager,
                    scenario_manager = scenario_manager)
                
                # 保存回合管理器的引用，以便CLI可以访问
                self.round_manager = round_manager
                
                # Log game start
                start_message = f"--- Game Started: {timestamp_str} ---\n"
                print(green_text(start_message.strip()))
                log_file.write(start_message)
                log_file.flush()

                # 执行游戏循环
                while not round_manager.should_terminate(game_state):
                    game_state = await round_manager.execute_round(game_state)
                    
                    # 检查是否有命令
                    cmd_prompt = "输入命令(例如 /history warrior /chat)或按回车继续: "
                    print(cmd_prompt, end="") # Print prompt without newline
                    log_file.write(f"\n> {cmd_prompt}") # Log the prompt
                    log_file.flush()
                    
                    cmd = input().strip()
                    log_file.write(f"{cmd}\n") # Log user input
                    log_file.flush()

                    if cmd.startswith("/"):
                        parts = cmd.split()
                        command = parts[0]
                        args = parts[1:] if len(parts) > 1 else []
                        
                        # Log command execution attempt
                        cmd_log_msg = f"Executing command: {cmd}\n"
                        print(gray_text(cmd_log_msg.strip()))
                        log_file.write(cmd_log_msg)
                        log_file.flush()

                        if command == "/history" and args:
                            # Note: _show_player_history prints directly, need modification to log
                            await self._show_player_history(args[0], log_file) 
                        elif command == "/chat":
                             # Note: _show_chat_history prints directly, need modification to log
                            await self._show_chat_history(log_file)
                        elif command == "/quit":
                            quit_msg = "Quitting game via command.\n"
                            print(yellow_text(quit_msg.strip()))
                            log_file.write(quit_msg)
                            log_file.flush()
                            break
                        else:
                            unknown_cmd_msg = "未知命令，可用命令: /history [玩家名称], /chat, /quit\n"
                            print(yellow_text(unknown_cmd_msg.strip()))
                            log_file.write(unknown_cmd_msg)
                            log_file.flush()
                
                end_message = f"--- Game Ended: 共进行了{game_state.round_number}回合 ---\n"
                print(green_text(end_message.strip()))
                log_file.write(end_message)
                log_file.flush()

        except KeyboardInterrupt:
            interrupt_msg = "\n游戏被用户中断\n"
            print(yellow_text(interrupt_msg.strip()))
            # Attempt to log interruption if log_file was opened
            try:
                with open(record_filename, 'a', encoding='utf-8') as log_file_interrupt:
                     log_file_interrupt.write(interrupt_msg)
            except NameError: # If log_file wasn't defined yet
                pass 
        except Exception as e:
            error_msg = f"\n游戏出错: {str(e)}\n"
            print(red_text(error_msg.strip())) # Assuming red_text exists or use yellow
             # Attempt to log error if log_file was opened
            try:
                with open(record_filename, 'a', encoding='utf-8') as log_file_error:
                     log_file_error.write(error_msg)
            except NameError:
                 pass
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
    
    # Modified to accept log_file handle
    async def _show_player_history(self, player_id: str, log_file: Optional[TextIO] = None) -> None:
        """
        显示指定玩家的聊天历史并记录
        """
        if not self.round_manager or not self.round_manager.message_dispatcher:
            no_dispatcher_msg = "消息分发器未初始化\n"
            print(yellow_text(no_dispatcher_msg.strip()))
            if log_file: log_file.write(no_dispatcher_msg); log_file.flush()
            return
            
        messages = self.round_manager.message_dispatcher.get_message_history(player_id)
        
        if not messages:
            no_messages_msg = f"玩家 {player_id} 没有可见的消息\n"
            print(yellow_text(no_messages_msg.strip()))
            if log_file: log_file.write(no_messages_msg); log_file.flush()
            return
            
        header = f"\n--- {player_id} 的消息历史 ---\n"
        print(header.strip())
        if log_file: log_file.write(header); log_file.flush()

        for message in messages:
            sender = message.source if hasattr(message, 'source') else "未知"
            content = message.content if hasattr(message, 'content') else str(message)
            timestamp = message.timestamp if hasattr(message, 'timestamp') else "未知时间"
            
            history_line_console = f"\n[{timestamp}] {sender}: {content}"
            history_line_log = f"[{timestamp}] {sender}: {content}\n"
            
            print(history_line_console.strip()) # Print without extra newline
            if log_file: log_file.write(history_line_log); log_file.flush()
            
        footer = "\n" + "-" * 50 + "\n"
        print(footer.strip())
        if log_file: log_file.write(footer); log_file.flush()

    # Modified to accept log_file handle
    async def _show_chat_history(self, log_file: Optional[TextIO] = None) -> None:
        """
        显示全局聊天历史并记录
        """
        # Assuming self.state exists and has chat_history - needs verification
        # This method seems to rely on a 'self.state' which isn't initialized in __init__
        # Let's assume it's populated elsewhere or this method is currently unused/broken
        # For safety, add a check.
        if not hasattr(self, 'state') or not self.state.chat_history:
            no_history_msg = "全局聊天历史不可用或为空\n"
            print(yellow_text(no_history_msg.strip()))
            if log_file: log_file.write(no_history_msg); log_file.flush()
            return
        
        header = "\n--- 全局聊天历史 ---\n"
        print(header.strip())
        if log_file: log_file.write(header); log_file.flush()

        for message in self.state.chat_history:
            # 获取消息来源和内容
            source = message.source if hasattr(message, 'source') else "未知"
            content = message.content if hasattr(message, 'content') else str(message)
            timestamp = message.timestamp if hasattr(message, 'timestamp') else "未知时间"
            
            log_line = f"[{timestamp}] {source}: {content}\n"
            console_line = ""

            # 根据消息来源确定颜色
            if source == "dm":
                console_line = f"\n[{timestamp}] {format_dm_message(source, content)}"
            elif source == "human_player":
                console_line = f"\n[{timestamp}] {gray_text(f'{source}: {content}')}"
            else:
                console_line = f"\n[{timestamp}] {format_player_message(source, content)}"
            
            print(console_line.strip()) # Print without extra newline
            if log_file: log_file.write(log_line); log_file.flush()
        
        footer = "\n" + "-" * 50 + "\n"
        print(footer.strip())
        if log_file: log_file.write(footer); log_file.flush()

# Helper function for red text (assuming it might be missing)
def red_text(text):
    return f"\033[91m{text}\033[0m"
