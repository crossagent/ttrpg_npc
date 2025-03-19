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
from models.schema import AgentConfig
from src.models.game_state_models import GameState
from src.agents.player_agent import PlayerAgent
from src.config.config_loader import load_llm_settings
from src.communication.message_dispatcher import MessageDispatcher
from src.communication.perspective_info_manager import PerspectiveInfoManager
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
        # 创建默认环境状态
        default_environment = {
            "current_location_id": "起始位置",
            "time": datetime.now(),
            "weather": "晴朗",
            "lighting": "明亮",
            "atmosphere": "平静"
        }
        
        from src.models.game_state_models import EnvironmentStatus
        environment_status = EnvironmentStatus(**default_environment)
        
        self.state = GameState(
            game_id=str(uuid.uuid4()),
            scenario_id="default",
            max_rounds=max_rounds,
            environment=environment_status
        )
        
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
        
        # 初始化通信组件
        self.perspective_info_manager = PerspectiveInfoManager()
        self.message_dispatcher = MessageDispatcher(
            game_state=self.state,
            perspective_info_manager=self.perspective_info_manager
        )
        
        # 初始化代理管理器
        from src.engine.agent_manager import AgentManager
        self.agent_manager = AgentManager(
            perspective_manager=self.perspective_info_manager
        )
        
        self.agents = []
        self.cancellation_token = CancellationToken()
    
    def init_config(self) -> GameState:
        """
        加载并解析全局配置和剧本数据
        
        Returns:
            GameState: 初始化后的游戏状态
        """
        # 在这个简单实现中，我们直接返回已初始化的状态
        return self.state
    
    def initialize_agents(self) -> List[BaseChatAgent]:
        """
        根据配置创建并注册各Agent
        
        Returns:
            List[BaseChatAgent]: 初始化后的Agent列表
        """
        # 创建DM代理 - 暂时使用简单的伪装DM
        dm_agent = AssistantAgent(
            name="dm",
            model_client=self.model_client,
            system_message="你是游戏的主持人，负责推动故事和描述场景。描述要生动有趣，富有想象力。",
        )
        
        # 注册DM代理
        self.agent_manager.register_agent("dm", "dm", dm_agent)
        
        # 创建3个玩家Agent并注册
        player1 = PlayerAgent(
            name="warrior",
            character_profile={
                "name": "高山",
                "personality": "勇敢，直接，喜欢冲锋在前",
                "background": "来自北方山区的战士，精通近战技能",
            },
            model_client=self.model_client
        )
        self.agent_manager.register_agent("warrior", "player", player1)
        
        player2 = PlayerAgent(
            name="mage",
            character_profile={
                "name": "星辰",
                "personality": "聪明，谨慎，思考周全",
                "background": "皇家魔法学院的毕业生，精通元素魔法",
            },
            model_client=self.model_client
        )
        self.agent_manager.register_agent("mage", "player", player2)
        
        player3 = PlayerAgent(
            name="rogue",
            character_profile={
                "name": "影子",
                "personality": "狡猾，机智，喜欢探索",
                "background": "出身于贫民窟，自学成才的地下城探险家",
            },
            model_client=self.model_client
        )
        self.agent_manager.register_agent("rogue", "player", player3)
        
        # 人类玩家代理
        human_agent = AssistantAgent(
            name="human_player",
            model_client=self.model_client, 
            system_message="你是人类玩家的代理人，负责转达玩家的指令。"
        )
        
        self.agents = [dm_agent, player1, player2, player3, human_agent]
        return self.agents
    
    async def start_game(self) -> GameState:
        """
        启动游戏，执行回合流程
        
        Returns:
            GameState: 游戏结束后的最终状态
        """
        # 初始化配置
        self.state = self.init_config()
        
        # 初始化代理
        if not self.agents:
            self.initialize_agents()
            
            # 代理已经在initialize_agents中注册并初始化了上下文
        
        # 创建回合管理器
        from src.engine.round_manager import RoundManager
        round_manager = RoundManager(
            game_state_manager = self.state,
            message_dispatcher = self.message_dispatcher,
            perspective_info_manager = self.perspective_info_manager,
            agent_manager = self.agent_manager,
            scenario_manager = None)
        
        # 保存回合管理器的引用，以便CLI可以访问
        self.round_manager = round_manager
        
        # 执行游戏循环
        while not round_manager.should_terminate(self.state):
            self.state = await round_manager.execute_round(self.state)
            
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
        
        print(green_text(f"游戏结束，共进行了{self.state.round_number}回合。"))
        
        # 清理资源
        await self.cleanup()
        
        return self.state
    
    async def cleanup(self) -> None:
        """
        清理游戏资源
        """
        # 清理消息组件
        self.perspective_info_manager = None
        self.message_dispatcher = None
        self.agent_manager = None
    
    async def _show_player_history(self, player_id: str) -> None:
        """
        显示指定玩家的聊天历史
        
        Args:
            player_id: 玩家ID
        """
        if not self.perspective_info_manager:
            print("视角管理器未初始化")
            return
            
        messages = self.perspective_info_manager.get_visible_messages(player_id)
        
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
