from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum


class ActionType(str, Enum):
    """玩家行动类型枚举"""
    DIALOGUE = "对话"
    ACTION = "行动"
    IGNORE = "无视"


class PlayerAction(BaseModel):
    """玩家行动模型，表示玩家在回合中采取的行动"""
    player_id: str = Field(..., description="玩家ID")
    action_type: ActionType = Field(..., description="行动类型")
    content: str = Field(..., description="行动内容")
    target: Union[str, List[str]] = Field(..., description="行动目标，可以是单个角色ID或多个角色ID列表")


class DiceResult(BaseModel):
    """骰子结果模型，表示掷骰的结果"""
    raw_value: int = Field(..., description="原始骰子值")
    modified_value: int = Field(..., description="经过修饰后的最终值")
    modifiers: Dict[str, int] = Field(default_factory=dict, description="修饰因素，如技能加成等")


class ActionResult(BaseModel):
    """行动结果模型，表示玩家行动的处理结果"""
    player_id: str = Field(..., description="玩家ID")
    action: PlayerAction = Field(..., description="原始行动")
    success: bool = Field(..., description="行动是否成功")
    narrative: str = Field(..., description="结果叙述")
    dice_result: Optional[DiceResult] = Field(None, description="如果涉及掷骰，则包含骰子结果")
    state_changes: Dict[str, Any] = Field(default_factory=dict, description="导致的状态变化")


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
