from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union, Literal
from enum import Enum
from datetime import datetime
from src.models.scenario_models import ScenarioEvent, Scenario
from src.models.message_models import Message, MessageStatus

class GamePhase(str, Enum):
    """游戏阶段枚举"""
    EXPLORATION = "探索阶段"
    NEGOTIATION = "博弈阶段"
    CONFLICT = "冲突阶段"
    REVELATION = "真相阶段"

# 添加角色内部思考记录模型
class InnerThought(BaseModel):
    """角色内部思考记录"""
    timestamp: datetime = Field(default_factory=datetime.now, description="思考发生的时间")
    round_id: int = Field(..., description="所属回合ID")
    observe: str = Field(..., description="观察的内容")
    thought: str = Field(..., description="思考的内容")
    decision: str = Field(..., description="决策的内容")

class MessageReadMemory(BaseModel):
    """消息已读记录模型"""
    player_id: str = Field(..., description="玩家ID")
    history_messages: Dict[str, MessageStatus] = Field(default_factory=dict, description="可见的消息状态，键为消息ID")
    inner_thoughts: List[InnerThought] = Field(default_factory=list, description="角色的心理活动记录（观察、思考、决策）")

class CharacterStatus(BaseModel):
    """角色状态模型，表示角色的当前状态"""
    character_id: str = Field(..., description="角色ID")
    location: str = Field(..., description="当前位置")
    health: int = Field(100, description="健康值")
    items: List[str] = Field(default_factory=list, description="拥有的物品")
    conditions: List[str] = Field(default_factory=list, description="当前状态效果")
    relationships: Dict[str, int] = Field(default_factory=dict, description="与其他角色的关系值(使用角色ID作为键)")
    known_information: List[str] = Field(default_factory=list, description="已知信息")
    # 修改为单个字符串
    goal: str = Field("", description="角色当前的主要目标")
    plans: str = Field("", description="角色达成目标的计划")
    # 添加内部思考历史
    inner_thoughts: List[InnerThought] = Field(default_factory=list, description="角色的心理活动记录（观察、思考、决策）")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="其他属性")


class LocationStatus(BaseModel):
    """位置状态模型，跟踪地点当前状态"""
    location_id: str = Field(..., description="地点ID")
    search_status: str = Field("未搜索", description="搜索状态(未搜索/部分搜索/被搜索过)")
    available_items: List[str] = Field(default_factory=list, description="当前可获取的物品")
    present_characters: List[str] = Field(default_factory=list, description="当前在此位置的角色")


class EnvironmentStatus(BaseModel):
    """环境状态模型，表示游戏环境的当前状态"""
    current_location_id: str = Field(..., description="当前主要场景位置ID")
    time: datetime = Field(default_factory=datetime.now, description="游戏内时间")
    weather: str = Field("晴朗", description="天气状况")
    lighting: str = Field("明亮", description="光照条件")
    atmosphere: str = Field("平静", description="氛围")


class EventInstance(BaseModel):
    """事件实例模型，表示游戏中的运行时事件实例"""
    instance_id: str = Field(..., description="事件实例ID")
    scenario_event_id: str = Field(..., description="对应的剧本事件ID")
    is_active: bool = Field(False, description="事件是否激活")
    is_completed: bool = Field(False, description="事件是否完成")
    related_character_ids: List[str] = Field(default_factory=list, description="相关角色ID列表")
    outcome: Optional[str] = Field(None, description="实际发生的事件结果")
    occurred_at: Optional[datetime] = Field(None, description="事件发生时间")
    triggered_by: Optional[str] = Field(None, description="触发该事件的条件/动作")
    revealed_to: List[str] = Field(default_factory=list, description="事件对哪些角色可见")


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
    scenario: Optional[Scenario] = Field(None, description="使用的剧本实例")
    round_number: int = Field(0, description="当前回合数")
    max_rounds: int = Field(10, description="最大回合数")
    is_finished: bool = Field(False, description="游戏是否结束")
    current_phase: GamePhase = Field(GamePhase.EXPLORATION, description="当前游戏阶段")
    
    # 游戏中的角色、事件、环境状态-模板来自于剧本
    characters: Dict[str, CharacterInstance] = Field(default_factory=dict, description="角色引用字典，键为角色ID")
    environment: EnvironmentStatus = Field(..., description="环境状态")
    active_events: Dict[str, EventInstance] = Field(default_factory=dict, description="活跃事件，键为实例ID")
    completed_events: Dict[str, EventInstance] = Field(default_factory=dict, description="已完成事件，键为实例ID")
    pending_events: Dict[str, EventInstance] = Field(default_factory=dict, description="待触发事件，键为实例ID")
    
    # 游戏进度相关
    chat_history: List[Message] = Field(default_factory=list, description="完整消息历史记录列表")
    revealed_secrets: List[str] = Field(default_factory=list, description="已揭示的秘密")
    game_variables: Dict[str, Any] = Field(default_factory=dict, description="游戏变量，用于条件判断")
    

    context: Dict[str, Any] = Field(default_factory=dict, description="游戏上下文")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")
