from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from src.models.message_models import Message, MessageVisibility


class MessageDispatcher:
    """
    消息分发器类，负责处理游戏中的所有消息分发，确保消息按照可见性正确传递。
    """
    
    def __init__(self, game_state=None, perspective_info_manager=None):
        """
        初始化消息分发器
        
        Args:
            game_state: 游戏状态，用于存储全局消息历史
            personal_context_manager: 个人视角信息管理器
        """
        self.game_state = game_state
        self.perspective_info_manager = perspective_info_manager
        self.message_handlers = {}  # 消息处理器字典，键为消息类型
    
    def broadcast_message(self, message: Message) -> List[str]:
        """
        广播消息给相关玩家
        
        Args:
            message: 消息对象
            
        Returns:
            List[str]: 成功接收消息的玩家ID列表
        """
        # 确保消息有唯一ID
        if not message.message_id:
            message.message_id = self.create_message_id()
            
        # 将消息添加到全局历史
        if self.game_state:
            self.game_state.chat_history.append(message)
            
        successful_recipients = []
        
        # 如果没有指定接收者且存在个人视角管理器，获取所有玩家ID
        if not message.recipients and self.perspective_info_manager:
            message.recipients = self.perspective_info_manager.get_all_player_ids()
            
        # 对每个接收者处理消息
        if self.perspective_info_manager and message.recipients:
            for player_id in message.recipients:
                # 根据玩家视角过滤消息
                filtered_message = self.perspective_info_manager.filter_message(message, player_id)
                
                if filtered_message:
                    # 更新玩家消息记录
                    self.perspective_info_manager.update_player_context(player_id, filtered_message)
                    successful_recipients.append(player_id)
        
        # 调用相应的消息处理器
        if message.type in self.message_handlers:
            for handler in self.message_handlers[message.type]:
                handler(message)
                    
        return successful_recipients
    
    def send_private_message(self, message: Message, recipient_id: str) -> bool:
        """
        发送私密消息
        
        Args:
            message: 消息对象
            recipient_id: 接收者ID
            
        Returns:
            bool: 是否发送成功
        """
        # 设置消息的可见性为私密
        message.visibility = MessageVisibility.PRIVATE
        message.recipients = [recipient_id]
        
        # 使用广播消息方法发送
        successful_recipients = self.broadcast_message(message)
        
        # 检查是否成功发送给指定接收者
        return recipient_id in successful_recipients
    
    def create_message_id(self) -> str:
        """
        创建唯一消息ID
        
        Returns:
            str: 唯一消息ID
        """
        return str(uuid.uuid4())
    
    def get_message_history(self, player_id: Optional[str] = None, limit: int = 50) -> List[Message]:
        """
        获取消息历史
        
        Args:
            player_id: 玩家ID，如果为None则获取所有消息
            limit: 消息数量限制
            
        Returns:
            List[Message]: 消息历史列表
        """
        if player_id and self.perspective_info_manager:
            return self.perspective_info_manager.get_visible_messages(player_id, limit)
        elif self.game_state and self.game_state.chat_history:
            # 返回全局消息历史
            history = self.game_state.chat_history
            return history[-limit:] if limit < len(history) else history[:]
        return []
    
    def register_message_handler(self, handler_function, message_types: List[str] = None) -> None:
        """
        注册消息处理器
        
        Args:
            handler_function: 处理器函数
            message_types: 要处理的消息类型列表
        """
        if not message_types:
            # 如果未指定消息类型，则处理所有类型
            message_types = ["*"]
            
        for message_type in message_types:
            if message_type not in self.message_handlers:
                self.message_handlers[message_type] = []
            self.message_handlers[message_type].append(handler_function)
