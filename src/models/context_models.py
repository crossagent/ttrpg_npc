from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class MessageStatus(BaseModel):
    """消息状态模型"""
    message_id: str = Field(..., description="消息ID")
    read_status: bool = Field(False, description="是否已读")
    read_timestamp: Optional[datetime] = Field(None, description="读取时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PlayerContext(BaseModel):
    """玩家上下文模型，表示玩家可见的信息"""
    player_id: str = Field(..., description="玩家ID")
    character_name: str = Field(..., description="角色名称")
    history_messages: Dict[str, MessageStatus] = Field(default_factory=dict, description="可见的消息状态，键为消息ID")
    goal: str = Field(..., description="角色的秘密目标")
    plan: str = Field(..., description="角色的计划")
    mood: str = Field(..., description="角色的情绪")
    locations: str = Field(..., description="角色所在的位置")
    known_locations: List[str] = Field(default_factory=list, description="已知的位置")
    known_characters: List[str] = Field(default_factory=list, description="已知的角色")
    known_items: List[str] = Field(default_factory=list, description="已知的物品")
    personal_state: Dict[str, Any] = Field(default_factory=dict, description="个人状态")
    last_updated: datetime = Field(default_factory=datetime.now, description="上次更新时间")

# 新增场景状态模型
class LocationState(BaseModel):
    """场景状态模型"""
    status: str = Field(..., description="场景状态(未搜索/部分搜索/被搜索过)")
    radiation_level: str = Field("低", description="辐射水平(低/中/高)")
    available_items: List[str] = Field(default_factory=list, description="可获取的物品")
    description: Optional[str] = Field(None, description="场景描述")
    connected_locations: List[str] = Field(default_factory=list, description="相连接的场景")
    special_features: Dict[str, Any] = Field(default_factory=dict, description="特殊特性")

# 新增角色状态模型
class CharacterState(BaseModel):
    """角色状态模型"""
    location: str = Field(..., description="当前位置")
    items: List[str] = Field(default_factory=list, description="持有物品")
    radiation_level: Optional[str] = Field(None, description="辐射水平")
    health: Optional[str] = Field("正常", description="健康状态")
    relationships: Dict[str, int] = Field(default_factory=dict, description="与其他角色的关系值(-100到100)")
    revealed_secrets: List[str] = Field(default_factory=list, description="已揭露的秘密")
    status_effects: List[str] = Field(default_factory=list, description="状态效果")
    additional_info: Dict[str, Any] = Field(default_factory=dict, description="额外信息")

# 新增DM上下文模型
class DMContext(BaseModel):
    """DM上下文模型，表示DM可见的全局信息"""
    message_status: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="所有消息状态")
    characters: Dict[str, CharacterState] = Field(default_factory=dict, description="所有角色状态")
    locations: Dict[str, LocationState] = Field(default_factory=dict, description="所有场景状态")
    
    # 游戏进展相关
    current_round: int = Field(0, description="当前回合数")
    game_phase: str = Field("探索阶段", description="当前游戏阶段(探索阶段/博弈阶段/冲突阶段/真相阶段)")
    revealed_events: List[str] = Field(default_factory=list, description="已触发的事件ID")
    pending_events: List[str] = Field(default_factory=list, description="待触发的事件ID")
    
    # 游戏状态相关
    global_state: Dict[str, Any] = Field(default_factory=dict, description="全局状态变量")
    event_log: List[Dict[str, Any]] = Field(default_factory=list, description="事件日志")
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
