from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union

class CharacterInfo(BaseModel):
    """角色信息模型"""
    identity: str = Field(..., description="角色的公开身份")
    goal: str = Field(..., description="角色的秘密目标")
    plan: str = Field(..., description="角色的计划")
    mood: str = Field(..., description="角色的情绪")
    
class ScenarioEvent(BaseModel):
    """剧本事件模型"""
    event_id: str = Field(..., description="事件唯一标识符")
    description: str = Field(..., description="事件描述")
    trigger_condition: str = Field(..., description="事件触发条件")
    aware_players: List[str] = Field(..., description="可感知该事件的玩家列表")
    possible_outcomes: List[str] = Field(..., description="事件可能的结局列表")
    
    # 可选的扩展字段
    location: Optional[str] = Field(None, description="事件发生地点")
    required_items: Optional[List[str]] = Field(None, description="事件所需物品")
    difficulty: Optional[str] = Field(None, description="事件难度等级")
    
class StoryInfo(BaseModel):
    """故事背景信息模型"""
    background: str = Field(..., description="故事背景")
    secrets: Dict[str, str] = Field(..., description="故事重要秘密")
    
class Scenario(BaseModel):
    """完整游戏剧本模型"""
    story_info: StoryInfo = Field(..., description="故事背景信息")
    characters: Dict[str, CharacterInfo] = Field(..., description="角色信息字典，键为角色名")
    events: List[ScenarioEvent] = Field(..., description="剧本事件列表")
    
    # 可选的扩展字段
    game_stages: Optional[List[str]] = Field(None, description="游戏阶段列表")
    locations: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="游戏地点详情")
    items: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="游戏物品详情")
    
    class Config:
        """模型配置"""
        arbitrary_types_allowed = True
        