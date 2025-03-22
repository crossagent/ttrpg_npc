from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from src.models.action_models import ActionType


class ActionDecisionLogic(BaseModel):
    """行动决策逻辑模型，表示角色的决策过程"""
    goal: str = Field(..., description="当前的主要目标")
    plan: str = Field(..., description="实现目标的计划")
    mood: str = Field(..., description="当前的心情")
    health: int = Field(..., description="当前的血量(0-100)")


class PlayerActionLLMOutput(BaseModel):
    """LLM输出的玩家行动模型"""
    observation: str = Field(..., description="观察到的环境和其他角色的信息")
    action_thought: ActionDecisionLogic = Field(..., description="行动决策逻辑")
    thinking: str = Field(..., description="内心想法和决策过程")
    action: str = Field(..., description="实际采取的行动")
    action_type: str = Field(default="对话", description="行动类型")
    target: Union[str, List[str]] = Field(default="all", description="行动目标")


class PlayerContextText(BaseModel):
    """玩家上下文文本模型，表示发送给LLM的玩家信息文本"""
    player_id: str = Field(..., description="玩家ID")
    character_description: str = Field(..., description="角色描述文本")
    goal_description: str = Field(..., description="角色目标描述")
    environment_description: str = Field(..., description="环境描述文本")
    knowledge_description: str = Field(..., description="已知信息描述")
    status_description: str = Field(..., description="当前状态描述")
    recent_events_description: str = Field(..., description="最近事件描述")
    relationships_description: str = Field(..., description="关系描述文本")
    items_description: str = Field("", description="物品描述文本")


class DMContextText(BaseModel):
    """DM上下文文本模型，表示发送给LLM的DM信息文本"""
    game_progress_description: str = Field(..., description="游戏进展描述")
    character_summaries: str = Field(..., description="所有角色状态摘要")
    environment_description: str = Field(..., description="环境详细描述")
    active_events_description: str = Field(..., description="活跃事件描述")
    secrets_description: str = Field(..., description="未揭示的秘密描述")
    narrative_guidance: str = Field(..., description="叙事指导建议")

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
