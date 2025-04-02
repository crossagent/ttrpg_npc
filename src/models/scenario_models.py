# src/models/scenario_models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union

# +++ 添加导入 +++
from src.models.consequence_models import Consequence

# +++ 新增模型定义 +++
class AttributeSet(BaseModel):
    """角色属性集合"""
    strength: int = Field(10, description="力量")
    dexterity: int = Field(10, description="敏捷")
    intelligence: int = Field(10, description="智力")
    charisma: int = Field(10, description="魅力")
    # 可以根据需要添加更多属性

class SkillSet(BaseModel):
    """角色技能集合"""
    persuasion: int = Field(0, description="说服")
    stealth: int = Field(0, description="潜行")
    combat: int = Field(0, description="战斗")
    # 可以根据需要添加更多技能

class ScenarioCharacterInfo(BaseModel):
    """剧本角色信息模型 - 静态数据，游戏过程中不变"""
    character_id: str = Field(..., description="角色唯一标识符")
    name: str = Field(..., description="角色名称")
    public_identity: str = Field(..., description="角色的公开身份")
    secret_goal: str = Field(..., description="角色的秘密目标")
    background: Optional[str] = Field(None, description="角色的背景故事")
    special_ability: Optional[str] = Field(None, description="角色的特殊能力")
    weakness: Optional[str] = Field(None, description="角色的弱点")
    is_playable: bool = Field(False, description="是否可供玩家选择或作为陪玩角色")
    # +++ 添加基础属性和技能 +++
    base_attributes: AttributeSet = Field(default_factory=AttributeSet, description="角色的基础属性")
    base_skills: SkillSet = Field(default_factory=SkillSet, description="角色的基础技能")

class EventOutcome(BaseModel):
    """事件结局模型"""
    id: str = Field(..., description="结局唯一标识符")
    description: str = Field(..., description="结局描述")
    consequences: List[Consequence] = Field(..., description="结局导致的结构化后果列表")

class ScenarioEvent(BaseModel):
    """剧本事件模型"""
    event_id: str = Field(..., description="事件唯一标识符")
    name: str = Field(..., description="事件名称")
    description: str = Field(..., description="事件描述")
    trigger_condition: Union[List[Dict[str, Any]], str] = Field(..., description="事件触发条件 (结构化列表或文本描述)")
    perceptible_players: List[str] = Field(..., description="可感知该事件的玩家列表")
    possible_outcomes: List[EventOutcome] = Field(..., description="事件可能的结局列表")

    # 扩展字段
    content: Optional[str] = Field(None, description="事件详细内容")
    location: Optional[str] = Field(None, description="事件发生地点")
    required_items: Optional[List[str]] = Field(None, description="事件所需物品")
    difficulty: Optional[str] = Field(None, description="事件难度等级")


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
    location_detail: Optional[str] = Field(None, description="物品位置详情")
    related_characters: Optional[List[str]] = Field(None, description="相关角色")
    difficulty: Optional[str] = Field(None, description="获取难度")
    difficulty_details: Optional[str] = Field(None, description="难度详情")
    effects: Optional[Dict[str, Any]] = Field(None, description="物品效果")

class StoryInfo(BaseModel):
    """故事背景信息模型"""
    id: Optional[str] = Field(None, description="故事ID")
    title: Optional[str] = Field(None, description="故事标题")
    background: str = Field(..., description="故事背景")
    narrative_style: str = Field(..., description="叙事风格")
    secrets: Dict[str, str] = Field(..., description="故事重要秘密")

class StoryStage(BaseModel):
    """游戏故事阶段模型"""
    id: str = Field(..., description="阶段唯一标识符")
    name: str = Field(..., description="阶段名称")
    description: str = Field(..., description="阶段描述")
    objective: str = Field(..., description="阶段目标")
    locations: List[str] = Field(..., description="相关地点ID列表")
    characters: List[str] = Field(..., description="相关角色ID列表")
    events: List[str] = Field(..., description="相关事件ID列表")
    available_items: Optional[List[str]] = Field(None, description="可获取物品ID列表")
    ending_variables: Optional[List[str]] = Field(None, description="结局相关变量")
    completion_criteria: Optional[List[Dict[str, Any]]] = Field(None, description="完成此阶段所需满足的条件列表 (例如: {'type': 'attribute', 'entity_id': 'player', 'attribute': 'level', 'op': '>=', 'value': 5})")

class StorySection(BaseModel):
    """游戏故事小节模型"""
    id: str = Field(..., description="小节唯一标识符")
    name: str = Field(..., description="小节名称")
    description: str = Field(..., description="小节描述")
    stages: List[StoryStage] = Field(..., description="阶段列表")

class StoryChapter(BaseModel):
    """游戏故事章节模型"""
    id: str = Field(..., description="章节唯一标识符")
    name: str = Field(..., description="章节名称")
    description: str = Field(..., description="章节描述")
    sections: List[StorySection] = Field(..., description="小节列表")

