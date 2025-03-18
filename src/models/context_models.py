from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class PlayerContext(BaseModel):
    """玩家上下文模型，表示玩家可见的信息"""
    player_id: str = Field(..., description="玩家ID")
    character_name: str = Field(..., description="角色名称")
    visible_messages: List[Dict[str, Any]] = Field(default_factory=list, description="可见的消息列表")
    known_locations: List[str] = Field(default_factory=list, description="已知的位置")
    known_characters: List[str] = Field(default_factory=list, description="已知的角色")
    known_items: List[str] = Field(default_factory=list, description="已知的物品")
    personal_state: Dict[str, Any] = Field(default_factory=dict, description="个人状态")
    last_updated: datetime = Field(default_factory=datetime.now, description="上次更新时间")


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
