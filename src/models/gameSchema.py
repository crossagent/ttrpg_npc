from pydantic import BaseModel, Field
from typing import Dict, List, Any, Callable, Optional
from autogen_agentchat.messages import ChatMessage

# 历史消息模型
class HistoryMessage(BaseModel):
    """标准的历史消息格式"""
    timestamp: str = Field(description="消息的时间戳")
    round: int = Field(description="消息所属的回合数")
    character_name: str = Field(description="发言角色的名称", default="")
    message: Any = Field(description="消息内容，可以是字符串或ChatMessage对象")
    message_type: str = Field(description="消息类型：dm, player, system", default="system")

# 代理配置模型
class AgentConfig(BaseModel):
    """
    代理配置模型，用于配置各种代理
    """
    name: str
    system_message: str
    tools: List[Callable] = Field(default_factory=list)
    model: str = "gpt-4o"
