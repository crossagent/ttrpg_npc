from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union, Literal
from enum import Enum
from datetime import datetime
from src.models.scenario_models import Scenario, StoryStage, AttributeSet, SkillSet
from src.models.message_models import Message, MessageStatus
from src.models.action_models import InternalThoughts

class MessageReadMemory(BaseModel):
    """消息已读记录模型"""
    player_id: str = Field(..., description="玩家ID")
    history_messages: Dict[str, MessageStatus] = Field(default_factory=dict, description="可见的消息状态，键为消息ID")


# 正确的 LocationStatus 定义
class LocationStatus(BaseModel):
    """位置状态模型，跟踪地点当前状态"""
    location_id: str = Field(..., description="地点ID")
    search_status: str = Field("未搜索", description="搜索状态(未搜索/部分搜索/被搜索过)")
    available_items: List['ItemInstance'] = Field(default_factory=list, description="当前可获取的物品实例列表") # Updated type hint
    present_characters: List[str] = Field(default_factory=list, description="当前在此位置的角色")
    description_state: str = Field("", description="当前位置状态描述(例如,是否有破坏,特殊情况等)")

# Added ItemInstance model
class ItemInstance(BaseModel):
    """物品实例模型，表示角色或地点持有的具体物品"""
    item_id: str = Field(..., description="物品的唯一标识符 (对应 Scenario.items 中的 key)")
    quantity: int = Field(1, description="持有的数量")
    name: str = Field(..., description="物品的名称 (方便使用，可从 Scenario.items 获取)")
    # 可以添加更多实例特定的属性，例如耐久度、特殊效果等
    # durability: Optional[int] = None
    # effects: List[str] = Field(default_factory=list)

# --- 移除 ItemStatus ---

class EventInstance(BaseModel):
    """事件实例模型，表示游戏中的运行时事件实例"""
    instance_id: str = Field(..., description="事件实例ID")
    event_id: str = Field(..., description="对应的剧本事件ID")
    is_active: bool = Field(False, description="事件是否激活")
    is_completed: bool = Field(False, description="事件是否完成")
    related_character_ids: List[str] = Field(default_factory=list, description="相关角色ID列表")
    outcome: Optional[str] = Field(None, description="实际发生的事件结果")
    occurred_at: Optional[datetime] = Field(None, description="事件发生时间")
    triggered_by: Optional[str] = Field(None, description="触发该事件的条件/动作")
    revealed_to: List[str] = Field(default_factory=list, description="事件对哪些角色可见")

class EnvironmentStatus(BaseModel):
    """环境状态模型，表示游戏环境的当前状态"""
    current_location_id: str = Field(..., description="当前主要场景位置ID")
    time: datetime = Field(default_factory=datetime.now, description="游戏内时间")
    weather: str = Field("晴朗", description="天气状况")
    atmosphere: str = Field("平静", description="当前氛围")
    lighting: str = Field("明亮", description="光照条件")

class ProgressStatus(BaseModel):
    """游戏进度状态"""
    current_chapter_id: str = Field(..., description="当前章ID")
    current_section_id: str = Field(..., description="当前节ID")
    current_stage_id: str = Field(..., description="当前幕ID")
    completed_chapters: List[str] = Field(default_factory=list, description="已完成的章")
    completed_sections: List[str] = Field(default_factory=list, description="已完成的节")
    completed_stages: List[str] = Field(default_factory=list, description="已完成的幕")
    
    # 当前阶段信息缓存
    current_stage: Optional[StoryStage] = Field(None, description="当前阶段的完整信息")
    current_stage_objective_completion: Dict[str, bool] = Field(default_factory=dict, description="当前阶段目标完成情况")
    
    # 进度追踪数据
    stage_start_time: Optional[datetime] = Field(None, description="当前阶段开始时间")
    next_available_progress: List[str] = Field(default_factory=list, description="下一个可用的进度选项")

class CharacterInstance(BaseModel):
    """角色引用模型，表示游戏中的一个角色实例"""
    character_id: str = Field(..., description="角色ID")
    instance_id: str = Field(..., description="角色实例ID")
    public_identity: str = Field(..., description="对应剧本角色ID")
    name: str = Field(..., description="角色名称")
    player_controlled: bool = Field(False, description="是否由玩家控制")
    # +++ 角色核心状态直接在此定义 +++
    attributes: AttributeSet = Field(..., description="角色属性")
    skills: SkillSet = Field(..., description="角色技能")
    health: int = Field(100, description="健康值")
    location: str = Field(..., description="当前位置")
    items: List['ItemInstance'] = Field(default_factory=list, description="拥有的物品实例列表")
    known_information: List[str] = Field(default_factory=list, description="已知信息")

class GameState(BaseModel):
    """完整游戏状态模型，表示游戏的当前状态"""
    game_id: str = Field(..., description="游戏实例ID")
    # scenario_id: str = Field(..., description="使用的剧本ID") # 移除旧的，保留下面新增的
    player_character_id: Optional[str] = Field(None, description="玩家选择控制的角色ID") # 新增字段
    round_number: int = Field(0, description="当前回合数")
    max_rounds: int = Field(10, description="最大回合数")
    is_finished: bool = Field(False, description="游戏是否结束")
    started_at: datetime = Field(default_factory=datetime.now, description="游戏开始时间")
    last_updated: datetime = Field(default_factory=datetime.now, description="最后更新时间")
    last_active_round: int = Field(0, description="最后一个有玩家实质性行动的回合ID")
    
    # 游戏进度
    progress: ProgressStatus = Field(..., description="游戏进度状态")
    
    # 游戏环境状态
    environment: EnvironmentStatus = Field(..., description="环境状态")
    
    # 游戏实例状态 - 所有元素都是实例状态，而非模板
    # scenario: Optional[Scenario] = Field(None, description="使用的剧本实例") # 改为 scenario_id
    scenario_id: str = Field(..., description="使用的剧本ID (用于加载完整剧本)") # 新增字段
    characters: Dict[str, CharacterInstance] = Field(default_factory=dict, description="角色引用字典，键为角色ID")
    location_states: Dict[str, LocationStatus] = Field(default_factory=dict, description="位置状态字典，键为位置ID")
    # item_states: Dict[str, ItemStatus] = Field(default_factory=dict, description="物品状态字典，键为物品ID") # --- 移除 item_states ---
    event_instances: Dict[str, EventInstance] = Field(default_factory=dict, description="事件实例字典，键为实例ID")
    active_event_ids: List[str] = Field(default_factory=list, description="当前激活的、等待玩家或环境触发的事件ID列表")
    
    # 叙事 Flags
    flags: Dict[str, bool] = Field(default_factory=dict, description="Stores the boolean state of narrative flags.")

    # 游戏交互历史 (已移除，将由独立机制管理)
    # chat_history: List[Message] = Field(default_factory=list, description="完整消息历史记录列表")
    revealed_secrets: List[str] = Field(default_factory=list, description="已揭示的秘密")
    character_internal_thoughts: Dict[str, InternalThoughts] = Field(default_factory=dict, description="角色的心理活动记录，键为角色ID")