class StoryStructure(BaseModel):
    """游戏故事结构模型"""
    chapters: List[StoryChapter] = Field(..., description="章节列表")

class Scenario(BaseModel):
    """游戏剧本 - 所有静态数据的容器"""
    story_info: StoryInfo = Field(..., description="故事背景信息")
    characters: Dict[str, ScenarioCharacterInfo] = Field(..., description="角色信息字典，键为角色ID")
    events: List[ScenarioEvent] = Field(..., description="剧本事件列表")
    game_stages: Optional[Dict[str, GameStageInfo]] = Field(None, description="游戏阶段信息")
    locations: Optional[Dict[str, LocationInfo]] = Field(None, description="游戏地点详情")
    items: Optional[Dict[str, ItemInfo]] = Field(None, description="游戏物品详情")
    story_structure: Optional[StoryStructure] = Field(None, description="故事结构")

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
        story_info = StoryInfo(
            background=story_info_data.get("background", ""),
            secrets={"main_secret": story_info_data.get("secret", "")}, # Simplified secrets handling
            id=story_info_data.get("id"), # Use get for optional fields
            title=story_info_data.get("title"),
            narrative_style=story_info_data.get("narrative_style", "")
        )

        # 处理characters
        characters = {}
        for char_data in json_data.get("characters", []):
            # Basic validation
            if all(k in char_data for k in ["id", "name", "public_identity", "secret_goal"]):
                character = ScenarioCharacterInfo(
                    character_id=char_data["id"],
                    name=char_data["name"],
                    public_identity=char_data["public_identity"],
                    secret_goal=char_data["secret_goal"],
                    background=char_data.get("background"),
                    special_ability=char_data.get("special_ability"),
                    weakness=char_data.get("weakness"),
                    # 读取 is_playable 字段，默认为 False
                    is_playable=char_data.get("is_playable", False),
                    # +++ 读取基础属性和技能，如果不存在则使用默认值 +++
                    base_attributes=AttributeSet(**char_data.get("base_attributes", {})),
                    base_skills=SkillSet(**char_data.get("base_skills", {}))
                )
                characters[character.character_id] = character
            else:
                 print(f"警告: 跳过不完整的角色数据: {char_data.get('id', '未知ID')}")


        # 处理events
        events = []
        for event_data in json_data.get("events", []):
             # Basic validation
            if all(k in event_data for k in ["id", "name", "description", "trigger_condition", "possible_outcomes"]):
                # 处理 outcomes
                outcomes = []
                for outcome_data in event_data.get("possible_outcomes", []):
                     if all(k in outcome_data for k in ["id", "description"]):
                        consequence_list = []
                        # Check if 'consequences' field exists and is a list (preferred format)
                        raw_consequences = outcome_data.get("consequences")
                        if isinstance(raw_consequences, list):
                            for cons_data in raw_consequences:
                                if isinstance(cons_data, dict): # Ensure it's a dictionary
                                    try:
                                        # Attempt to parse the dictionary into a Consequence object
                                        consequence_list.append(Consequence(**cons_data))
                                    except Exception as e:
                                        print(f"警告: 解析事件 {event_data.get('id', '未知事件ID')} 结局 {outcome_data.get('id', '未知结局ID')} 的结构化后果失败: {e}, 数据: {cons_data}")
                                else:
                                     print(f"警告: 事件 {event_data.get('id', '未知事件ID')} 结局 {outcome_data.get('id', '未知结局ID')} 的后果列表包含非字典元素: {cons_data}")
                        # Fallback for old string format (consider removing later)
                        elif isinstance(raw_consequences, str):
                             print(f"警告: 事件 {event_data.get('id', '未知事件ID')} 结局 {outcome_data.get('id', '未知结局ID')} 使用了旧的字符串后果格式: '{raw_consequences}'. 将尝试创建 send_message 后果。")
                             # You might want a more robust fallback or error handling here
                             consequence_list.append(Consequence(type="send_message", message_content=f"结局效果: {raw_consequences}"))
                        elif raw_consequences is not None:
                             print(f"警告: 事件 {event_data.get('id', '未知事件ID')} 结局 {outcome_data.get('id', '未知结局ID')} 的后果格式未知: {type(raw_consequences)}")


                        outcome = EventOutcome(
                            id=outcome_data["id"],
                            description=outcome_data["description"],
                            consequences=consequence_list
                        )
                        outcomes.append(outcome)
                     else:
                         print(f"警告: 跳过事件 {event_data['id']} 中不完整的结局数据: {outcome_data.get('id', '未知ID')}")


                # 处理 trigger_condition (Union[List[Dict], str])
                raw_trigger = event_data.get("trigger_condition")
                parsed_trigger: Union[List[Dict[str, Any]], str]
                if isinstance(raw_trigger, str):
                    # Store the string directly
                    parsed_trigger = raw_trigger
                elif isinstance(raw_trigger, list):
                    # Assume it's already a list of dicts if it's a list
                    # Add validation if needed to ensure it's List[Dict]
                    parsed_trigger = raw_trigger
                else:
                    # Handle unexpected type, default to empty string or raise error
                    parsed_trigger = "" # Default to empty string if invalid type
                    print(f"警告: 事件 {event_data['id']} 的 trigger_condition 类型未知或无效: {type(raw_trigger)}")

                event = ScenarioEvent(
                    event_id=event_data["id"],
                    name=event_data["name"],
                    description=event_data["description"],
                    trigger_condition=parsed_trigger, # Use parsed trigger
                    perceptible_players=event_data.get("perceptible_players", ["all"]),
                    possible_outcomes=outcomes,
                    # Optional fields
                    content=event_data.get("content"),
                    location=event_data.get("location"),
                    required_items=event_data.get("required_items"),
                    difficulty=event_data.get("difficulty")
                )
                events.append(event)
            else:
                print(f"警告: 跳过不完整的事件数据: {event_data.get('id', '未知ID')}")


        # 创建基本剧本
        scenario = cls(
            story_info=story_info,
            characters=characters,
            events=events
        )

        # 添加关键物品
        items = {}
        for item_data in json_data.get("key_items", []):
            if all(k in item_data for k in ["id", "description"]):
                item_id = item_data["id"]
                items[item_id] = ItemInfo(
                    description=item_data["description"],
                    location=item_data.get("location"),
                    location_detail=item_data.get("location_detail"),
                    related_characters=item_data.get("related_characters"),
                    difficulty=item_data.get("acquisition_difficulty"), # Check key name
                    difficulty_details=item_data.get("difficulty_details"),
                    effects=item_data.get("effects")
                )
            else:
                print(f"警告: 跳过不完整的物品数据: {item_data.get('id', '未知ID')}")
        scenario.items = items if items else None


        # 处理地点详情
        locations = {}
        for loc_data in json_data.get("locations", []):
             if all(k in loc_data for k in ["id", "description"]):
                loc_id = loc_data["id"]
                locations[loc_id] = LocationInfo(
                    description=loc_data["description"],
                    connected_locations=loc_data.get("connected_locations"),
                    available_items=loc_data.get("available_items"),
                    danger_level=loc_data.get("danger_level")
                )
             else:
                 print(f"警告: 跳过不完整的地点数据: {loc_data.get('id', '未知ID')}")
        scenario.locations = locations if locations else None


        # 处理故事结构 (Simplified parsing, assumes correct structure)
        story_structure_data = json_data.get("story_structure")
        if story_structure_data and "chapters" in story_structure_data:
            try:
                chapters = []
                for chapter_data in story_structure_data.get("chapters", []):
                    sections = []
                    for section_data in chapter_data.get("sections", []):
                        stages = []
                        for stage_data in section_data.get("stages", []):
                            # Basic validation for stage
                            if all(k in stage_data for k in ["id", "name", "description", "objective", "locations", "characters", "events"]):
                                stages.append(StoryStage(
                                    id=stage_data["id"],
                                    name=stage_data["name"],
                                    description=stage_data["description"],
                                    objective=stage_data["objective"],
                                    locations=stage_data["locations"],
                                    characters=stage_data["characters"],
                                    events=stage_data["events"],
                                    available_items=stage_data.get("available_items"),
                                    ending_variables=stage_data.get("ending_variables"),
                                    completion_criteria=stage_data.get("completion_criteria") # Added
                                ))
                            else:
                                print(f"警告: 跳过章节 {chapter_data.get('id')} 小节 {section_data.get('id')} 中不完整的阶段数据: {stage_data.get('id', '未知ID')}")

                        # Basic validation for section
                        if all(k in section_data for k in ["id", "name", "description"]):
                             sections.append(StorySection(
                                id=section_data["id"],
                                name=section_data["name"],
                                description=section_data["description"],
                                stages=stages
                            ))
                        else:
                            print(f"警告: 跳过章节 {chapter_data.get('id')} 中不完整的小节数据: {section_data.get('id', '未知ID')}")


                    # Basic validation for chapter
                    if all(k in chapter_data for k in ["id", "name", "description"]):
                        chapters.append(StoryChapter(
                            id=chapter_data["id"],
                            name=chapter_data["name"],
                            description=chapter_data["description"],
                            sections=sections
                        ))
                    else:
                         print(f"警告: 跳过不完整的章节数据: {chapter_data.get('id', '未知ID')}")

                scenario.story_structure = StoryStructure(chapters=chapters)
            except Exception as e:
                print(f"错误: 解析故事结构时出错: {e}")
                scenario.story_structure = None # Set to None on error

        return scenario
