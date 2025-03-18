from pydantic import BaseModel, Field
from typing import Dict, List, Any, Callable, Optional

# 代理配置模型
class AgentConfig(BaseModel):
    """
    代理配置模型，用于配置各种代理
    """
    name: str
    system_message: str
    tools: List[Callable] = Field(default_factory=list)
    model: str = "gpt-4o"
