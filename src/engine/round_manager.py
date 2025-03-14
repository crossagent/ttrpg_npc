from autogen_agentchat.agents import BaseChatAgent, AssistantAgent  
from autogen_agentchat.messages import TextMessage, ChatMessage
from autogen_core import CancellationToken
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime

# 导入我们的数据模型
from src.models.gameSchema import GameState
from src.agents.player_agent import PlayerAgent

# 导入颜色工具
from src.config.color_utils import (
    format_dm_message, format_player_message, format_observation,
    format_state, format_thinking, print_colored,
    Color
)

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
        self.dm_agent = next((a for a in agents if a.name == "dm"), None)
        
        # 获取所有玩家Agent
        self.player_agents = [a for a in agents if isinstance(a, PlayerAgent)]
        
        # 获取人类玩家Agent
        self.human_agent = next((a for a in agents if a.name == "human_player"), None)
        
        # 初始化消息历史
        self.message_history = []
    
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
        
        # 记录回合开始时间
        round_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 从历史中提取上一轮的玩家响应
        previous_messages = self._extract_previous_responses()
        
        # DM发言（描述场景）
        dm_message = await self._generate_dm_message(state, previous_messages)
        # 添加时间戳
        dm_message.metadata = {"timestamp": round_start_time}
        self.message_history.append(dm_message)
        print(format_dm_message(self.dm_agent.name, dm_message.content))
        
        # 收集所有玩家的响应
        player_messages = []
        
        # 首先处理AI玩家
        for player_agent in self.player_agents:
            # 复制当前消息历史供玩家Agent使用
            agent_context = self.message_history.copy()
            
            # 玩家Agent生成响应
            player_response = await player_agent.generate_response(agent_context, self.cancellation_token)
            
            # 获取当前时间作为消息时间戳
            message_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 创建只包含行动部分的消息添加到群聊历史
            action_message = TextMessage(
                content=player_response.action,
                source=player_agent.name,
                metadata={"timestamp": message_timestamp}
            )
            self.message_history.append(action_message)
            player_messages.append(action_message)
            
            # 使用绿色打印玩家发言
            print(format_player_message(player_agent.name, player_response.action))
            
            # 打印内部状态（仅用于调试）- 使用黄色
            print(f"--- {player_agent.name}的内部状态 ---")
            print(format_observation(player_response.observation))
            print(format_state(
                player_response.character_state.goal,
                player_response.character_state.plan,
                player_response.character_state.mood,
                player_response.character_state.health
            ))
            print(format_thinking(player_response.thinking))
            print("-------------------------")
        
        # 如果有人类玩家，获取人类输入
        if self.human_agent:
            from src.scripts.cli_runner import get_user_input
            user_input = await get_user_input()
            
            # 获取当前时间作为消息时间戳
            message_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            human_message = TextMessage(
                content=user_input,
                source=self.human_agent.name,
                metadata={"timestamp": message_timestamp}
            )
            self.message_history.append(human_message)
            player_messages.append(human_message)
        
        # 更新游戏状态上下文
        state = self.update_context(state, [dm_message] + player_messages)
        
        return state
    
    def _extract_previous_responses(self) -> List[ChatMessage]:
        """
        从聊天历史中提取上一轮的玩家响应
        
        Returns:
            List[ChatMessage]: 上一轮的响应消息列表
        """
        # 在这个简单实现中，我们直接返回所有历史消息
        return self.message_history
    
    async def _generate_dm_message(self, state: GameState, previous_messages: List[ChatMessage]) -> TextMessage:
        """
        生成DM的场景描述消息
        
        Args:
            state: 当前游戏状态
            previous_messages: 上一轮的消息历史
            
        Returns:
            TextMessage: DM的场景描述消息
        """
        if not self.dm_agent:
            # 如果没有DM Agent，使用默认消息
            return TextMessage(
                content=f"这是第{state.round_number}回合，游戏继续进行中...",
                source="系统"
            )
        
        # 暂时使用伪装的DM消息 - 未来替换为真正的DMAgent
        if state.round_number == 1:
            dm_content = "你们站在一座古老城堡的入口处。高耸的石墙上爬满了藤蔓，铁门已经生锈，但仍然紧闭着。周围是茂密的森林，有微弱的光从城堡的窗户透出。你们听到城堡内传来奇怪的声音。"
        else:
            dm_content = f"第{state.round_number}回合：随着你们的探索，城堡内的气氛变得更加紧张。走廊上的火把忽明忽暗，墙上的画像似乎在注视着你们。远处传来金属碰撞的声音和低沉的咆哮。"
        
        return TextMessage(
            content=dm_content,
            source=self.dm_agent.name
        )
    
    def update_context(self, state: GameState, messages: List[TextMessage]) -> GameState:
        """
        分析本回合对话，更新环境与剧本状态
        
        Args:
            state: 当前游戏状态
            messages: 本回合的消息列表
            
        Returns:
            GameState: 更新后的游戏状态
        """
        # 在这个实现中，我们只存储消息历史
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
        
    def get_player_history(self, player_name: str) -> List[Dict[str, Any]]:
        """
        获取指定玩家的历史记录
        
        Args:
            player_name: 玩家名称
            
        Returns:
            List[Dict[str, Any]]: 玩家历史记录列表
        """
        player_agent = next((a for a in self.player_agents if a.name == player_name), None)
        if player_agent:
            return player_agent.get_history()
        return []
