from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union

class ScenarioCharacterInfo(BaseModel):
    """剧本角色信息模型 - 静态数据，游戏过程中不变"""
    public_identity: str = Field(..., description="角色的公开身份")
    secret_goal: str = Field(..., description="角色的秘密目标")
    background_story: Optional[str] = Field(None, description="角色的背景故事")
    special_ability: Optional[str] = Field(None, description="角色的特殊能力")
    weakness: Optional[str] = Field(None, description="角色的弱点")
    
class EventOutcome(BaseModel):
    """事件结局影响模型"""
    outcome_description: str = Field(..., description="结局描述")
    consequences: str = Field(..., description="结局导致的后果")

class ScenarioEvent(BaseModel):
    """剧本事件模型"""
    event_id: str = Field(..., description="事件唯一标识符")
    description: str = Field(..., description="事件描述")
    trigger_condition: str = Field(..., description="事件触发条件")
    aware_players: List[str] = Field(..., description="可感知该事件的玩家列表")
    possible_outcomes: List[str] = Field(..., description="事件可能的结局列表")
    
    # 扩展字段
    content: Optional[str] = Field(None, description="事件详细内容")
    location: Optional[str] = Field(None, description="事件发生地点")
    required_items: Optional[List[str]] = Field(None, description="事件所需物品")
    difficulty: Optional[str] = Field(None, description="事件难度等级")
    outcome_effects: Optional[Dict[str, str]] = Field(None, description="不同结局的后续影响")

class LocationInfo(BaseModel):
    """地点信息模型"""
    description: str = Field(..., description="地点描述")
    connected_locations: Optional[List[str]] = Field(None, description="相连的地点")
    available_items: Optional[List[str]] = Field(None, description="可获取的物品")
    danger_level: Optional[str] = Field(None, description="危险等级")

class GameStageInfo(BaseModel):
    """游戏阶段信息模型"""
    description: str = Field(..., description="阶段描述")
    objectives: str = Field(..., description="阶段目标")
    key_events: List[str] = Field(..., description="关键事件ID列表")

class ItemInfo(BaseModel):
    """物品信息模型"""
    description: str = Field(..., description="物品描述")
    location: Optional[str] = Field(None, description="物品位置")
    related_characters: Optional[List[str]] = Field(None, description="相关角色")
    difficulty: Optional[str] = Field(None, description="获取难度")
    effects: Optional[Dict[str, Any]] = Field(None, description="物品效果")

class StoryInfo(BaseModel):
    """故事背景信息模型"""
    background: str = Field(..., description="故事背景")
    secrets: Dict[str, str] = Field(..., description="故事重要秘密")
    locations_description: Optional[Dict[str, str]] = Field(None, description="地点简要描述")
    
class Scenario(BaseModel):
    """完整游戏剧本模型"""
    story_info: StoryInfo = Field(..., description="故事背景信息")
    characters: Dict[str, ScenarioCharacterInfo] = Field(..., description="角色信息字典，键为角色ID")
    events: List[ScenarioEvent] = Field(..., description="剧本事件列表")
    
    # 扩展字段
    game_stages: Optional[Dict[str, GameStageInfo]] = Field(None, description="游戏阶段信息")
    locations: Optional[Dict[str, LocationInfo]] = Field(None, description="游戏地点详情")
    items: Optional[Dict[str, ItemInfo]] = Field(None, description="游戏物品详情")
    
    class Config:
        """模型配置"""
        arbitrary_types_allowed = True
        
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> "Scenario":
        """从JSON数据创建剧本模型实例
        
        处理中英文字段名称映射和数据结构转换
        """
        # 处理story_info
        story_info = StoryInfo(
            background=json_data["story_info"]["背景"],
            secrets={"货轮秘密": json_data["story_info"]["货轮秘密"]}
        )
        
        if "地点描述" in json_data["story_info"]:
            story_info.locations_description = json_data["story_info"]["地点描述"]
        
        # 处理characters
        characters = {}
        for name, info in json_data["角色信息"].items():
            character = ScenarioCharacterInfo(
                public_identity=info["公开身份"],
                secret_goal=info["秘密目标"]
            )
            
            # 添加可选字段
            if "背景故事" in info:
                character.background_story = info["背景故事"]
            if "特殊能力" in info:
                character.special_ability = info["特殊能力"]
            if "弱点" in info:
                character.weakness = info["弱点"]
                
            characters[name] = character
        
        # 处理events
        events = []
        for event_data in json_data["剧本事件"]:
            event = ScenarioEvent(
                event_id=event_data["事件ID"],
                description=event_data["描述"],
                trigger_condition=event_data["触发条件"],
                aware_players=event_data.get("可感知玩家", ["全部"]),
                possible_outcomes=event_data["可能结局"]
            )
            
            # 添加可选字段
            if "内容" in event_data:
                event.content = event_data["内容"]
            if "后续影响" in event_data:
                event.outcome_effects = event_data["后续影响"]
            
            events.append(event)
        
        # 创建基本剧本
        scenario = cls(
            story_info=story_info,
            characters=characters,
            events=events
        )
        
        # 添加可选的游戏阶段
        if "游戏阶段" in json_data:
            game_stages = {}
            for stage_name, stage_info in json_data["游戏阶段"].items():
                game_stages[stage_name] = GameStageInfo(
                    description=stage_info["描述"],
                    objectives=stage_info["目标"],
                    key_events=stage_info.get("关键事件", [])
                )
            scenario.game_stages = game_stages
            
        # 添加关键物品
        if "关键物品" in json_data:
            items = {}
            for item_name, item_info in json_data["关键物品"].items():
                items[item_name] = ItemInfo(
                    description=item_info["描述"],
                    location=item_info.get("位置"),
                    related_characters=item_info.get("相关角色", []),
                    difficulty=item_info.get("获取难度")
                )
            scenario.items = items
            
        return scenario