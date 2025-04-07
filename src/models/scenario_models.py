# src/models/scenario_models.py
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any, Optional, Union

# Import the new union type and specific types if needed
from src.models.consequence_models import AnyConsequence, SendMessageConsequence, ConsequenceType

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
    character_id: str = Field(..., alias='id', description="角色唯一标识符") # Added alias='id'
    name: str = Field(..., description="角色名称")
    public_identity: str = Field(..., description="角色的公开身份")
    secret_goal: str = Field(..., description="角色的秘密目标")
    background: Optional[str] = Field(None, description="角色的背景故事")
    special_ability: Optional[str] = Field(None, description="角色的特殊能力")
    weakness: Optional[str] = Field(None, description="角色的弱点")
    is_playable: bool = Field(False, description="是否可供玩家选择或作为陪玩角色")
    # +++ 添加内在设定字段 +++
    values: Optional[List[str]] = Field(None, description="角色的核心价值观列表")
    likes: Optional[List[str]] = Field(None, description="角色喜欢的事物/行为列表")
    dislikes: Optional[List[str]] = Field(None, description="角色厌恶的事物/行为列表")
    personality_summary: Optional[str] = Field(None, description="角色性格核心总结，供LLM参考")
    # +++ 添加基础属性和技能 +++
    base_attributes: AttributeSet = Field(default_factory=AttributeSet, description="角色的基础属性")
    base_skills: SkillSet = Field(default_factory=SkillSet, description="角色的基础技能")

class EventOutcome(BaseModel):
    """事件结局模型"""
    id: str = Field(..., description="结局唯一标识符")
    description: str = Field(..., description="结局描述")
    consequences: List[AnyConsequence] = Field(..., description="结局导致的结构化后果列表") # Updated type hint

class ScenarioEvent(BaseModel):
    """剧本事件模型"""
    event_id: str = Field(..., alias='id', description="事件唯一标识符") # Added alias='id'
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
    id: str = Field(..., alias='id', description="地点唯一标识符") # Added id field with alias
    name: str = Field(..., description="地点名称") # Added name field (present in JSON)
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
    id: str = Field(..., alias='id', description="物品唯一标识符") # Added id field with alias
    name: str = Field(..., description="物品名称") # Added name field (present in JSON)
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
        """从JSON数据创建剧本模型实例 (使用 Pydantic 验证)"""
        
        # --- 预处理: 调整数据结构以匹配 Pydantic 模型 ---

        # 1. 将 characters 列表转换为字典 (键为 character_id)
        if "characters" in json_data and isinstance(json_data["characters"], list):
            char_dict = {}
            for char_data in json_data["characters"]:
                if isinstance(char_data, dict) and "id" in char_data:
                    # Pydantic 会自动处理嵌套的 base_attributes 和 base_skills
                    char_dict[char_data["id"]] = char_data
                else:
                     print(f"警告: 跳过格式不正确的角色数据: {char_data}")
            json_data["characters"] = char_dict # 替换原始列表

        # 2. 将 locations 列表转换为字典 (键为 id)
        if "locations" in json_data and isinstance(json_data["locations"], list):
            loc_dict = {}
            for loc_data in json_data["locations"]:
                 if isinstance(loc_data, dict) and "id" in loc_data:
                    loc_dict[loc_data["id"]] = loc_data
                 else:
                     print(f"警告: 跳过格式不正确的地点数据: {loc_data}")
            json_data["locations"] = loc_dict # 替换原始列表

        # 3. 将 key_items 列表转换为 items 字典 (键为 id)
        if "key_items" in json_data and isinstance(json_data["key_items"], list):
            item_dict = {}
            for item_data in json_data["key_items"]:
                 if isinstance(item_data, dict) and "id" in item_data:
                     # 重命名字段以匹配 ItemInfo 模型
                     if "acquisition_difficulty" in item_data and "difficulty" not in item_data:
                         item_data["difficulty"] = item_data.pop("acquisition_difficulty")
                     item_dict[item_data["id"]] = item_data
                 else:
                     print(f"警告: 跳过格式不正确的物品数据: {item_data}")
            json_data["items"] = item_dict # 创建 'items' 键
            del json_data["key_items"] # 删除原始 'key_items' 键

        # 4. 处理 story_info 中的简化 secrets 结构
        if "story_info" in json_data and isinstance(json_data["story_info"], dict):
            story_info_data = json_data["story_info"]
            if "secret" in story_info_data and "secrets" not in story_info_data:
                 story_info_data["secrets"] = {"main_secret": story_info_data["secret"]}
                 # 可以选择删除旧的 'secret' 键: del story_info_data["secret"]

        # --- Pydantic 验证 ---
        # 让 Pydantic 处理整个结构的验证，包括嵌套模型和 AnyConsequence
        try:
            # Pydantic V2 使用 model_validate
            instance = cls.model_validate(json_data)

            # --- 后处理: 处理旧的字符串后果格式 (如果需要保留兼容性) ---
            # 遍历已验证的实例，查找并转换旧格式
            for event in instance.events:
                for outcome in event.possible_outcomes:
                    processed_consequences = []
                    # 检查原始数据中的后果格式
                    original_event_data = next((e for e in json_data.get("events", []) if e.get("id") == event.event_id), None)
                    if original_event_data:
                        original_outcome_data = next((o for o in original_event_data.get("possible_outcomes", []) if o.get("id") == outcome.id), None)
                        if original_outcome_data:
                            raw_consequences = original_outcome_data.get("consequences")
                            if isinstance(raw_consequences, str):
                                print(f"警告: 事件 {event.event_id} 结局 {outcome.id} 使用了旧的字符串后果格式: '{raw_consequences}'. 将创建 SendMessageConsequence。")
                                processed_consequences.append(SendMessageConsequence(message_content=f"结局效果: {raw_consequences}"))
                            elif isinstance(raw_consequences, list):
                                # 如果是列表，Pydantic 应该已经处理了，直接使用验证后的结果
                                processed_consequences.extend(outcome.consequences)
                            elif raw_consequences is not None:
                                 print(f"警告: 事件 {event.event_id} 结局 {outcome.id} 的后果格式未知: {type(raw_consequences)}")
                        else:
                             # 如果原始结局数据找不到，保留 Pydantic 验证的结果
                             processed_consequences.extend(outcome.consequences)
                    else:
                        # 如果原始事件数据找不到，保留 Pydantic 验证的结果
                        processed_consequences.extend(outcome.consequences)
                    
                    # 更新实例中的后果列表
                    # 注意:直接修改 Pydantic 模型实例的字段可能需要配置 model_config(frozen=False)
                    # 或者创建一个新的 EventOutcome 实例。为简单起见，这里假设可以直接修改。
                    # 如果遇到问题，需要调整此部分。
                    outcome.consequences = processed_consequences 

            return instance

        except ValidationError as e:
            print(f"错误: 剧本数据验证失败 (Scenario.from_json):\n{e}")
            # 可以选择引发错误或返回 None/默认值
            raise e # 重新引发验证错误以获得详细信息
        except Exception as e:
            print(f"错误: Scenario.from_json 中发生意外错误: {e}")
            raise e # 重新引发未知错误
