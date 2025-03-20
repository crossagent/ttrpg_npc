from autogen_agentchat.agents import AssistantAgent, BaseChatAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage, ChatMessage
from typing import Dict, List, Any, Callable, Optional
import asyncio
from datetime import datetime
import uuid
from autogen_core.models import ModelFamily

# 导入我们的数据模型和Agent
from src.models.schema import AgentConfig
from src.models.game_state_models import GameState
from src.agents.player_agent import PlayerAgent
from src.config.config_loader import load_llm_settings, load_config
from src.communication.message_dispatcher import MessageDispatcher
from src.engine.agent_manager import AgentManager
from src.engine.game_state_manager import GameStateManager
from src.engine.scenario_manager import ScenarioManager
from src.engine.round_manager import RoundManager

from src.config.color_utils import (
    format_dm_message, format_player_message, format_observation,
    format_state, format_thinking, print_colored,
    Color, green_text, yellow_text, gray_text
)

# 默认配置
DEFAULT_MAX_ROUNDS = 5

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
        confing = load_config()
        
        # 加载LLM配置
        llm_settings = load_llm_settings()
        
        # 使用配置初始化模型客户端
        self.model_client = OpenAIChatCompletionClient(
            model=llm_settings.model,
            api_key=llm_settings.openai_api_key,
            temperature=llm_settings.temperature,
            base_url=llm_settings.base_url,
            model_info={
                "name": llm_settings.model,
                "vision": False,
                "function_calling": False,
                "json_output": False,
                'family': ModelFamily.UNKNOWN
            }
        )
        
        self.cancellation_token = CancellationToken() 

    async def run_game(self) -> None:
        """
        启动游戏，执行回合流程
        
        Returns:
            GameState: 游戏结束后的最终状态
        """
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
        
        # 初始化通信组件
        message_dispatcher = MessageDispatcher(
            game_state=game_state,
            agent_manager=agent_manager
        )

        # 创建回合管理器
        round_manager = RoundManager(
            game_state_manager = game_state_manager,
            message_dispatcher = message_dispatcher,
            agent_manager = agent_manager,
            scenario_manager = scenario_manager)
        
        # 保存回合管理器的引用，以便CLI可以访问
        self.round_manager = round_manager
        
        # 执行游戏循环
        while not round_manager.should_terminate(game_state):
            game_state = await round_manager.execute_round(game_state)
            
            # 检查是否有命令
            cmd = input("输入命令(例如 /history warrior /chat)或按回车继续: ").strip()
            if cmd.startswith("/"):
                parts = cmd.split()
                command = parts[0]
                args = parts[1:] if len(parts) > 1 else []
                
                if command == "/history" and args:
                    await self._show_player_history(args[0])
                elif command == "/chat":
                    await self._show_chat_history()
                elif command == "/quit":
                    break
                else:
                    print("未知命令，可用命令: /history [玩家名称], /chat, /quit")
        
        print(green_text(f"游戏结束，共进行了{game_state.round_number}回合。"))
        
        # 清理资源
        await self.cleanup()

        return
    
    async def cleanup(self) -> None:
        """
        清理游戏资源
        """
        # 清理消息组件
        self.round_manager = None
    
    async def _show_player_history(self, player_id: str) -> None:
        """
        显示指定玩家的聊天历史
        
        Args:
            player_id: 玩家ID
        """
        if not self.round_manager or not self.round_manager.message_dispatcher:
            print("消息分发器未初始化")
            return
            
        messages = self.round_manager.message_dispatcher.get_message_history(player_id)
        
        if not messages:
            print(f"玩家 {player_id} 没有可见的消息")
            return
            
        print(f"\n--- {player_id} 的消息历史 ---")
        for message in messages:
            sender = message.source if hasattr(message, 'source') else "未知"
            content = message.content if hasattr(message, 'content') else str(message)
            timestamp = message.timestamp if hasattr(message, 'timestamp') else "未知时间"
            
            print(f"\n[{timestamp}] {sender}: {content}")
            
        print("\n" + "-" * 50)
    
    async def _show_chat_history(self) -> None:
        """
        显示全局聊天历史
        """
        if not self.state.chat_history:
            print("聊天历史为空")
            return
        
        print("\n--- 全局聊天历史 ---")
        for message in self.state.chat_history:
            # 获取消息来源和内容
            source = message.source if hasattr(message, 'source') else "未知"
            content = message.content if hasattr(message, 'content') else str(message)
            timestamp = message.timestamp if hasattr(message, 'timestamp') else "未知时间"
            
            # 根据消息来源确定颜色
            if source == "dm":
                # DM消息使用绿色
                print(f"\n[{timestamp}] {format_dm_message(source, content)}")
            elif source == "human_player":
                # 人类玩家输入使用灰色
                print(f"\n[{timestamp}] {gray_text(f'{source}: {content}')}")
            else:
                # 其他玩家消息使用绿色
                print(f"\n[{timestamp}] {format_player_message(source, content)}")
        
        print("\n" + "-" * 50)
