from typing import List, Dict, Any, Optional, Union, Sequence
from datetime import datetime
from pydantic import BaseModel
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import ChatMessage
from src.models.message_models import Message, MessageVisibility
# Re-add GameState import for process_new_information type hint
from src.models.game_state_models import GameState
from src.engine.chat_history_manager import ChatHistoryManager # Import ChatHistoryManager
from autogen_core import CancellationToken
from autogen_agentchat.base import Response

class BaseAgent:
    """
    基础Agent类，提供消息处理和记忆管理的基础功能。
    所有具体的Agent类（如PlayerAgent、DMAgent等）都应继承此类。
    """
    
    def __init__(self, agent_id: str, agent_name: str, chat_history_manager: ChatHistoryManager, model_client=None): # Add chat_history_manager
        """
        初始化基础Agent
        
        Args:
            agent_id: Agent的唯一标识符
            agent_name: Agent的名称
            chat_history_manager: ChatHistoryManager 实例 # Add doc
            model_client: 模型客户端
        """
        # 使用组合而非继承
        self.model_client = model_client
        self.chat_history_manager = chat_history_manager # Store chat_history_manager
                
        self.agent_id: str = agent_id
        self.agent_name: str = agent_name  # 保存agent_name以便访问
        self.is_player_controlled = False  # 默认为非玩家控制
        self.entity_knowledge: Dict[str, List[str]] = {
            "locations": [],
            "characters": [],
            "items": []
        }
        
    # 委托方法，将AssistantAgent的方法委托给self.assistant
    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        """委托给assistant的on_messages方法"""
        return await self.assistant.on_messages(messages, cancellation_token)
    
    async def on_messages_stream(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken):
        """委托给assistant的on_messages_stream方法"""
        return self.assistant.on_messages_stream(messages, cancellation_token)
    
    async def run(self, **kwargs):
        """委托给assistant的run方法"""
        return await self.assistant.run(**kwargs)
    
    async def run_stream(self, **kwargs):
        """委托给assistant的run_stream方法"""
        return self.assistant.run_stream(**kwargs)
    
    @property
    def config(self):
        """访问assistant的配置"""
        return self.assistant.config
    
    def update_context(self, message: Message) -> None:
        """
        更新Agent的上下文，处理新接收的消息
        
        Args:
            message: 接收到的消息对象
        """
        # 基类中的空实现，子类可以根据需要重写
        pass
    
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
    
    def get_visible_messages(self, limit: int = 50) -> List[Message]: # Remove game_state parameter
        """
        获取Agent可见的消息历史
        
        Args:
            limit: 消息数量限制
            
        Returns:
            List[Message]: 可见消息列表
        """
        # Get messages from ChatHistoryManager
        all_messages = self.chat_history_manager.get_all_messages()
        visible_messages = []
        
        for message in all_messages:
            if self.filter_message(message):
                visible_messages.append(message)
        
        # 返回最近的limit条消息
        return visible_messages[-limit:] if limit < len(visible_messages) else visible_messages
    
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
        # 基类中的空实现，子类可以根据需要重写
        pass
