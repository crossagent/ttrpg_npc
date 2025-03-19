from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from datetime import datetime
from autogen_agentchat.messages import BaseChatMessage

class MessageType(str, Enum):
    """消息类型枚举"""
    DM = "dm"
    PLAYER = "player"
    SYSTEM = "system"
    ACTION = "action"
    RESULT = "result"
    DICE = "dice"
    PRIVATE = "private"

class MessageVisibility(str, Enum):
    """消息可见性枚举"""
    PUBLIC = "public"    # 广播消息，所有人可见
    PRIVATE = "private"  # 私聊消息，仅特定接收者可见

class Message(BaseChatMessage):
    """消息模型，表示游戏中的消息，扩展自ChatMessage"""
    message_id: str = Field(..., description="消息ID")
    content: str = Field(..., description="消息内容") 
    type: MessageType = Field(..., description="消息类型")
    timestamp: str = Field(..., description="时间戳")
    visibility: MessageVisibility = Field(MessageVisibility.PUBLIC, description="消息可见性：广播或私聊")
    recipients: List[str] = Field(..., description="接收者列表，包含可接收此消息的玩家ID列表")
    round_id: int = Field(..., description="回合ID")
    # ChatMessage已经包含metadata字段，我们可以继承使用，不需要重复定义


class MessageFilter(BaseModel):
    """消息过滤器模型，用于过滤消息"""
    player_id: str = Field(..., description="玩家ID")
    message_types: Optional[List[MessageType]] = Field(None, description="要过滤的消息类型")
    since_timestamp: Optional[str] = Field(None, description="起始时间戳")
    max_messages: Optional[int] = Field(None, description="最大消息数")
    include_metadata: bool = Field(False, description="是否包含元数据")
    visibility: Optional[MessageVisibility] = Field(None, description="按可见性过滤")

class MessageStatus(BaseModel):
    """消息状态模型"""
    message_id: str = Field(..., description="消息ID")
    read_status: bool = Field(False, description="是否已读")
    read_timestamp: Optional[datetime] = Field(None, description="读取时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class MessageReadMemory(BaseModel):
    """消息已读记录模型"""
    player_id: str = Field(..., description="玩家ID")
    history_messages: Dict[str, MessageStatus] = Field(default_factory=dict, description="可见的消息状态，键为消息ID")