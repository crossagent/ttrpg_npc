from typing import List, Dict, Any, Optional
from datetime import datetime
import copy

from src.models.message_models import Message, MessageStatus, MessageReadMemory, MessageVisibility


class PerspectiveInfoManager:
    """
    个人视角信息管理器类，负责管理每个玩家可见的信息，维护个人信息上下文。
    """
    
    def __init__(self):
        """
        初始化个人视角信息管理器
        """
        self.player_message_memories = {}  # player_id -> MessageReadMemory
        self.stored_messages = {}  # message_id -> Message
        self.entity_knowledge = {}  # player_id -> {entity_type -> [entities]}
    
    def update_player_context(self, player_id: str, message: Message) -> None:
        """
        更新玩家上下文
        
        Args:
            player_id: 玩家ID
            message: 消息对象
        """
        if player_id not in self.player_message_memories:
            self.initialize_player_memory(player_id, "未知角色")
            
        # 存储消息本身
        self.stored_messages[message.message_id] = copy.deepcopy(message)
        
        # 创建消息状态
        message_status = MessageStatus(
            message_id=message.message_id,
            read_status=False
        )
        
        # 更新玩家消息记录
        self.player_message_memories[player_id].history_messages[message.message_id] = message_status
    
    def get_player_memory(self, player_id: str) -> MessageReadMemory:
        """
        获取玩家当前上下文
        
        Args:
            player_id: 玩家ID
            
        Returns:
            MessageReadMemory: 玩家消息记录
        """
        if player_id not in self.player_message_memories:
            return self.initialize_player_memory(player_id, "未知角色")
            
        return self.player_message_memories[player_id]
    
    def filter_message(self, message: Message, player_id: str) -> Optional[Message]:
        """
        过滤消息可见性
        
        Args:
            message: 原始消息
            player_id: 玩家ID
            
        Returns:
            Optional[Message]: 过滤后的消息，如果不可见则为None
        """
        # 检查可见性
        if message.visibility == MessageVisibility.PRIVATE and player_id not in message.recipients:
            return None
            
        # 这里可以添加更复杂的过滤逻辑，根据游戏规则和角色知识范围
        # 例如基于entity_knowledge过滤消息内容
        
        # 返回消息的副本，避免修改原始消息
        return copy.deepcopy(message)
    
    def initialize_player_memory(self, player_id: str, character_name: str) -> MessageReadMemory:
        """
        初始化玩家上下文
        
        Args:
            player_id: 玩家ID
            character_name: 角色名称
            
        Returns:
            MessageReadMemory: 初始化的玩家消息记录
        """
        if player_id not in self.player_message_memories:
            self.player_message_memories[player_id] = MessageReadMemory(
                player_id=player_id,
                history_messages={}
            )
            
            # 初始化玩家的已知实体
            self.entity_knowledge[player_id] = {
                "locations": [],
                "characters": [character_name],  # 初始至少知道自己
                "items": []
            }
            
        return self.player_message_memories[player_id]
    
    def update_known_entities(self, player_id: str, entity_type: str, entities: List[str]) -> None:
        """
        更新玩家已知实体
        
        Args:
            player_id: 玩家ID
            entity_type: 实体类型（locations, characters, items）
            entities: 实体列表
        """
        if player_id not in self.entity_knowledge:
            self.entity_knowledge[player_id] = {
                "locations": [],
                "characters": [],
                "items": []
            }
            
        # 确保实体类型存在
        if entity_type not in self.entity_knowledge[player_id]:
            self.entity_knowledge[player_id][entity_type] = []
            
        # 添加新的实体（去重）
        current_entities = set(self.entity_knowledge[player_id][entity_type])
        current_entities.update(entities)
        self.entity_knowledge[player_id][entity_type] = list(current_entities)
    
    def get_visible_messages(self, player_id: str, limit: int = 50) -> List[Message]:
        """
        获取玩家可见的消息历史
        
        Args:
            player_id: 玩家ID
            limit: 消息数量限制
            
        Returns:
            List[Message]: 可见消息列表
        """
        if player_id not in self.player_message_memories:
            return []
            
        # 获取该玩家的消息记录
        memory = self.player_message_memories[player_id]
        
        visible_messages = []
        for message_id in memory.history_messages:
            if message_id in self.stored_messages:
                visible_messages.append(self.stored_messages[message_id])
                
        # 按时间戳排序
        visible_messages.sort(key=lambda m: m.timestamp)
        
        # 返回最近的limit条
        return visible_messages[-limit:] if limit < len(visible_messages) else visible_messages
    
    def get_all_player_ids(self) -> List[str]:
        """
        获取所有玩家ID
        
        Returns:
            List[str]: 所有玩家ID列表
        """
        return list(self.player_message_memories.keys())
    
    def mark_message_as_read(self, player_id: str, message_id: str) -> bool:
        """
        将消息标记为已读
        
        Args:
            player_id: 玩家ID
            message_id: 消息ID
            
        Returns:
            bool: 是否成功标记
        """
        if (player_id not in self.player_message_memories or 
            message_id not in self.player_message_memories[player_id].history_messages):
            return False
            
        # 更新消息状态
        message_status = self.player_message_memories[player_id].history_messages[message_id]
        message_status.read_status = True
        message_status.read_timestamp = datetime.now()
        
        return True
    
    def get_unread_messages_count(self, player_id: str) -> int:
        """
        获取玩家未读消息数量
        
        Args:
            player_id: 玩家ID
            
        Returns:
            int: 未读消息数量
        """
        if player_id not in self.player_message_memories:
            return 0
            
        # 统计未读消息
        unread_count = 0
        for message_status in self.player_message_memories[player_id].history_messages.values():
            if not message_status.read_status:
                unread_count += 1
                
        return unread_count
