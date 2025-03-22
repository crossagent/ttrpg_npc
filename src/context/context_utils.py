"""
上下文构建工具函数，提供共享的格式化和工具函数。
"""
from typing import List, Dict, Any
from src.models.message_models import Message
from src.models.game_state_models import CharacterInstance

def format_messages(messages: List[Message]) -> str:
    """
    格式化消息列表为文本
    
    Args:
        messages: 消息列表
        
    Returns:
        str: 格式化后的消息文本
    """
    if not messages:
        return "没有新消息"
    
    return "\n".join([f"{msg.source}: {msg.content}" for msg in messages])

def format_character_list(characters: Dict[str, CharacterInstance]) -> str:
    """
    格式化角色列表为文本
    
    Args:
        characters: 角色实例字典，键为角色ID
        
    Returns:
        str: 格式化后的角色列表文本
    """
    if not characters:
        return "未指定角色"
    
    return ", ".join([char.name for char in characters.values()])

def format_location_list(locations: Dict[str, Any]) -> str:
    """
    格式化位置列表为文本
    
    Args:
        locations: 位置字典，键为位置ID
        
    Returns:
        str: 格式化后的位置列表文本
    """
    if not locations:
        return "未指定场景"
    
    return ", ".join(locations.keys())
