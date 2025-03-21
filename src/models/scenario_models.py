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
    
class Scenario(BaseModel):
    """游戏剧本 - 所有静态数据的容器"""
    story_info: StoryInfo = Field(..., description="故事背景信息")
    characters: Dict[str, ScenarioCharacterInfo] = Field(..., description="角色信息字典，键为角色ID")
    events: List[ScenarioEvent] = Field(..., description="剧本事件列表")
    game_stages: Optional[Dict[str, GameStageInfo]] = Field(None, description="游戏阶段信息")
    locations: Optional[Dict[str, LocationInfo]] = Field(None, description="游戏地点详情")
    items: Optional[Dict[str, ItemInfo]] = Field(None, description="游戏物品详情")
    
    class Config:
        """模型配置"""
        arbitrary_types_allowed = True
        
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> "Scenario":
        """从JSON数据创建剧本模型实例
        
        处理标准化的英文字段JSON结构
        """
        # 处理story_info
        story_info_data = json_data.get("story_info", {})
        
        # 创建StoryInfo对象
        story_info = StoryInfo(
            background=story_info_data.get("background", ""),
            secrets={"main_secret": story_info_data.get("secret", "")}
        )
        
        # 处理characters
        characters = {}
        for char_id, info in json_data.get("characters", {}).items():
            character = ScenarioCharacterInfo(
                public_identity=info.get("public_identity", ""),
                secret_goal=info.get("secret_goal", "")
            )
            
            # 添加可选字段
            if "background" in info:
                character.background_story = info["background"]
            if "special_ability" in info:
                character.special_ability = info["special_ability"]
            if "weakness" in info:
                character.weakness = info["weakness"]
                
            characters[char_id] = character
        
        # 处理events
        events = []
        for event_data in json_data.get("events", []):
            event = ScenarioEvent(
                event_id=event_data.get("event_id", ""),
                description=event_data.get("description", ""),
                trigger_condition=event_data.get("trigger_condition", ""),
                aware_players=event_data.get("perceptible_players", ["all"]),
                possible_outcomes=event_data.get("possible_outcomes", [])
            )
            
            # 添加可选字段
            if "content" in event_data:
                event.content = event_data["content"]
            if "consequences" in event_data:
                event.outcome_effects = event_data["consequences"]
            
            events.append(event)
        
        # 创建基本剧本
        scenario = cls(
            story_info=story_info,
            characters=characters,
            events=events
        )
        
        # 添加可选的游戏阶段
        if "game_phases" in json_data:
            game_stages = {}
            for phase_id, phase_info in json_data["game_phases"].items():
                game_stages[phase_id] = GameStageInfo(
                    description=phase_info.get("description", ""),
                    objectives=phase_info.get("objective", ""),
                    key_events=phase_info.get("key_events", [])
                )
            scenario.game_stages = game_stages
            
        # 添加关键物品 - 处理数组格式
        if "key_items" in json_data:
            items = {}
            for item_data in json_data["key_items"]:
                if "id" in item_data and "description" in item_data:
                    item_id = item_data["id"]
                    items[item_id] = ItemInfo(
                        description=item_data["description"],
                        location=item_data.get("location"),
                        related_characters=item_data.get("related_characters", []),
                        difficulty=item_data.get("acquisition_difficulty")
                    )
                    
                    # 添加额外效果信息
                    if "difficulty_details" in item_data:
                        if not items[item_id].effects:
                            items[item_id].effects = {}
                        items[item_id].effects["difficulty_details"] = item_data["difficulty_details"]
                        
            scenario.items = items
        
        # 处理地点详情
        if "locations" in json_data:
            locations = {}
            for loc_data in json_data["locations"]:
                if "id" in loc_data and "description" in loc_data:
                    loc_id = loc_data["id"]
                    
                    # 构建基本LocationInfo
                    location_info = LocationInfo(
                        description=loc_data["description"]
                    )
                    
                    # 添加可选字段
                    if "connected_locations" in loc_data:
                        location_info.connected_locations = loc_data["connected_locations"]
                    if "available_items" in loc_data:
                        location_info.available_items = loc_data["available_items"]
                    if "danger_level" in loc_data:
                        location_info.danger_level = loc_data["danger_level"]
                        
                    locations[loc_id] = location_info
                    
            scenario.locations = locations
            
        return scenario