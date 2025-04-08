from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from src.models.action_models import ActionType
from src.models.message_models import Message
from src.models.action_models import InternalThoughts, ActionOption # Import ActionOption

class PlayerActionLLMOutput(BaseModel):
    """LLM输出的玩家行动模型"""
    observation: str = Field(..., description="观察到的环境和其他角色的信息")
    internal_thoughts: InternalThoughts = Field(..., description="内心活动")
    action: str = Field(..., description="实际采取的行动") # Note: This field likely represents the main content/dialogue
    action_type: ActionType = Field(default=ActionType.TALK, description="行动类型：对话、行动或无视")
    target: Union[str, List[str]] = Field(default="all", description="行动目标")
    minor_action: Optional[str] = Field(None, description="伴随对话的微小动作 (例如: 叹气, 撩头发), 主要用于 TALK 类型")

class PlayerActionSystemContext(BaseModel):
    """玩家行动系统上下文模型，表示玩家行动系统的上下文信息"""
    character_name: str = Field(..., description="角色名称")
    character_personality: str = Field(..., description="角色性格")
    character_background: str = Field(..., description="角色背景故事")

class PlayerActionUserContext(BaseModel):
    """玩家行动用户上下文模型，表示玩家行动用户的上下文信息"""
    recent_messages: List[Message] = Field(default_factory=list, description="最近的消息")
    recent_internal_thoughts: List[InternalThoughts] = Field(default_factory=list, description="最近的内心活动")
    current_location: str = Field(..., description="当前位置")
    current_health: int = Field(..., description="当前血量")
    
class PlayerContextText(BaseModel):
    """玩家上下文文本模型，表示发送给LLM的玩家信息文本"""
    character_description: str = Field(..., description="角色描述文本")
    goal_description: str = Field(..., description="角色目标描述")
    environment_description: str = Field(..., description="环境描述文本")
    knowledge_description: str = Field(..., description="已知信息描述")
    status_description: str = Field(..., description="当前状态描述")
    recent_events_description: str = Field(..., description="最近事件描述")
    relationships_description: str = Field(..., description="关系描述文本")
    items_description: str = Field("", description="物品描述文本")

class DMNarrativeSystemContext(BaseModel):
    """DM叙述系统上下文模型，表示DM叙述系统的上下文信息"""
    story_background: str = Field(..., description="故事背景")
    narrative_style: str = Field(..., description="叙事风格")


class DMNarrativeUserContext(BaseModel):
    """DM叙述用户上下文模型，表示DM叙述用户的上下文信息"""
    recent_messages: str = Field(default_factory=list, description="最近的消息")
    stage_decribertion: str = Field(..., description="当前阶段描述")
    characters_description: str = Field(..., description="角色描述")
    environment_description: str = Field(..., description="环境描述")
    location_description: str = Field(..., description="位置描述")

class StateChanges(BaseModel):
    """状态变化模型，表示从DM叙述中提取的状态变化"""
    player_changes: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="玩家状态变化")
    environment_changes: Dict[str, Any] = Field(default_factory=dict, description="环境状态变化")
    item_changes: Dict[str, List[str]] = Field(default_factory=dict, description="物品变化")
    relationship_changes: Dict[str, Dict[str, int]] = Field(default_factory=dict, description="关系变化")


class Inconsistency(BaseModel):
    """一致性检查结果模型，表示状态一致性检查的结果"""
    type: str = Field(..., description="不一致类型")
    description: str = Field(..., description="不一致描述")
    affected_entities: List[str] = Field(default_factory=list, description="受影响的实体")
    severity: str = Field("中", description="严重程度：低、中、高")


class StateUpdateRequest(BaseModel):
    """状态更新请求模型，用于请求更新游戏状态"""
    dm_narrative: str = Field(..., description="DM叙述")
    action_context: Dict[str, Any] = Field(default_factory=dict, description="行动上下文")


class ActionResolutionLLMOutput(BaseModel):
    """LLM输出的行动解析结果模型"""
    success: bool = Field(..., description="行动是否成功")
    narrative: str = Field(..., description="行动结果的详细描述")
    state_changes: Dict[str, Any] = Field(default_factory=dict, description="行动导致的游戏状态变化")


# 新增：用于验证 LLM 返回的行动选项列表的模型
class ActionOptionsLLMOutput(BaseModel):
    """LLM 输出的行动选项列表模型"""
    options: List[ActionOption] = Field(..., description="包含多个行动选项的列表")
