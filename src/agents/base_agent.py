from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel
from autogen_agentchat.agents import AssistantAgent
from src.models.message_models import Message, MessageStatus, MessageReadMemory, MessageVisibility
from src.models.game_state_models import GameState


class BaseAgent (AssistantAgent):
    """
    基础Agent类，提供消息处理和记忆管理的基础功能。
    所有具体的Agent类（如PlayerAgent、DMAgent等）都应继承此类。
    """
    
    def __init__(self, agent_id: str, agent_name: str, model_client=None):
        """
        初始化基础Agent
        
        Args:
            agent_id: Agent的唯一标识符
            name: Agent的名称
        """
        self.agent_id: str = agent_id
        self.is_player_controlled = False  # 默认为非玩家控制
        self.message_memory: MessageReadMemory = MessageReadMemory(
            player_id=agent_id,
            history_messages={}
        )
        self.entity_knowledge: Dict[str, List[str]] = {
            "locations": [],
            "characters": [],
            "items": []
        }

        # 如果提供了model_client，初始化AssistantAgent
        if model_client:
            AssistantAgent.__init__(self, name=agent_name, model_client=model_client)
    
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
    
    def filter_message(self, message: Message) -> Optional[Message]:
        """
        过滤消息可见性，决定Agent是否可以看到该消息
        
        Args:
            message: 原始消息
            
        Returns:
            Optional[Message]: 过滤后的消息，如果不可见则为None
        """
        # 检查可见性
        if message.visibility == MessageVisibility.PRIVATE and self.agent_id not in message.recipients:
            return None
            
        # 这里可以添加更复杂的过滤逻辑，根据游戏规则和角色知识范围
        # 例如基于entity_knowledge过滤消息内容
        
        return message
    
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
            if (message.message_id in self.message_memory.history_messages and 
                not self.message_memory.history_messages[message.message_id].read_status and
                self.filter_message(message)):  # 确保消息对自己可见
                unread_messages.append(message)
                
        # 标记为已读
        for message in unread_messages:
            self.mark_message_as_read(message.message_id)
            
        return unread_messages
    
    def get_visible_messages(self, game_state: GameState, limit: int = 50) -> List[Message]:
        """
        获取Agent可见的消息历史
        
        Args:
            game_state: 游戏状态，包含消息历史
            limit: 消息数量限制
            
        Returns:
            List[Message]: 可见消息列表
        """
        all_messages = game_state.chat_history
        visible_messages = []
        
        for message in all_messages:
            if self.filter_message(message):
                visible_messages.append(message)
        
        # 返回最近的limit条消息
        return visible_messages[-limit:] if limit < len(visible_messages) else visible_messages
    
    def mark_message_as_read(self, message_id: str) -> bool:
        """
        将消息标记为已读
        
        Args:
            message_id: 消息ID
            
        Returns:
            bool: 是否成功标记
        """
        if message_id not in self.message_memory.history_messages:
            return False
            
        # 更新消息状态
        message_status = self.message_memory.history_messages[message_id]
        message_status.read_status = True
        message_status.read_timestamp = datetime.now()
        
        return True
    
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
    
    def update_known_entities(self, entity_type: str, entities: List[str]) -> None:
        """
        更新Agent已知实体
        
        Args:
            entity_type: 实体类型（locations, characters, items）
            entities: 实体列表
        """
        # 确保实体类型存在
        if entity_type not in self.entity_knowledge:
            self.entity_knowledge[entity_type] = []
            
        # 添加新的实体（去重）
        current_entities = set(self.entity_knowledge[entity_type])
        current_entities.update(entities)
        self.entity_knowledge[entity_type] = list(current_entities)
    
    def process_new_information(self, game_state: GameState) -> None:
        """
        处理新信息，由子类实现具体逻辑
        
        Args:
            game_state: 游戏状态，包含消息历史
        """
        # 获取未读消息
        unread_messages = self.get_unread_messages(game_state)
        
        # 基类中只提供基本处理，具体逻辑由子类实现
        for message in unread_messages:
            # 可以在这里添加通用的处理逻辑
            pass
