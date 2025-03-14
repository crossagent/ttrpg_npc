from pydantic import BaseModel, Field
from typing import Dict, List, Any, Callable, Optional

# 角色状态模型
class CharacterState(BaseModel):
    """角色状态模型，表示角色的当前状态"""
    goal: str = Field(description="角色当前的目标")
    plan: str = Field(description="角色实现目标的计划")
    mood: str = Field(description="角色当前的心情", default="平静")
    health: int = Field(description="角色当前的血量", default=100)

# 玩家响应模型
class PlayerResponse(BaseModel):
    """玩家响应模型，表示玩家在每个回合的观察、状态、思考和行动"""
    observation: str = Field(description="玩家观察到的内容")
    character_state: CharacterState = Field(description="角色当前状态")
    thinking: str = Field(description="玩家的思考过程")
    action: str = Field(description="玩家的行动，这部分会发送到群聊中")

# 历史消息模型
class HistoryMessage(BaseModel):
    """标准的历史消息格式"""
    timestamp: str = Field(description="消息的时间戳")
    round: int = Field(description="消息所属的回合数")
    character_name: str = Field(description="发言角色的名称")
    message: str = Field(description="消息内容")

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
    chat_history: List[HistoryMessage] = Field(default_factory=list)  # 聊天历史记录

# 代理配置模型
class AgentConfig(BaseModel):
    """
    代理配置模型，用于配置各种代理
    """
    name: str
    system_message: str
    tools: List[Callable] = Field(default_factory=list)
    model: str = "gpt-4o"
