from autogen_agentchat.agents import BaseChatAgent, AssistantAgent  
from autogen_agentchat.messages import TextMessage, ChatMessage
from autogen_core import CancellationToken
from typing import List, Dict, Any, Optional
import asyncio

# 导入我们的数据模型
from src.models.gameSchema import GameState

class RoundManager:
    """
    回合管理器类，负责执行每个回合的流程，协调Agent之间的交互，更新游戏状态，并判断游戏是否应该结束
    """
    
    def __init__(self, agents: List[BaseChatAgent], cancellation_token: CancellationToken):
        """
        初始化回合管理器
        
        Args:
            agents: Agent列表
            cancellation_token: 取消令牌，用于取消异步操作
        """
        self.agents = agents
        self.cancellation_token = cancellation_token
        
        # 获取专门的agent引用，便于后续使用
        self.counting_agent = next((a for a in agents if a.name == "counter"), None)
        self.dm_agent = next((a for a in agents if a.name == "dm"), None)
        self.player_agent = next((a for a in agents if a.name == "player"), None)
    
    async def execute_round(self, state: GameState) -> GameState:
        """
        执行单个回合的所有步骤
        
        Args:
            state: 当前游戏状态
            
        Returns:
            GameState: 更新后的游戏状态
        """
        # 更新回合数
        state.round_number += 1
        print(f"\n--- 回合 {state.round_number} 开始 ---\n")
        
        # DM发言（描述场景）
        dm_message = TextMessage(
            content=f"这是第{state.round_number}回合，请计数者继续数数。",
            source=self.dm_agent.name
        )
        print(f"{self.dm_agent.name}: {dm_message.content}")
        
        # 数数Agent回应
        if state.round_number == 1:
            # 第一回合，从1开始
            state.current_count = 1
        else:
            # 之后的回合，每次+1
            state.current_count += 1
            
        count_message = TextMessage(
            content=str(state.current_count),
            source=self.counting_agent.name
        )
        print(f"{self.counting_agent.name}: {count_message.content}")
        
        # 获取玩家输入
        from src.scripts.cli_runner import get_user_input
        user_input = await get_user_input()
        player_message = TextMessage(
            content=user_input,
            source=self.player_agent.name
        )
        
        # 更新游戏状态上下文
        state = self.update_context(state, [dm_message, count_message, player_message])
        
        return state
    
    def update_context(self, state: GameState, messages: List[TextMessage]) -> GameState:
        """
        分析本回合对话，更新环境与剧本状态
        
        Args:
            state: 当前游戏状态
            messages: 本回合的消息列表
            
        Returns:
            GameState: 更新后的游戏状态
        """
        # 在这个简单实现中，我们只存储消息历史
        if "message_history" not in state.context:
            state.context["message_history"] = []
            
        state.context["message_history"].extend(messages)
        return state
    
    def should_terminate(self, state: GameState) -> bool:
        """
        判断当前回合是否满足终止条件
        
        Args:
            state: 当前游戏状态
            
        Returns:
            bool: 是否应该终止游戏
        """
        # 如果达到最大回合数或游戏已结束，则终止
        return state.round_number >= state.max_rounds or state.is_finished
