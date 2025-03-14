from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage, ChatMessage
from typing import Dict, List, Any, Callable, Optional
import asyncio

# 导入我们的数据模型
from src.models.gameSchema import GameState, AgentConfig
from src.config.settings import DEFAULT_MAX_ROUNDS, DEFAULT_MODEL

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
        self.state = GameState(max_rounds=max_rounds)
        self.model_client = OpenAIChatCompletionClient(model=DEFAULT_MODEL)
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
    
    def initialize_agents(self) -> List[AssistantAgent]:
        """
        根据配置创建并注册各Agent
        
        Returns:
            List[AssistantAgent]: 初始化后的Agent列表
        """
        # 创建一个只会数数的Agent
        counting_agent = AssistantAgent(
            name="counter",
            model_client=self.model_client,
            system_message="你只会数数，从1开始，每次回应都只输出下一个数字，不解释也不做其他回应。",
        )
        
        # 创建一个DM代理（可以扩展为更复杂的角色）
        dm_agent = AssistantAgent(
            name="dm",
            model_client=self.model_client,
            system_message="你是游戏的主持人，负责推动故事和描述场景。",
        )
        
        # 玩家代理（用于接收用户输入）
        player_agent = AssistantAgent(
            name="player",
            model_client=self.model_client, 
            system_message="你是玩家角色的代理人，负责转达玩家的指令。"
        )
        
        self.agents = [counting_agent, dm_agent, player_agent]
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
        
        # 创建回合管理器
        from src.engine.round_manager import RoundManager
        round_manager = RoundManager(self.agents, self.cancellation_token)
        
        # 执行游戏循环
        while not round_manager.should_terminate(self.state):
            self.state = await round_manager.execute_round(self.state)
            
        print(f"游戏结束，共进行了{self.state.round_number}回合。")
        return self.state
