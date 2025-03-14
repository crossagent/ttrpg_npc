from typing import List
from autogen_agentchat.messages import ChatMessage
from src.models.gameSchema import HistoryMessage, MessageType

def convert_history_to_chat_messages(history_messages: List[HistoryMessage]) -> List[ChatMessage]:
    """
    将HistoryMessage列表转换为ChatMessage列表
    
    Args:
        history_messages: HistoryMessage格式的消息列表
        
    Returns:
        List[ChatMessage]: 转换后的ChatMessage列表
    """
    chat_messages = []
    for msg in history_messages:
        # 使用枚举确定角色（role）
        if msg.message_type == MessageType.DM:
            role = "assistant"  # DM通常是助手角色
        elif msg.message_type == MessageType.PLAYER:
            role = "user"  # 玩家通常是用户角色
        else:  # MessageType.SYSTEM
            role = "system"  # 系统消息
            
        # 获取消息内容
        content = msg.message
        if not isinstance(content, str):
            # 如果message不是字符串，尝试获取文本内容
            content = str(content)
            
        # 创建ChatMessage
        chat_message = ChatMessage(
            role=role,
            content=content,
            sender=msg.character_name
        )
        chat_messages.append(chat_message)
    
    return chat_messages
