from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime


class CharacterStatus(BaseModel):
    """角色状态模型，表示角色的当前状态"""
    location: str = Field(..., description="当前位置")
    health: int = Field(100, description="健康值")
    items: List[str] = Field(default_factory=list, description="拥有的物品")
    conditions: List[str] = Field(default_factory=list, description="当前状态效果")
    relationships: Dict[str, int] = Field(default_factory=dict, description="与其他角色的关系值")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="其他属性")


class EnvironmentStatus(BaseModel):
    """环境状态模型，表示游戏环境的当前状态"""
    current_location: str = Field(..., description="当前主要场景位置")
    time: datetime = Field(default_factory=datetime.now, description="游戏内时间")
    weather: str = Field("晴朗", description="天气状况")
    lighting: str = Field("明亮", description="光照条件")
    atmosphere: str = Field("平静", description="氛围")
    hazards: List[str] = Field(default_factory=list, description="环境危害")
    properties: Dict[str, Any] = Field(default_factory=dict, description="其他环境属性")


class Event(BaseModel):
    """事件模型，表示游戏中的事件"""
    event_id: str = Field(..., description="事件ID")
    name: str = Field(..., description="事件名称")
    description: str = Field(..., description="事件描述")
    triggers: List[str] = Field(default_factory=list, description="触发条件")
    consequences: List[str] = Field(default_factory=list, description="事件后果")
    is_active: bool = Field(False, description="事件是否激活")
    is_completed: bool = Field(False, description="事件是否完成")
    related_characters: List[str] = Field(default_factory=list, description="相关角色")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class CharacterInfo(BaseModel):
    """角色信息模型，表示角色的基本信息"""
    character_id: str = Field(..., description="角色ID")
    name: str = Field(..., description="角色名称")
    description: str = Field(..., description="角色描述")
    background: str = Field(..., description="角色背景")
    goals: List[str] = Field(default_factory=list, description="角色目标")
    skills: Dict[str, int] = Field(default_factory=dict, description="角色技能")
    personality: Dict[str, int] = Field(default_factory=dict, description="性格特点")
    relationships: Dict[str, int] = Field(default_factory=dict, description="初始关系")
    starting_items: List[str] = Field(default_factory=list, description="初始物品")


class GameState(BaseModel):
    """完整游戏状态模型，表示游戏的当前状态"""
    round_number: int = Field(0, description="当前回合数")
    max_rounds: int = Field(10, description="最大回合数")
    is_finished: bool = Field(False, description="游戏是否结束")
    characters: Dict[str, CharacterStatus] = Field(default_factory=dict, description="角色状态")
    environment: EnvironmentStatus = Field(..., description="环境状态")
    active_events: List[Event] = Field(default_factory=list, description="活跃事件")
    completed_events: List[Event] = Field(default_factory=list, description="已完成事件")
    chat_history: List[Any] = Field(default_factory=list, description="聊天历史")
    context: Dict[str, Any] = Field(default_factory=dict, description="游戏上下文")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class Script(BaseModel):
    """剧本模型，表示游戏剧本"""
    script_id: str = Field(..., description="剧本ID")
    title: str = Field(..., description="剧本标题")
    description: str = Field(..., description="剧本描述")
    characters: List[CharacterInfo] = Field(..., description="剧本角色")
    events: List[Event] = Field(..., description="剧本事件")
    locations: Dict[str, Dict[str, Any]] = Field(..., description="剧本位置")
    items: Dict[str, Dict[str, Any]] = Field(..., description="剧本物品")
    initial_state: Dict[str, Any] = Field(..., description="初始状态")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")
