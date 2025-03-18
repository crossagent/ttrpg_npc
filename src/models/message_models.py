from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from datetime import datetime


class MessageType(str, Enum):
    """消息类型枚举"""
    DM = "dm"
    PLAYER = "player"
    SYSTEM = "system"
    ACTION = "action"
    RESULT = "result"
    DICE = "dice"
    PRIVATE = "private"


class Message(BaseModel):
    """消息模型，表示游戏中的消息"""
    message_id: str = Field(..., description="消息ID")
    type: MessageType = Field(..., description="消息类型")
    sender: str = Field(..., description="发送者")
    content: str = Field(..., description="消息内容")
    timestamp: str = Field(..., description="时间戳")
    visibility: List[str] = Field(..., description="可见性，包含可见的玩家ID列表或'所有人'")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class MessageFilter(BaseModel):
    """消息过滤器模型，用于过滤消息"""
    player_id: str = Field(..., description="玩家ID")
    message_types: Optional[List[MessageType]] = Field(None, description="要过滤的消息类型")
    since_timestamp: Optional[str] = Field(None, description="起始时间戳")
    max_messages: Optional[int] = Field(None, description="最大消息数")
    include_metadata: bool = Field(False, description="是否包含元数据")
