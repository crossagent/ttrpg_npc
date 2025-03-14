from typing import List
from autogen_agentchat.messages import TextMessage
from src.models.gameSchema import HistoryMessage, MessageType

def convert_history_to_chat_messages(history_messages: List[HistoryMessage]) -> List[TextMessage]:
    """
    将HistoryMessage列表转换为ChatMessage列表
    
    Args:
        history_messages: HistoryMessage格式的消息列表
        
    Returns:
        List[ChatMessage]: 转换后的ChatMessage列表
    """
    chat_messages = []
    for msg in history_messages:
        # 获取消息内容
        content = msg.message
        if not isinstance(content, str):
            # 如果message不是字符串，尝试获取文本内容
            content = str(content)
            
        # 创建ChatMessage
        chat_message = TextMessage(
            content=content,
            source=msg.character_name
        )
        chat_messages.append(chat_message)
    
    return chat_messages
