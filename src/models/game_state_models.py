from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from datetime import datetime
from src.models.scenario_models import ScenarioEvent
from src.models.message_models import Message


class CharacterStatus(BaseModel):
    """角色状态模型，表示角色的当前状态"""
    character_id: str = Field(..., description="角色ID")
    location: str = Field(..., description="当前位置")
    health: int = Field(100, description="健康值")
    items: List[str] = Field(default_factory=list, description="拥有的物品")
    conditions: List[str] = Field(default_factory=list, description="当前状态效果")
    relationships: Dict[str, int] = Field(default_factory=dict, description="与其他角色的关系值(使用角色ID作为键)")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="其他属性")


class EnvironmentStatus(BaseModel):
    """环境状态模型，表示游戏环境的当前状态"""
    current_location_id: str = Field(..., description="当前主要场景位置ID")
    time: datetime = Field(default_factory=datetime.now, description="游戏内时间")
    weather: str = Field("晴朗", description="天气状况")
    lighting: str = Field("明亮", description="光照条件")
    atmosphere: str = Field("平静", description="氛围")
    hazards: List[str] = Field(default_factory=list, description="环境危害")
    properties: Dict[str, Any] = Field(default_factory=dict, description="其他环境属性")


class EventInstance(BaseModel):
    """事件实例模型，表示游戏中的运行时事件实例"""
    instance_id: str = Field(..., description="事件实例ID")
    scenario_event_id: str = Field(..., description="对应的剧本事件ID")
    is_active: bool = Field(False, description="事件是否激活")
    is_completed: bool = Field(False, description="事件是否完成")
    related_character_ids: List[str] = Field(default_factory=list, description="相关角色ID列表")
    outcome: Optional[str] = Field(None, description="实际发生的事件结果")
    occurred_at: Optional[datetime] = Field(None, description="事件发生时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class CharacterReference(BaseModel):
    """角色引用模型，游戏状态中引用剧本中的角色"""
    character_id: str = Field(..., description="游戏中的角色ID")
    scenario_character_id: str = Field(..., description="对应剧本角色ID")
    name: str = Field(..., description="角色名称")
    player_controlled: bool = Field(False, description="是否由玩家控制")
    status_id: Optional[str] = Field(None, description="对应的角色状态ID")
    additional_info: Dict[str, Any] = Field(default_factory=dict, description="运行时附加信息")


class GameState(BaseModel):
    """完整游戏状态模型，表示游戏的当前状态"""
    game_id: str = Field(..., description="游戏实例ID")
    scenario_id: str = Field(..., description="使用的剧本ID")
    round_number: int = Field(0, description="当前回合数")
    max_rounds: int = Field(10, description="最大回合数")
    is_finished: bool = Field(False, description="游戏是否结束")
    
    # 使用ID索引的核心数据
    characters: Dict[str, CharacterReference] = Field(default_factory=dict, description="角色引用字典，键为角色ID")
    character_status: Dict[str, CharacterStatus] = Field(default_factory=dict, description="角色状态字典，键为状态ID")
    environment: EnvironmentStatus = Field(..., description="环境状态")
    active_events: Dict[str, EventInstance] = Field(default_factory=dict, description="活跃事件，键为实例ID")
    completed_events: Dict[str, EventInstance] = Field(default_factory=dict, description="已完成事件，键为实例ID")
    
    # 游戏进度相关
    chat_history: List[Message] = Field(default_factory=list, description="完整消息历史记录列表")
    context: Dict[str, Any] = Field(default_factory=dict, description="游戏上下文")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")
