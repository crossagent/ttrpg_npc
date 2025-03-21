from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union, Literal
from enum import Enum
from datetime import datetime
from src.models.scenario_models import Scenario, ScenarioCharacterInfo, ScenarioEvent, LocationInfo, ItemInfo, StoryStage, StorySection, StoryChapter
from src.models.message_models import Message

class GamePhase(str, Enum):
    """游戏阶段枚举"""
    EXPLORATION = "探索阶段"
    NEGOTIATION = "博弈阶段"
    CONFLICT = "冲突阶段"
    REVELATION = "真相阶段"

class InnerThought(BaseModel):
    """角色内部思考记录"""
    timestamp: datetime = Field(default_factory=datetime.now, description="思考发生的时间")
    round_id: int = Field(..., description="所属回合ID")
    observe: str = Field(..., description="观察的内容")
    thought: str = Field(..., description="思考的内容")
    decision: str = Field(..., description="决策的内容")

class MessageReadStatus(Enum):
    """消息读取状态枚举"""
    UNREAD = "未读"
    READ = "已读"
    REPLIED = "已回复"

class MessageReadMemory(BaseModel):
    """消息已读记录模型"""
    player_id: str = Field(..., description="玩家ID")
    history_messages: Dict[str, MessageReadStatus] = Field(default_factory=dict, description="可见的消息状态，键为消息ID")
    inner_thoughts: List[InnerThought] = Field(default_factory=list, description="角色的心理活动记录（观察、思考、决策）")

class CharacterStatus(BaseModel):
    """角色状态模型，表示角色的当前状态"""
    character_id: str = Field(..., description="角色ID")
    location: str = Field(..., description="当前位置")
    health: int = Field(100, description="健康值")
    items: Optional[List[str]] = Field(default_factory=list, description="拥有的物品，None表示未确定")
    conditions: List[str] = Field(default_factory=list, description="当前状态效果")
    relationships: Dict[str, int] = Field(default_factory=dict, description="与其他角色的关系值(使用角色ID作为键)")
    known_information: Optional[List[str]] = Field(default_factory=list, description="已知信息，None表示未确定")
    goal: str = Field("", description="角色当前的主要目标")
    plans: str = Field("", description="角色达成目标的计划")
    inner_thoughts: List[InnerThought] = Field(default_factory=list, description="角色的心理活动记录（观察、思考、决策）")

class LocationStatus(BaseModel):
    """位置状态模型，跟踪地点当前状态"""
    location_id: str = Field(..., description="地点ID")
    search_status: str = Field("未搜索", description="搜索状态(未搜索/部分搜索/被搜索过)")
    available_items: Optional[List[str]] = Field(default_factory=list, description="当前可获取的物品，None表示未确定")
    present_characters: List[str] = Field(default_factory=list, description="当前在此位置的角色")
    description_state: str = Field("", description="当前位置状态描述(例如,是否有破坏,特殊情况等)")

class ItemStatus(BaseModel):
    """物品状态模型，跟踪物品当前状态"""
    item_id: str = Field(..., description="物品ID")
    current_location: str = Field(..., description="当前位置(可以是地点ID或角色ID)")
    is_hidden: bool = Field(True, description="是否隐藏")
    condition: str = Field("完好", description="物品状态")
    discovered_by: Optional[List[str]] = Field(default_factory=list, description="已被哪些角色发现，None表示未确定")

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
    public_identity: str = Field(..., description="对应剧本角色ID")
    name: str = Field(..., description="角色名称")
    player_controlled: bool = Field(False, description="是否由玩家控制")
    status: CharacterStatus = Field(..., description="角色状态")

class GameState(BaseModel):
    """完整游戏状态模型，表示游戏的当前状态"""
    game_id: str = Field(..., description="游戏实例ID")
    scenario_id: str = Field(..., description="使用的剧本ID")
    scenario: Optional[Scenario] = Field(None, description="使用的剧本实例")
    round_number: int = Field(0, description="当前回合数")
    max_rounds: int = Field(10, description="最大回合数")
    is_finished: bool = Field(False, description="游戏是否结束")
    started_at: datetime = Field(default_factory=datetime.now, description="游戏开始时间")
    last_updated: datetime = Field(default_factory=datetime.now, description="最后更新时间")
    
    # 游戏进度
    progress: ProgressStatus = Field(..., description="游戏进度状态")
    
    # 游戏环境状态
    environment: EnvironmentStatus = Field(..., description="环境状态")
    
    # 游戏实例状态 - 所有元素都是实例状态，而非模板
    characters: Dict[str, CharacterInstance] = Field(default_factory=dict, description="角色引用字典，键为角色ID")
    character_states: Dict[str, CharacterStatus] = Field(default_factory=dict, description="角色状态字典，键为角色ID")
    location_states: Dict[str, LocationStatus] = Field(default_factory=dict, description="位置状态字典，键为位置ID")
    item_states: Dict[str, ItemStatus] = Field(default_factory=dict, description="物品状态字典，键为物品ID")
    event_instances: Dict[str, EventInstance] = Field(default_factory=dict, description="事件实例字典，键为实例ID")
    
    # 游戏交互历史
    chat_history: List[Message] = Field(default_factory=list, description="完整消息历史记录列表")
    revealed_secrets: List[str] = Field(default_factory=list, description="已揭示的秘密")
    player_message_status: Dict[str, MessageReadMemory] = Field(default_factory=dict, description="玩家消息状态，键为角色ID")
