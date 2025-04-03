from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from datetime import datetime
from autogen_agentchat.messages import BaseChatMessage

# --- 新增 SenderRole 枚举 ---
class SenderRole(str, Enum):
    """消息发送者角色枚举"""
    PLAYER_CHARACTER = "player_character" # 玩家或陪玩角色代理
    NARRATOR = "narrator"             # 叙事代理 (DM)
    REFEREE = "referee"               # 裁判代理
    SYSTEM = "system"                 # 游戏引擎或其他系统组件

# --- 重定义 MessageType 枚举 (仅关注内容性质) ---
class MessageType(str, Enum):
    """消息类型枚举 (仅关注内容性质)"""
    NARRATION = "narration"                 # DM 的叙述性文本
    DIALOGUE = "dialogue"                   # 角色的对话
    ACTION_DECLARATION = "action_declaration" # 角色宣告行动
    WAIT_NOTIFICATION = "wait_notification"   # 角色宣告等待/观察
    ACTION_RESULT_NARRATIVE = "action_result_narrative" # 行动结果的叙述描述 (来自 DM)
    ACTION_RESULT_SYSTEM = "action_result_system"     # 行动结果的系统摘要 (来自裁判)
    EVENT_NOTIFICATION = "event_notification"       # 事件触发的系统通知 (来自裁判/系统)
    DICE_ROLL = "dice_roll"                   # 掷骰信息 (如果需要)
    SYSTEM_INFO = "system_info"               # 其他系统消息
    # 移除了 DM, PLAYER, SYSTEM, ACTION, RESULT, SYSTEM_ACTION_RESULT, SYSTEM_EVENT, PRIVATE

class MessageVisibility(str, Enum):
    """消息可见性枚举"""
    PUBLIC = "public"    # 广播消息，所有人可见
    PRIVATE = "private"  # 私聊消息，仅特定接收者可见

class Message(BaseChatMessage):
    """消息模型，表示游戏中的消息，扩展自ChatMessage"""
    message_id: str = Field(..., description="消息ID")
    content: str = Field(..., description="消息内容")
    sender_role: SenderRole = Field(..., description="消息发送者角色") # --- 新增 sender_role 字段 ---
    type: MessageType = Field(..., description="消息类型 (内容性质)") # --- 修改 type 字段描述 ---
    timestamp: str = Field(..., description="时间戳")
    visibility: MessageVisibility = Field(MessageVisibility.PUBLIC, description="消息可见性：广播或私聊")
    recipients: List[str] = Field(..., description="接收者列表，包含可接收此消息的玩家ID列表")
    round_id: int = Field(..., description="回合ID")
    source_id: Optional[str] = Field(None, description="消息来源的唯一ID (例如, agent_id), 如果适用") # 新增 source_id
    # message_subtype 字段已移除
    # ChatMessage已经包含metadata字段，我们可以继承使用，不需要重复定义


class MessageFilter(BaseModel):
    """消息过滤器模型，用于过滤消息"""
    player_id: str = Field(..., description="玩家ID")
    message_types: Optional[List[MessageType]] = Field(None, description="要过滤的消息类型")
    since_timestamp: Optional[str] = Field(None, description="起始时间戳")
    max_messages: Optional[int] = Field(None, description="最大消息数")
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
