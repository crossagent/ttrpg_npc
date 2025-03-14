from autogen_agentchat.agents import BaseChatAgent, AssistantAgent  
from autogen_agentchat.messages import TextMessage, ChatMessage
from autogen_core import CancellationToken
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime

# 导入我们的数据模型
from src.models.gameSchema import GameState, HistoryMessage
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
        previous_messages = self._extract_previous_responses(state)
        
        # DM发言（描述场景）
        dm_text_message = await self._generate_dm_message(state, previous_messages)
        
        # 创建标准的HistoryMessage对象
        dm_message = HistoryMessage(
            timestamp=round_start_time,
            round=state.round_number,
            character_name=self.dm_agent.name if self.dm_agent else "系统",
            message=dm_text_message.content
        )
        
        # 添加到聊天历史
        state.chat_history.append(dm_message)
        
        # 将原始TextMessage添加到临时消息列表中，用于传递给Agent
        temp_message_history = []
        dm_text_message.metadata = {
            "timestamp": round_start_time,
            "round": state.round_number
        }
        temp_message_history.append(dm_text_message)
        
        print(format_dm_message(dm_message.character_name, dm_message.message))
        
        # 收集所有玩家的响应
        player_messages = []
        
        # 首先处理AI玩家
        for player_agent in self.player_agents:
            # 复制当前消息历史供玩家Agent使用
            agent_context = temp_message_history.copy()
            
            # 玩家Agent生成响应，传递当前回合数
            player_response = await player_agent.generate_response(agent_context, self.cancellation_token, state.round_number)
            
            # 获取当前时间作为消息时间戳
            message_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 创建标准的HistoryMessage对象
            player_history_message = HistoryMessage(
                timestamp=message_timestamp,
                round=state.round_number,
                character_name=player_agent.name,
                message=player_response.action
            )
            
            # 添加到聊天历史
            state.chat_history.append(player_history_message)
            
            # 创建只包含行动部分的消息添加到临时消息列表，用于传递给其他Agent
            action_message = TextMessage(
                content=player_response.action,
                source=player_agent.name,
                metadata={
                    "timestamp": message_timestamp,
                    "round": state.round_number
                }
            )
            temp_message_history.append(action_message)
            player_messages.append(player_history_message)
            
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
            
            # 创建标准的HistoryMessage对象
            human_history_message = HistoryMessage(
                timestamp=message_timestamp,
                round=state.round_number,
                character_name=self.human_agent.name,
                message=user_input
            )
            
            # 添加到聊天历史
            state.chat_history.append(human_history_message)
            
            # 创建TextMessage添加到临时消息列表，用于传递给Agent
            human_text_message = TextMessage(
                content=user_input,
                source=self.human_agent.name,
                metadata={
                    "timestamp": message_timestamp,
                    "round": state.round_number
                }
            )
            temp_message_history.append(human_text_message)
            player_messages.append(human_history_message)
        
        # 更新游戏状态上下文
        state = self.update_context(state, [dm_message] + player_messages)
        
        return state
    
    def _extract_previous_responses(self, state: GameState) -> List[ChatMessage]:
        """
        从聊天历史中提取上一轮的玩家响应
        
        Args:
            state: 当前游戏状态
            
        Returns:
            List[ChatMessage]: 上一轮的响应消息列表
        """
        # 如果没有历史记录，返回空列表
        if not state.chat_history:
            return []
        
        # 获取当前回合数
        current_round = state.round_number
        
        # 只返回上一回合的消息
        previous_round = current_round - 1
        if previous_round <= 0:
            return []
        
        # 从chat_history中提取上一回合的消息，并转换为ChatMessage格式
        previous_messages = []
        for msg in state.chat_history:
            if msg.round == previous_round:
                # 创建TextMessage对象
                text_msg = TextMessage(
                    content=msg.message,
                    source=msg.character_name,
                    metadata={
                        "timestamp": msg.timestamp,
                        "round": msg.round
                    }
                )
                previous_messages.append(text_msg)
                
        return previous_messages
    
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
    
    def update_context(self, state: GameState, messages: List[HistoryMessage]) -> GameState:
        """
        分析本回合对话，更新环境与剧本状态
        
        Args:
            state: 当前游戏状态
            messages: 本回合的HistoryMessage列表
            
        Returns:
            GameState: 更新后的游戏状态
        """
        # 消息已经在execute_round方法中添加到state.chat_history中
        # 这里可以进行其他状态更新逻辑
        
        # 为了向后兼容，我们也将消息添加到context中
        if "message_history" not in state.context:
            state.context["message_history"] = []
            
        # 将HistoryMessage对象添加到游戏状态上下文中
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
