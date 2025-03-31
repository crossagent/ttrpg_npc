from autogen_agentchat.messages import TextMessage, ChatMessage
from autogen_core import CancellationToken
from typing import List, Dict, Any, Optional, Union
import json
from datetime import datetime
from src.models.scenario_models import ScenarioCharacterInfo
from src.models.game_state_models import GameState, MessageReadMemory
from src.models.action_models import PlayerAction
from src.agents.base_agent import BaseAgent
from src.models.action_models import ActionType
from src.models.llm_validation import create_validator_for, LLMOutputError
from src.models.context_models import PlayerActionLLMOutput
from src.models.message_models import Message, MessageStatus
from src.context.player_context_builder import (
    build_decision_system_prompt,
    build_decision_user_prompt
)
import uuid

class PlayerAgent(BaseAgent):
    """
    玩家Agent类，负责生成玩家的观察、状态、思考和行动
    """
    
    def __init__(self, agent_id: str, agent_name: str, character_id:str, model_client=None):
        """
        初始化玩家Agent
        
        Args:
            agent_id: Agent唯一标识符
            agent_name: Agent名称
            character_id: 角色ID
            model_client: 模型客户端
        """
        # 初始化BaseAgent
        super().__init__(agent_id=agent_id, agent_name=agent_name, model_client=model_client)

        self.character_id = character_id
        
        # 初始化消息记忆
        self.message_memory: MessageReadMemory = MessageReadMemory(
            player_id=agent_id,
            history_messages={}
        )
    
    def update_context(self, message: Message) -> None:
        """
        更新Agent的上下文，处理新接收的消息
        
        Args:
            message: 接收到的消息对象
        """
        # 创建消息状态
        message_status = MessageStatus(
            message_id=message.message_id,
            read_status=False
        )
        
        # 更新消息记录
        self.message_memory.history_messages[message.message_id] = message_status
    
    def get_unread_messages(self, game_state: GameState) -> List[Message]:
        """
        获取所有未读消息
        
        Args:
            game_state: 游戏状态，包含消息历史
            
        Returns:
            List[Message]: 未读消息列表
        """
        # 直接从game_state获取消息历史
        all_messages = game_state.chat_history
        
        # 过滤出自己可见且未读的消息
        unread_messages = []
        for message in all_messages:
            # Check if message exists in memory AND is marked as unread AND is visible
            if (message.message_id in self.message_memory.history_messages and
                not self.message_memory.history_messages[message.message_id].read_status and
                self.filter_message(message)): # filter_message is inherited from BaseAgent
                unread_messages.append(message)
                
        # 标记为已读 (Important: Mark as read *after* identifying all unread messages for this turn)
        for message in unread_messages:
            self.mark_message_as_read(message.message_id)
            
        return unread_messages
    
    def mark_message_as_read(self, message_id: str) -> bool:
        """
        将消息标记为已读
        
        Args:
            message_id: 消息ID
            
        Returns:
            bool: 是否成功标记
        """
        if message_id not in self.message_memory.history_messages:
             # If the message isn't even in memory, we can't mark it.
             # This might happen if update_context wasn't called for this message.
             # Consider logging a warning here.
             print(f"Warning: Attempted to mark message '{message_id}' as read, but it was not found in memory for agent {self.agent_id}.")
             return False
            
        # 更新消息状态
        message_status = self.message_memory.history_messages[message_id]
        if not message_status.read_status: # Only update timestamp if it wasn't already read
            message_status.read_status = True
            message_status.read_timestamp = datetime.now()
            return True
        return False # Return False if it was already marked as read
    
    def get_unread_messages_count(self) -> int:
        """
        获取未读消息数量
        
        Returns:
            int: 未读消息数量
        """
        # 统计未读消息
        unread_count = 0
        for message_status in self.message_memory.history_messages.values():
            if not message_status.read_status:
                unread_count += 1
                
        return unread_count

    
    async def player_decide_action(self, game_state: GameState, charaInfo: ScenarioCharacterInfo) -> PlayerAction:
        """
        玩家决策行动
        
        Args:
            game_state: 游戏状态，包含消息历史
            charaInfo: 当前玩家角色的剧本信息
            
        Returns:
            PlayerAction: 玩家行动
        """
        # 获取未读消息 (This also marks them as read in memory)
        unread_messages = self.get_unread_messages(game_state)
        
        # 生成系统消息
        system_message = build_decision_system_prompt(charaInfo)
        
        # 直接创建新的AssistantAgent实例
        from autogen_agentchat.agents import AssistantAgent
        assistant = AssistantAgent(
            name=self.agent_name, # Use unique name per call
            model_client=self.model_client,
            system_message=system_message
        )
        
        # 构建用户消息
        user_message_content = build_decision_user_prompt(game_state, unread_messages, self.character_id)
        user_message = TextMessage(
            content=user_message_content,
            source="DM" # Source is DM providing context
        )
        
        response_content = "" # Initialize response content
        try:
            # 使用新创建的assistant的on_messages方法
            response = await assistant.on_messages([user_message], CancellationToken())
            if response and response.chat_message and response.chat_message.content:
                response_content = response.chat_message.content
                
                # 使用验证器验证LLM输出
                try:
                    # 创建验证器
                    validator = create_validator_for(PlayerActionLLMOutput)
                    
                    # 验证响应
                    validated_data: PlayerActionLLMOutput = validator.validate_response(response_content)
                    
                    # 创建行动对象
                    return PlayerAction(
                        character_id=self.character_id,
                        interal_thoughts=validated_data.internal_thoughts, # Corrected attribute name
                        action_type=validated_data.action_type,
                        content=validated_data.action,
                        target=validated_data.target,
                        timestamp=datetime.now().isoformat()
                    )
                except LLMOutputError as e:
                    # 处理验证错误，使用默认值
                    print(f"LLM output validation error for PlayerAgent {self.agent_id}: {e.message}. Raw output: {e.raw_output[:200]}...") # Log raw output snippet
                    # 尝试从原始响应中提取有用信息
                    import re
                    # 尝试提取action
                    action_match = re.search(r'"action"\s*:\s*"([^"]+)"', e.raw_output, re.IGNORECASE)
                    action_content = action_match.group(1) if action_match else "未能决定行动 (解析错误)"
                    
                    # 创建默认行动对象
                    return PlayerAction(
                        character_id=self.character_id,
                        internal_thoughts="未能生成内心活动 (验证失败)", # Corrected attribute name
                        action_type=ActionType.TALK, # Default to TALK on error
                        content=action_content,
                        target="all", # Default target
                        timestamp=datetime.now().isoformat()
                    )
            else:
                 print(f"Warning: PlayerAgent {self.agent_id} received no valid response from LLM assistant.")
                 # Fallback action if LLM fails completely
                 return PlayerAction(
                        character_id=self.character_id,
                        internal_thoughts="未能生成内心活动 (LLM无响应)",
                        action_type=ActionType.ACTION, # Default to ACTION (e.g., wait/observe)
                        content="...", # Indicate waiting or observing
                        target="environment",
                        timestamp=datetime.now().isoformat()
                    )

                    
        except Exception as e:
            # Log the full error and the response content if available
            import traceback
            print(f"Error during PlayerAgent {self.agent_id} action decision: {str(e)}")
            print(f"LLM Response Content (if any): {response_content[:200]}...")
            traceback.print_exc()
            # Raise a more specific exception or return a default action
            raise Exception(f"Assistant生成行动失败 for agent {self.agent_id}: {str(e)}")
