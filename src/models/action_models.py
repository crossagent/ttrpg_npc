from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime

# Import the new union type
from src.models.consequence_models import AnyConsequence
# +++ 添加 Literal 导入 +++
from typing import List, Optional, Dict, Any, Union, Literal


# +++ 新增：关系影响评估模型 +++
class RelationshipImpactType(str, Enum):
    """关系影响类型【【【【【【【【【【【【【【【【【【【【【【【【【【【【【【【【【【【【【【【【【【【【枚举"""
    POSITIVE_MATCH = "positive_match" # 行为/言论符合NPC偏好/价值观
    NEGATIVE_CLASH = "negative_clash" # 行为/言论违背NPC偏好/价值观
    NEUTRAL = "neutral"           # 行为/言论与NPC偏好/价值观无关或影响轻微

class ImpactIntensity(str, Enum):
    """影响强度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class RelationshipImpactAssessment(BaseModel):
    """LLM对玩家行为/对话造成的关系影响评估结果"""
    interaction_type: RelationshipImpactType = Field(..., description="互动影响类型 (正面匹配/负面冲突/中立)")
    intensity: ImpactIntensity = Field(..., description="影响强度 (低/中/高)")
    reason: str = Field(..., description="评估理由 (LLM解释判断依据)")
    suggested_change: int = Field(..., description="建议的关系值变化量 (例如: +10, -5, 0)")


# Add this new model before InternalThoughts class
class AttitudeType(str, Enum):
    """态度类型枚举"""
    FRIENDLY = "友好"
    NEUTRAL = "中立"
    HOSTILE = "敌对"
    UNKNOWN = "未知"

class TrustLevel(str, Enum):
    """信任程度枚举"""
    HIGH = "高度信任"
    MODERATE = "一般信任" 
    LOW = "低度信任"
    DISTRUSTFUL = "不信任"
    UNKNOWN = "未知"

class PlayerAssessment(BaseModel):
    """角色对其他玩家的评估模型"""
    intention: str = Field("", description="对其行为意图的评估")
    attitude_toward_self: AttitudeType = Field(AttitudeType.UNKNOWN, description="对自己的态度")
    trust_level: TrustLevel = Field(TrustLevel.UNKNOWN, description="信任程度")
    power_assessment: str = Field("", description="实力与资源评估")
    last_interaction: Optional[datetime] = Field(None, description="最后交互时间")

class InternalThoughts(BaseModel):
    """角色内心世界模型，表示角色的心理状态、观察和分析"""
    # 背景与目标
    short_term_goals: List[str] = Field(default_factory=list, description="短期目标")
    
    # 情绪与心理状态
    primary_emotion: str = Field("平静", description="当前主要情绪")
    psychological_state: str = Field("正常", description="心理状态描述")
    
    # 局势分析
    narrative_analysis: str = Field("", description="对DM叙事的理解与总结")
    other_players_assessment: Dict[str, PlayerAssessment] = Field(default_factory=dict, description="对其他玩家的详细评估(使用角色ID作为键)")
    perceived_risks: List[str] = Field(default_factory=list, description="感知到的风险")
    perceived_opportunities: List[str] = Field(default_factory=list, description="感知到的机会")
    
    # 更新时间
    last_updated: datetime = Field(default_factory=datetime.now, description="最后更新时间")
    last_updated_round: int = Field(0, description="最后更新的回合数")

class ActionType(str, Enum):
    """玩家行动类型枚举"""
    TALK = "讨论沟通"       # 用于描述玩家之间的讨论和沟通
    ACTION = "主要行动"     # 表示会对环境或剧情产生实质性影响的主要行动
    WAIT = "继续旁观"    # 表示玩家选择持续旁观而不进行干预


# 新增：定义行动选项的模型
class ActionOption(BaseModel):
    """代表一个可供玩家选择的行动选项"""
    action_type: ActionType = Field(..., description="行动类型 (TALK, ACTION, WAIT)")
    content: str = Field(..., description="行动内容描述")
    target: Optional[str] = Field(None, description="行动目标 (角色ID, 'environment', 'all', etc.)")


class PlayerAction(BaseModel):
    """玩家行动模型，表示玩家在回合中采取的行动"""
    character_id: str = Field(..., description="玩家ID")
    internal_thoughts: Optional[InternalThoughts] = Field(None, description="行动背后的内心活动") # 修正拼写错误
    action_type: ActionType = Field(..., description="行动类型")
    content: str = Field(..., description="行动内容")
    target: Optional[Union[str, List[str]]] = Field(None, description="行动目标，可以是单个角色ID、多个角色ID列表或None") # 允许None并设为可选
    minor_action: Optional[str] = Field(None, description="伴随对话的微小动作 (例如: 叹气, 撩头发), 主要用于 TALK 类型")
    generated_consequences: List[AnyConsequence] = Field(default_factory=list, description="由Agent内部状态变化（如关系评估）产生的后果") # 新增字段, 更新类型



class DiceResult(BaseModel):
    """骰子结果模型，表示掷骰的结果"""
    raw_value: int = Field(..., description="原始骰子值")
    modified_value: int = Field(..., description="经过修饰后的最终值")
    modifiers: Dict[str, int] = Field(default_factory=dict, description="修饰因素，如技能加成等")


class ActionResult(BaseModel):
    """行动结果模型，表示玩家行动的处理结果"""
    character_id: str = Field(..., description="角色ID")
    action: PlayerAction = Field(..., description="原始行动")
    success: bool = Field(..., description="行动是否成功")
    narrative: str = Field(..., description="结果叙述")
    dice_result: Optional[DiceResult] = Field(None, description="如果涉及掷骰，则包含骰子结果")
    consequences: List[AnyConsequence] = Field(default_factory=list, description="行动导致的结构化后果列表") # 更新类型


class ActionResolutionRequest(BaseModel):
    """行动解析请求模型，用于请求DM解析玩家行动"""
    player_id: str = Field(..., description="玩家ID")
    action: str = Field(..., description="行动描述")
    game_state: Any = Field(..., description="当前游戏状态")
    dice_result: Optional[DiceResult] = Field(None, description="如果已经掷骰，则包含骰子结果")


class ItemQuery(BaseModel):
    """物品查询模型，用于查询玩家是否拥有某物品"""
    player_id: str = Field(..., description="玩家ID")
    item_id: str = Field(..., description="物品ID")


class ItemResult(BaseModel):
    """物品查询结果模型，表示物品查询的结果"""
    has_item: bool = Field(..., description="玩家是否拥有该物品")
    quantity: int = Field(0, description="物品数量")
    details: Optional[Dict[str, Any]] = Field(None, description="物品详情")
