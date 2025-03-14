from pydantic import BaseModel, Field
from typing import Dict, List, Any, Callable, Optional

# 游戏状态模型
class GameState(BaseModel):
    """
    游戏状态模型，用于跟踪游戏的当前状态
    """
    round_number: int = 0
    max_rounds: int = 5
    is_finished: bool = False
    current_count: int = 0  # 用于跟踪"数数"的当前值
    context: Dict[str, Any] = Field(default_factory=dict)

# 代理配置模型
class AgentConfig(BaseModel):
    """
    代理配置模型，用于配置各种代理
    """
    name: str
    system_message: str
    tools: List[Callable] = Field(default_factory=list)
    model: str = "gpt-4o"
