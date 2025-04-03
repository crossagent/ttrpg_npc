from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging # Import logging

from src.models.message_models import Message, MessageVisibility
# Direct imports instead of TYPE_CHECKING
from src.engine.game_state_manager import GameStateManager
from src.engine.agent_manager import AgentManager
from src.engine.chat_history_manager import ChatHistoryManager


class MessageDispatcher:
    """
    消息分发器类，负责处理游戏中的所有消息分发，确保消息按照可见性正确传递。
    """
    
    def __init__(self, 
                 game_state_manager: GameStateManager, # Remove quotes
                 agent_manager: AgentManager,       # Remove quotes
                 chat_history_manager: ChatHistoryManager): # Remove quotes
        """
        初始化消息分发器
        
        Args:
            game_state_manager: 游戏状态管理器实例
            agent_manager: Agent管理器实例
            chat_history_manager: 聊天记录管理器实例
        """
        self.game_state_manager = game_state_manager
        self.agent_manager = agent_manager
        self.chat_history_manager = chat_history_manager
        self.message_handlers = {}  # 消息处理器字典，键为消息类型
        self.logger = logging.getLogger(__name__) # Add logger
    
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
            
        # --- 移除将消息添加到 game_state.chat_history ---
        # if self.game_state:
        #     self.game_state.chat_history.append(message)
            
        successful_recipients = []
        
        # 如果没有指定接收者，抛出异常
        if not message.recipients:
            raise ValueError("Message recipients not specified. Messages must have explicit recipients.")
    
        # 对每个接收者处理消息
        if self.agent_manager and message.recipients:
            for agent_id in message.recipients:
                agent = self.agent_manager.get_agent(agent_id)
                if not agent:
                    continue
                    
                # 根据Agent视角过滤消息
                filtered_message = agent.filter_message(message)
                
                if filtered_message:
                    # 更新Agent消息记录
                    agent.update_context(filtered_message)
                    successful_recipients.append(agent_id)
        
        # 调用相应的消息处理器
        if message.type in self.message_handlers:
            for handler in self.message_handlers[message.type]:
                try:
                    handler(message)
                except Exception as e:
                    self.logger.exception(f"执行消息处理器 {handler.__name__} 时出错: {e}")

        # --- 添加消息到 ChatHistoryManager ---
        try:
            current_round = self.game_state_manager.get_state().round_number
            self.chat_history_manager.add_message(current_round, message)
        except Exception as e:
            self.logger.exception(f"添加消息到 ChatHistoryManager 时出错: {e}")
            
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
    
    def get_message_history(self, agent_id: Optional[str] = None, limit: int = 50) -> List[Message]:
        """
        获取消息历史
        
        Args:
            agent_id: Agent ID，如果为None则获取所有消息
            limit: 消息数量限制
            
        Returns:
            List[Message]: 消息历史列表
        """
        # --- 从 ChatHistoryManager 获取所有消息 ---
        history = self.chat_history_manager.get_all_messages()
        
        if not history:
            return []
            
        # 如果指定了Agent ID，过滤出该Agent可见的消息 (过滤逻辑保持不变)
        if agent_id and self.agent_manager:
            agent = self.agent_manager.get_agent(agent_id)
            if agent:
                visible_messages = []
                for message in history:
                    if agent.filter_message(message):
                        visible_messages.append(message)
                history = visible_messages
        
        # 返回最近的limit条消息
        return history[-limit:] if limit < len(history) else history[:]
    
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
