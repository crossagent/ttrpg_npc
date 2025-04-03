from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging # Add logging import
from operator import add, sub, mul, truediv # For attribute updates

from typing import List, Dict, Any, Optional, TYPE_CHECKING # Import TYPE_CHECKING
from datetime import datetime
import uuid
import logging # Add logging import
from operator import add, sub, mul, truediv # For attribute updates

from src.models.game_state_models import (
    GameState, CharacterInstance,
    EnvironmentStatus, EventInstance, ProgressStatus,
    LocationStatus, ItemStatus, ItemInstance # Add ItemInstance
)
from src.models.scenario_models import Scenario, StoryStage # Import StoryStage
from src.models.context_models import StateChanges, Inconsistency, StateUpdateRequest
from src.models.action_models import ItemQuery, ItemResult
from src.models.consequence_models import Consequence, ConsequenceType # Import Consequence models
from src.communication.message_dispatcher import MessageDispatcher # Import MessageDispatcher
from src.models.message_models import Message, MessageType, MessageVisibility # Import Message models for broadcasting
import uuid # Import uuid for message IDs
from datetime import datetime # Import datetime for timestamps

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from src.engine.scenario_manager import ScenarioManager


class GameStateManager:
    """
    游戏状态管理器类，负责维护游戏状态的一致性、解析DM叙述中的状态变化、提供状态查询。
    """

    def __init__(self, scenario_manager: 'ScenarioManager', initial_state: Optional[GameState] = None):
        """
        初始化游戏状态管理器

        Args:
            scenario_manager: 剧本管理器实例
            initial_state: 初始游戏状态，如果为None则创建新状态
        """
        self.game_state = initial_state
        self.scenario_manager = scenario_manager # Store the scenario manager
        # self.message_dispatcher = message_dispatcher # Removed dispatcher dependency
        self.logger = logging.getLogger("GameStateManager") # Add logger

    def initialize_game_state(self) -> GameState:
        """
        初始化游戏状态 (现在依赖 self.scenario_manager)

        Returns:
            GameState: 初始化的游戏状态
        """
        # 从 ScenarioManager 获取剧本
        scenario = self.scenario_manager.get_current_scenario()
        if not scenario:
            self.logger.error("无法初始化游戏状态：ScenarioManager 中没有加载剧本。")
            raise ValueError("无法初始化游戏状态：ScenarioManager 中没有加载剧本。")

        # 创建基本游戏状态
        game_id = str(uuid.uuid4())

        # 确定初始地点
        initial_location_id = None
        if scenario.locations:
            # 使用第一个地点作为初始位置
            initial_location_id = next(iter(scenario.locations.keys()))

        # 如果没有找到任何地点，使用默认位置
        if not initial_location_id:
            initial_location_id = "main_location"

        # 创建环境状态
        environment = EnvironmentStatus(
            current_location_id=initial_location_id,
            time=datetime.now(),
            weather="晴朗",
            atmosphere="平静",
            lighting="明亮"
        )

        # 创建进度状态 - 使用第一章节、小节、阶段作为初始值
        current_chapter_id = "chapter_1"
        current_section_id = "section_1"
        current_stage_id = "stage_1"

        if scenario.story_structure and scenario.story_structure.chapters:
            first_chapter = scenario.story_structure.chapters[0]
            current_chapter_id = first_chapter.id
            if first_chapter.sections:
                first_section = first_chapter.sections[0]
                current_section_id = first_section.id
                if first_section.stages:
                    current_stage_id = first_section.stages[0].id

        progress = ProgressStatus(
            current_chapter_id=current_chapter_id,
            current_section_id=current_section_id,
            current_stage_id=current_stage_id
        )

        # 创建游戏状态
        game_state = GameState(
            game_id=game_id,
            scenario_id=scenario.story_info.id,
            scenario=scenario, # Keep scenario reference for now, though ideally accessed via manager
            environment=environment,
            progress=progress
        )

        # 存储游戏状态
        self.game_state = game_state

        # 初始化角色
        self._initialize_characters_from_scenario(game_state, scenario)

        # 初始化场景
        self._initialize_locations_from_scenario(game_state, scenario)

        # 初始化事件
        self._initialize_events_from_scenario(game_state, scenario)

        # --- 阶段三: 初始化后更新活动事件 ---
        self.update_active_events() # This method also needs scenario access, currently uses game_state.scenario
        self.logger.info("游戏状态初始化完成，并已更新初始活动事件列表。")
        # --- 阶段三结束 ---

        # 不再需要将剧本信息复制到context中，因为现在可以直接通过game_state.scenario访问

        return game_state

    def _initialize_characters_from_scenario(self, game_state: GameState, scenario: Scenario):
        """
        从剧本中初始化角色到游戏状态
        
        Args:
            game_state: 游戏状态对象
            scenario: 剧本对象
        """
        # 清空现有角色信息
        game_state.characters = {}
        # game_state.character_states = {} # --- 移除 character_states 初始化 ---

        # 从剧本中加载角色
        if hasattr(scenario, 'characters') and scenario.characters:
            for char_id, character_info in scenario.characters.items():
                # 获取公开身份
                public_identity = getattr(character_info, 'public_identity', f"角色_{char_id}")

                # 确定初始位置
                initial_location = getattr(game_state.environment, 'current_location_id', "main_location")

                character_id=char_id

                # --- 创建 CharacterInstance，直接包含状态 ---
                character_instance = CharacterInstance(
                    character_id=character_id,
                    instance_id = f"char_inst_{(uuid.uuid4().hex[:8])}", # Changed prefix for clarity
                    public_identity=public_identity,
                    name=character_info.name,
                    player_controlled=False,  # 默认为NPC
                    # 直接使用剧本中的基础属性/技能，并设置运行时状态
                    attributes=character_info.base_attributes.copy(deep=True), # Use deep copy
                    skills=character_info.base_skills.copy(deep=True),       # Use deep copy
                    health=100, # Default health
                    location=initial_location,
                    items=[],   # Initial empty inventory
                    known_information=[], # Initial empty knowledge
                )

                # 将角色实例添加到游戏状态
                game_state.characters[character_id] = character_instance
                # --- 不再需要填充 character_states ---
                # game_state.character_states[character_id] = character_status
    
    def _initialize_locations_from_scenario(self, game_state: GameState, scenario: Scenario):
        """
        从剧本中初始化位置到游戏状态
        
        Args:
            game_state: 游戏状态对象
            scenario: 剧本对象
            
        Raises:
            ValueError: 如果剧本中缺少locations信息
        """
        # 检查剧本是否包含位置信息
        if not hasattr(scenario, 'locations') or not scenario.locations:
            # 如果没有locations属性，直接报错
            raise ValueError("剧本结构异常：缺少必要的locations信息。请确保剧本包含至少一个地点。")
        
        # 初始化位置状态
        game_state.location_states = {}
        
        # 从剧本中加载位置
        for loc_id, location_info in scenario.locations.items():
            # --- Correctly initialize available_items as List[ItemInstance] ---
            item_instances: List[ItemInstance] = []
            available_item_ids = getattr(location_info, 'available_items', None) # Get list of IDs or None

            if available_item_ids and isinstance(available_item_ids, list):
                for item_id in available_item_ids:
                    if isinstance(item_id, str): # Ensure it's a string ID
                        item_definition = game_state.scenario.items.get(item_id) if game_state.scenario and game_state.scenario.items else None
                        if item_definition:
                            # Assuming default quantity 1 for items initially present in locations
                            item_instances.append(ItemInstance(item_id=item_id, name=item_definition.name, quantity=1))
                        else:
                            self.logger.warning(f"初始化地点 '{loc_id}' 时警告：在剧本物品定义中未找到物品 ID '{item_id}'。")
                    else:
                         self.logger.warning(f"初始化地点 '{loc_id}' 时警告：available_items 列表中包含非字符串元素 '{item_id}'。")

            # 创建位置状态，使用处理过的 item_instances 列表
            location_status = LocationStatus(
                location_id=loc_id,
                search_status="未搜索",
                available_items=item_instances, # Pass the list of ItemInstance objects
                present_characters=[]
            )
            # --- End of correction ---

            # 将位置添加到游戏状态
            game_state.location_states[loc_id] = location_status
            
    def _initialize_events_from_scenario(self, game_state: GameState, scenario: Scenario):
        """
        从剧本中初始化事件到游戏状态
        
        Args:
            game_state: 游戏状态对象
            scenario: 剧本对象
        """
        # 初始化事件字典
        game_state.event_instances = {}
        
        # 如果有events属性，加载事件信息
        if hasattr(scenario, 'events') and scenario.events:
            for event in scenario.events:
                # 创建事件实例
                event_instance = EventInstance(
                    instance_id=str(uuid.uuid4()),
                    event_id=getattr(event, 'event_id', str(uuid.uuid4())),
                    is_active=False,
                    is_completed=False,
                    related_character_ids=[],
                    revealed_to=[]
                )
                
                # 添加到事件实例字典
                game_state.event_instances[event_instance.instance_id] = event_instance

    def get_state(self) -> GameState:
        """
        获取当前游戏状态
        
        Returns:
            GameState: 当前游戏状态
        """
        return self.game_state
    
    def extract_state_changes(self, dm_narrative: str) -> StateChanges:
        """
        从DM叙述中提取状态变化
        
        Args:
            dm_narrative: DM叙述文本
            
        Returns:
            StateChanges: 提取的状态变化
        """
        pass
    
    def _apply_changes(self, changes: StateChanges) -> GameState:
        """
        应用状态变化
        
        Args:
            changes: 状态变化
            
        Returns:
            GameState: 更新后的游戏状态
        """
        pass # Placeholder for extract_state_changes

    def _apply_changes(self, changes: StateChanges) -> GameState:
        """
        应用状态变化 (此方法已废弃，保留以防万一，但逻辑应在 apply_consequences 中)

        Args:
            changes: 状态变化

        Returns:
            GameState: 更新后的游戏状态
        """
        self.logger.warning("_apply_changes 方法已废弃，请使用 apply_consequences。")
        return self.game_state # Return current state without changes

    def check_item(self, character_id: str, item_id: str, quantity: int = 1) -> ItemResult:
        """
        检查角色是否拥有指定数量的特定物品。

        Args:
            character_id: 角色ID
            item_id: 物品ID
            quantity: 需要检查的最小数量，默认为1

        Returns:
            ItemResult: 包含检查结果的对象
        """
        # --- 修改为从 game_state.characters 获取 ---
        if not self.game_state or character_id not in self.game_state.characters:
            self.logger.warning(f"check_item 失败：未找到角色 ID '{character_id}'。")
            return ItemResult(character_id=character_id, item_id=item_id, has_item=False, quantity=0)

        character_instance = self.game_state.characters[character_id]
        found_item: Optional[ItemInstance] = next((item for item in character_instance.items if item.item_id == item_id), None)

        if found_item and found_item.quantity >= quantity:
            self.logger.debug(f"物品检查成功：角色 '{character_id}' 拥有 {found_item.quantity} 个物品 '{item_id}' (需要 {quantity})。")
            return ItemResult(character_id=character_id, item_id=item_id, has_item=True, quantity=found_item.quantity)
        else:
            current_quantity = found_item.quantity if found_item else 0
            self.logger.debug(f"物品检查失败：角色 '{character_id}' 拥有 {current_quantity} 个物品 '{item_id}' (需要 {quantity})。")
            return ItemResult(character_id=character_id, item_id=item_id, has_item=False, quantity=current_quantity)

    def check_consistency(self, proposed_state: GameState) -> List[Inconsistency]:
        """
        检查状态一致性，确认DM生成的状态变更是否合法
        
        Args:
            proposed_state: 提议的游戏状态
            
        Returns:
            List[Inconsistency]: 不一致列表
        """
        # TODO: Implement consistency check logic
        self.logger.warning(f"check_consistency 方法尚未实现。")
        return []

    # --- 阶段三: 后果应用核心逻辑 ---

    async def apply_consequences(self, consequences: List[Consequence]):
        """
        应用一系列结构化的后果到当前游戏状态。

        Args:
            consequences: 后果对象的列表。

        Returns:
            List[str]: 应用后果产生的描述信息列表。
        """
        if not self.game_state:
            self.logger.error("无法应用后果：游戏状态未初始化。")
            return [] # Return empty list

        change_descriptions: List[str] = [] # List to store descriptions
        self.logger.info(f"开始应用 {len(consequences)} 条后果...")
        for i, cons in enumerate(consequences):
            self.logger.debug(f"应用后果 {i+1}/{len(consequences)}: {cons.model_dump_json()}")
            description = None # Initialize description for this consequence
            try:
                handler = self._get_consequence_handler(cons.type)
                if handler:
                    # Await the handler and get the description string
                    description = await handler(self.game_state, cons)
                else:
                    self.logger.warning(f"未找到后果类型 '{cons.type.value}' 的处理程序。")
            except Exception as e:
                self.logger.exception(f"应用后果时出错 ({cons.type.value}): {e}")

            # Add the description to the list if it's not None or empty
            if description:
                change_descriptions.append(description)

        # 更新最后修改时间
        self.game_state.last_updated = datetime.now()
        self.logger.info(f"所有后果应用完成，共产生 {len(change_descriptions)} 条状态变更描述。")
        return change_descriptions # Return the list of descriptions

    def _get_consequence_handler(self, consequence_type: ConsequenceType):
        """根据后果类型返回对应的处理方法。"""
        handlers = {
            ConsequenceType.UPDATE_ATTRIBUTE: self._apply_update_attribute,
            ConsequenceType.ADD_ITEM: self._apply_add_item,
            ConsequenceType.REMOVE_ITEM: self._apply_remove_item,
            ConsequenceType.CHANGE_RELATIONSHIP: self._apply_change_relationship,
            ConsequenceType.TRIGGER_EVENT: self._apply_trigger_event,
            ConsequenceType.SEND_MESSAGE: self._apply_send_message,
            # +++ Add handlers for new types +++
            ConsequenceType.UPDATE_CHARACTER_ATTRIBUTE: self._apply_update_character_attribute,
            ConsequenceType.UPDATE_CHARACTER_SKILL: self._apply_update_character_skill,
            ConsequenceType.CHANGE_LOCATION: self._apply_change_location, # +++ Add handler for location change +++
            # Add handlers for other types here
        }
        return handlers.get(consequence_type)

    async def _apply_update_attribute(self, game_state: GameState, cons: Consequence) -> Optional[str]:
        """处理 UPDATE_ATTRIBUTE 后果 (通用，可能用于地点等)。"""
        if not cons.target_entity_id or not cons.attribute_name:
            self.logger.warning(f"无效的 UPDATE_ATTRIBUTE 后果：缺少 target_entity_id 或 attribute_name。 {cons}")
            return None # Return None on failure

        target_obj = None
        # Find the target object (location status, item status, etc.)
        # --- 移除对 character_states 的检查 ---
        # if cons.target_entity_id in game_state.character_states:
        #     target_obj = game_state.character_states[cons.target_entity_id]
        if cons.target_entity_id in game_state.location_states:
            target_obj = game_state.location_states[cons.target_entity_id]
        # TODO: Add checks for items if they have attributes to update
        # elif cons.target_entity_id in game_state.item_instances: # Assuming items might have states
        #     target_obj = game_state.item_instances[cons.target_entity_id]
        else:
            self.logger.warning(f"UPDATE_ATTRIBUTE 失败：未找到目标实体 ID '{cons.target_entity_id}'。")
            return

        if not hasattr(target_obj, cons.attribute_name):
            self.logger.warning(f"UPDATE_ATTRIBUTE 失败：目标实体 '{cons.target_entity_id}' 没有属性 '{cons.attribute_name}'。")
            return

        try:
            # Handle different update operations (e.g., set, add, subtract)
            # Simple 'set' operation for now
            # More complex logic can be added based on 'cons.value' structure or metadata
            current_value = getattr(target_obj, cons.attribute_name)
            new_value = cons.value # Direct assignment for now

            # Example: Allow simple arithmetic operations if value is like {"op": "+=", "amount": 5}
            if isinstance(cons.value, dict) and "op" in cons.value and "amount" in cons.value:
                 op_str = cons.value["op"]
                 amount = cons.value["amount"]
                 ops = {"+=": add, "-=": sub, "*=": mul, "/=": truediv, "=": lambda x, y: y}
                 if op_str in ops and isinstance(current_value, (int, float)) and isinstance(amount, (int, float)):
                     new_value = ops[op_str](current_value, amount)
                 else:
                     self.logger.warning(f"UPDATE_ATTRIBUTE: 不支持的操作 '{op_str}' 或类型不匹配 ({type(current_value)}, {type(amount)}) for attribute '{cons.attribute_name}' on '{cons.target_entity_id}'. Performing direct set.")
                     new_value = amount # Fallback to setting the amount directly if op fails

            setattr(target_obj, cons.attribute_name, new_value)
            description = f"属性更新：实体 '{cons.target_entity_id}' 的属性 '{cons.attribute_name}' 已从 '{current_value}' 更新为 '{new_value}'。"
            self.logger.info(description)
            return description # Return the description string
        except Exception as e:
            self.logger.exception(f"更新属性 '{cons.attribute_name}' 时出错：{e}")
            return None # Return None on error

    async def _apply_add_item(self, game_state: GameState, cons: Consequence):
        """处理 ADD_ITEM 后果。"""
        if not cons.target_entity_id or not cons.item_id:
            self.logger.warning(f"无效的 ADD_ITEM 后果：缺少 target_entity_id 或 item_id。 {cons}")
            return

        quantity = cons.value if isinstance(cons.value, int) and cons.value > 0 else 1

        # Add to character inventory
        if cons.target_entity_id in game_state.characters: # Use game_state.characters
            character_instance = game_state.characters[cons.target_entity_id] # Get CharacterInstance
            # Find if item already exists in CharacterInstance.items
            existing_item: Optional[ItemInstance] = next((item for item in character_instance.items if item.item_id == cons.item_id), None)
            if existing_item:
                existing_item.quantity += quantity
                description = f"物品更新：角色 '{cons.target_entity_id}' ({character_instance.name}) 的物品 '{cons.item_id}' 数量增加 {quantity}，当前数量: {existing_item.quantity}。"
                self.logger.info(description)
                return description # Return the description string
            else:
                # Check if item definition exists in scenario (optional but good practice)
                item_def = game_state.scenario.items.get(cons.item_id) if game_state.scenario and game_state.scenario.items else None
                if not item_def:
                     self.logger.warning(f"ADD_ITEM 警告：尝试添加未在剧本中定义的物品 '{cons.item_id}' 到角色 '{cons.target_entity_id}' ({character_instance.name})。")
                     # Decide whether to proceed or fail. Let's proceed for now.

                new_item = ItemInstance(item_id=cons.item_id, quantity=quantity, name=item_def.name if item_def else cons.item_id)
                character_instance.items.append(new_item) # Add to CharacterInstance.items
                description = f"物品添加：向角色 '{cons.target_entity_id}' ({character_instance.name}) 添加了 {quantity} 个物品 '{cons.item_id}'。"
                self.logger.info(description)
                return description # Return the description string


        # Add to location
        elif cons.target_entity_id in game_state.location_states:
            location_state = game_state.location_states[cons.target_entity_id]
            existing_item: Optional[ItemInstance] = next((item for item in location_state.available_items if item.item_id == cons.item_id), None)
            if existing_item:
                existing_item.quantity += quantity
                self.logger.info(f"物品更新：地点 '{cons.target_entity_id}' 的物品 '{cons.item_id}' 数量增加 {quantity}，当前数量: {existing_item.quantity}。")
            else:
                item_def = game_state.scenario.items.get(cons.item_id) if game_state.scenario and game_state.scenario.items else None
                if not item_def:
                     self.logger.warning(f"ADD_ITEM 警告：尝试添加未在剧本中定义的物品 '{cons.item_id}' 到地点 '{cons.target_entity_id}'。")

                new_item = ItemInstance(item_id=cons.item_id, quantity=quantity, name=item_def.name if item_def else cons.item_id)
                location_state.available_items.append(new_item)
                description = f"物品添加：向地点 '{cons.target_entity_id}' 添加了 {quantity} 个物品 '{cons.item_id}'。"
                self.logger.info(description)
                return description # Return the description string

        else:
            self.logger.warning(f"ADD_ITEM 失败：未找到目标实体 ID '{cons.target_entity_id}' (既不是角色也不是地点)。")
            return None # Return None on failure


    async def _apply_remove_item(self, game_state: GameState, cons: Consequence) -> Optional[str]:
        """处理 REMOVE_ITEM 后果。"""
        if not cons.target_entity_id or not cons.item_id:
            self.logger.warning(f"无效的 REMOVE_ITEM 后果：缺少 target_entity_id 或 item_id。 {cons}")
            return None # Return None on failure

        quantity_to_remove = cons.value if isinstance(cons.value, int) and cons.value > 0 else 1

        # --- 修改为操作 CharacterInstance.items ---
        if cons.target_entity_id in game_state.characters:
            character_instance = game_state.characters[cons.target_entity_id]
            item_to_remove: Optional[ItemInstance] = next((item for item in character_instance.items if item.item_id == cons.item_id), None)
            if item_to_remove:
                if item_to_remove.quantity >= quantity_to_remove:
                    original_quantity = item_to_remove.quantity
                    item_to_remove.quantity -= quantity_to_remove
                    description = f"物品移除：从角色 '{cons.target_entity_id}' ({character_instance.name}) 移除 {quantity_to_remove} 个物品 '{cons.item_id}'，剩余数量: {item_to_remove.quantity}。"
                    self.logger.info(description)

                    description_to_return = description # Start with the base description
                    if item_to_remove.quantity <= 0: # Check if quantity is zero or less
                        character_instance.items.remove(item_to_remove)
                        description_removed = f"物品移除：角色 '{cons.target_entity_id}' ({character_instance.name}) 的物品 '{cons.item_id}' 已完全移除。"
                        self.logger.info(description_removed)
                        description_to_return = description_removed # Update return value if fully removed

                    return description_to_return # Return the appropriate description

                else:
                    self.logger.warning(f"REMOVE_ITEM 失败：角色 '{cons.target_entity_id}' ({character_instance.name}) 物品 '{cons.item_id}' 数量不足 ({item_to_remove.quantity} < {quantity_to_remove})。")
                    return None # Return None on failure
            else:
                self.logger.warning(f"REMOVE_ITEM 失败：角色 '{cons.target_entity_id}' ({character_instance.name}) 没有物品 '{cons.item_id}'。")
                return None # Return None on failure

        # Remove from location (保持不变)
        elif cons.target_entity_id in game_state.location_states:
            location_state = game_state.location_states[cons.target_entity_id]
            item_to_remove: Optional[ItemInstance] = next((item for item in location_state.available_items if item.item_id == cons.item_id), None)
            if item_to_remove:
                if item_to_remove.quantity >= quantity_to_remove:
                    original_quantity = item_to_remove.quantity
                    item_to_remove.quantity -= quantity_to_remove
                    description = f"物品移除：从地点 '{cons.target_entity_id}' 移除 {quantity_to_remove} 个物品 '{cons.item_id}'，剩余数量: {item_to_remove.quantity}。"
                    self.logger.info(description)

                    description_to_return = description # Start with the base description
                    if item_to_remove.quantity == 0:
                        location_state.available_items.remove(item_to_remove)
                        description_removed = f"物品移除：地点 '{cons.target_entity_id}' 的物品 '{cons.item_id}' 已完全移除。"
                        self.logger.info(description_removed)
                        description_to_return = description_removed # Update return value if fully removed

                    return description_to_return # Return the appropriate description
                else:
                    self.logger.warning(f"REMOVE_ITEM 失败：地点 '{cons.target_entity_id}' 物品 '{cons.item_id}' 数量不足 ({item_to_remove.quantity} < {quantity_to_remove})。")
                    return None # Return None on failure
            else:
                self.logger.warning(f"REMOVE_ITEM 失败：地点 '{cons.target_entity_id}' 没有物品 '{cons.item_id}'。")
        else:
            self.logger.warning(f"REMOVE_ITEM 失败：未找到目标实体 ID '{cons.target_entity_id}' (既不是角色也不是地点)。")


    async def _apply_change_relationship(self, game_state: GameState, cons: Consequence):
        """处理 CHANGE_RELATIONSHIP 后果。"""
        # TODO: Implement logic
        self.logger.warning(f"后果类型 'CHANGE_RELATIONSHIP' 的处理程序尚未实现。")
        pass

    async def _apply_trigger_event(self, game_state: GameState, cons: Consequence):
        """处理 TRIGGER_EVENT 后果。"""
        # TODO: Implement logic - likely involves adding event_id to active_event_ids or similar
        self.logger.warning(f"后果类型 'TRIGGER_EVENT' 的处理程序尚未实现。")
        pass

    async def _apply_send_message(self, game_state: GameState, cons: Consequence):
        """处理 SEND_MESSAGE 后果。"""
        # TODO: Implement logic - likely involves using MessageDispatcher
        self.logger.warning(f"后果类型 'SEND_MESSAGE' 的处理程序尚未实现。")
        return None # Return None

    # +++ 新增处理角色属性/技能的方法 +++
    async def _apply_update_character_attribute(self, game_state: GameState, cons: Consequence) -> Optional[str]:
        """处理 UPDATE_CHARACTER_ATTRIBUTE 后果。"""
        if not cons.target_entity_id or not cons.attribute_name or cons.value is None:
            self.logger.warning(f"无效的 UPDATE_CHARACTER_ATTRIBUTE 后果：缺少 target_entity_id, attribute_name 或 value。 {cons}")
            return None

        character_instance = game_state.characters.get(cons.target_entity_id)
        if not character_instance:
            self.logger.warning(f"UPDATE_CHARACTER_ATTRIBUTE 失败：未找到角色 ID '{cons.target_entity_id}'。")
            return None

        if not hasattr(character_instance.attributes, cons.attribute_name):
            self.logger.warning(f"UPDATE_CHARACTER_ATTRIBUTE 失败：角色 '{cons.target_entity_id}' 的属性集没有属性 '{cons.attribute_name}'。")
            return None

        try:
            current_value = getattr(character_instance.attributes, cons.attribute_name)
            change_value = cons.value
            new_value = current_value

            # Assume value is the change amount (e.g., +1, -2)
            if isinstance(change_value, (int, float)) and isinstance(current_value, (int, float)):
                new_value = current_value + change_value
            else:
                self.logger.warning(f"UPDATE_CHARACTER_ATTRIBUTE: 无法应用变化值 '{change_value}' (类型: {type(change_value)}) 到属性 '{cons.attribute_name}' (当前值: {current_value}, 类型: {type(current_value)})。将尝试直接设置。")
                # Fallback: try direct assignment if types mismatch or value isn't numeric change
                new_value = change_value

            setattr(character_instance.attributes, cons.attribute_name, new_value)
            description = f"角色属性更新：角色 '{cons.target_entity_id}' ({character_instance.name}) 的属性 '{cons.attribute_name}' 从 '{current_value}' 更新为 '{new_value}' (变化: {change_value})。"
            self.logger.info(description)
            return description
        except Exception as e:
            self.logger.exception(f"更新角色属性 '{cons.attribute_name}' 时出错：{e}")
            return None

    async def _apply_update_character_skill(self, game_state: GameState, cons: Consequence) -> Optional[str]:
        """处理 UPDATE_CHARACTER_SKILL 后果。"""
        if not cons.target_entity_id or not cons.skill_name or cons.value is None:
            self.logger.warning(f"无效的 UPDATE_CHARACTER_SKILL 后果：缺少 target_entity_id, skill_name 或 value。 {cons}")
            return None

        character_instance = game_state.characters.get(cons.target_entity_id)
        if not character_instance:
            self.logger.warning(f"UPDATE_CHARACTER_SKILL 失败：未找到角色 ID '{cons.target_entity_id}'。")
            return None

        if not hasattr(character_instance.skills, cons.skill_name):
            self.logger.warning(f"UPDATE_CHARACTER_SKILL 失败：角色 '{cons.target_entity_id}' 的技能集没有技能 '{cons.skill_name}'。")
            return None

        try:
            current_value = getattr(character_instance.skills, cons.skill_name)
            change_value = cons.value
            new_value = current_value

            # Assume value is the change amount (e.g., +1, -2)
            if isinstance(change_value, (int, float)) and isinstance(current_value, (int, float)):
                new_value = current_value + change_value
            else:
                self.logger.warning(f"UPDATE_CHARACTER_SKILL: 无法应用变化值 '{change_value}' (类型: {type(change_value)}) 到技能 '{cons.skill_name}' (当前值: {current_value}, 类型: {type(current_value)})。将尝试直接设置。")
                new_value = change_value # Fallback

            setattr(character_instance.skills, cons.skill_name, new_value)
            description = f"角色技能更新：角色 '{cons.target_entity_id}' ({character_instance.name}) 的技能 '{cons.skill_name}' 从 '{current_value}' 更新为 '{new_value}' (变化: {change_value})。"
            self.logger.info(description)
            return description
        except Exception as e:
            self.logger.exception(f"更新角色技能 '{cons.skill_name}' 时出错：{e}")
            return None

    async def _apply_change_location(self, game_state: GameState, cons: Consequence) -> Optional[str]:
        """处理 CHANGE_LOCATION 后果。"""
        if not cons.target_entity_id or not cons.value or not isinstance(cons.value, str):
            self.logger.warning(f"无效的 CHANGE_LOCATION 后果：缺少 target_entity_id 或 value 不是字符串。 {cons}")
            return None

        character_instance = game_state.characters.get(cons.target_entity_id)
        if not character_instance:
            self.logger.warning(f"CHANGE_LOCATION 失败：未找到角色 ID '{cons.target_entity_id}'。")
            return None

        new_location_id = cons.value
        # Optional: Validate if new_location_id exists in game_state.location_states
        if new_location_id not in game_state.location_states:
             self.logger.warning(f"CHANGE_LOCATION 警告：目标地点 ID '{new_location_id}' 不存在于 location_states 中。")
             # Decide whether to proceed or fail. Let's proceed for now.

        try:
            old_location = character_instance.location
            character_instance.location = new_location_id
            description = f"角色位置更新：角色 '{cons.target_entity_id}' ({character_instance.name}) 的位置从 '{old_location}' 更新为 '{new_location_id}'。"
            self.logger.info(description)

            # --- 更新旧地点和新地点的 present_characters ---
            # Remove from old location
            if old_location and old_location in game_state.location_states:
                if cons.target_entity_id in game_state.location_states[old_location].present_characters:
                    game_state.location_states[old_location].present_characters.remove(cons.target_entity_id)
                    self.logger.debug(f"已将角色 '{cons.target_entity_id}' 从地点 '{old_location}' 的 present_characters 移除。")
            # Add to new location
            if new_location_id in game_state.location_states:
                if cons.target_entity_id not in game_state.location_states[new_location_id].present_characters:
                    game_state.location_states[new_location_id].present_characters.append(cons.target_entity_id)
                    self.logger.debug(f"已将角色 '{cons.target_entity_id}' 添加到地点 '{new_location_id}' 的 present_characters。")
            # --- 结束更新 present_characters ---

            return description
        except Exception as e:
            self.logger.exception(f"更新角色 '{cons.target_entity_id}' 位置时出错：{e}")
            return None

    # --- 移除旧的 update_state 方法 ---
    # def update_state(self, state_changes: Dict[str, Any]) -> GameState:
    #     """
    #     直接根据裁判代理提供的状态变化字典更新游戏状态。
    #     (此方法已废弃，请使用 apply_consequences)
    #     """
    #     # ... (旧代码已注释掉) ...
    #     pass

    # --- 阶段三: 游戏进程管理方法 ---

    def check_stage_completion(self) -> bool:
        """
        检查当前阶段的完成条件是否满足。
        注意：此方法仅检查条件，不执行推进。
        """
        if not self.game_state:
            self.logger.warning("无法检查阶段完成条件：游戏状态未初始化。")
            return False

        current_stage_id = self.game_state.progress.current_stage_id
        # 使用 ScenarioManager 获取阶段信息
        current_stage: Optional[StoryStage] = self.scenario_manager.get_stage_info(current_stage_id)

        if not current_stage:
            self.logger.warning(f"无法检查阶段完成条件：通过 ScenarioManager 未找到当前阶段 ID '{current_stage_id}'。")
            return False

        if not current_stage.completion_criteria:
            self.logger.info(f"阶段 '{current_stage_id}' 没有定义完成条件，视为未完成。")
            return False

        self.logger.debug(f"开始检查阶段 '{current_stage_id}' 的完成条件...")
        all_conditions_met = True
        for condition in current_stage.completion_criteria:
            # TODO: Implement more sophisticated condition checking logic
            # This is a very basic example assuming simple flag checks or item checks
            condition_met = False
            condition_type = condition.get('type') # Use .get() for safety
            condition_details = condition.get('details', {}) # Use .get() with default empty dict
            condition_description = condition.get('description', '未知条件') # Use .get() with default

            if condition_type == "flag_set":
                flag_name = condition_details.get("flag_name")
                required_value = condition_details.get("value", True)
                # Ensure flags attribute exists before accessing
                if flag_name and hasattr(self.game_state, 'flags') and self.game_state.flags.get(flag_name) == required_value:
                    condition_met = True
            elif condition_type == "item_possession":
                char_id = condition_details.get("character_id")
                item_id = condition_details.get("item_id")
                quantity = condition_details.get("quantity", 1)
                if char_id and item_id:
                     # Use the already implemented check_item method
                     item_result = self.check_item(char_id, item_id, quantity)
                     if item_result.has_item:
                         condition_met = True
            # Add more condition types (e.g., attribute_check, location_reached)
            else:
                self.logger.warning(f"未知的阶段完成条件类型: {condition_type}")

            if not condition_met:
                self.logger.debug(f"阶段 '{current_stage_id}' 完成条件未满足: {condition_description} (类型: {condition_type})")
                all_conditions_met = False
                break # No need to check further if one condition fails
            else:
                 self.logger.debug(f"阶段 '{current_stage_id}' 完成条件已满足: {condition_description} (类型: {condition_type})")


        if all_conditions_met:
            self.logger.info(f"阶段 '{current_stage_id}' 的所有完成条件均已满足。")
        return all_conditions_met

    def advance_stage(self) -> bool:
        """
        如果当前阶段已完成，则查找并推进到下一个阶段。
        同时更新活动事件列表。

        Returns:
            bool: 如果成功推进到下一阶段则返回 True，否则返回 False。
        """
        if not self.check_stage_completion():
            self.logger.debug("advance_stage 调用：当前阶段未完成，无法推进。")
            return False

        if not self.game_state:
            self.logger.error("无法推进阶段：游戏状态未初始化。")
            return False

        current_chapter_id = self.game_state.progress.current_chapter_id
        current_section_id = self.game_state.progress.current_section_id
        current_stage_id = self.game_state.progress.current_stage_id

        # 使用 ScenarioManager 查找下一个阶段
        next_stage_id, next_section_id, next_chapter_id = self.scenario_manager.find_next_stage(
            current_stage_id, current_section_id, current_chapter_id
        )

        if next_stage_id:
            old_stage_id = self.game_state.progress.current_stage_id
            self.game_state.progress.current_stage_id = next_stage_id
            self.game_state.progress.current_section_id = next_section_id
            self.game_state.progress.current_chapter_id = next_chapter_id
            self.logger.info(f"游戏阶段已从 '{old_stage_id}' 推进到 '{next_stage_id}' (章节: {next_chapter_id}, 小节: {next_section_id})。")
            # 阶段推进后，更新活动事件
            self.update_active_events()
            return True
        else:
            # TODO: Handle game completion scenario
            self.logger.info(f"当前阶段 '{current_stage_id}' 是最后一个阶段，游戏可能已完成。")
            # Potentially set a game completion flag in game_state
            return False

    def update_active_events(self):
        """
        根据当前阶段更新活动事件列表 (game_state.active_event_ids)。
        事件的激活通常由其 `activation_stage_id` 决定。
        """
        if not self.game_state or not self.game_state.scenario or not self.game_state.scenario.events:
            self.logger.warning("无法更新活动事件：游戏状态或剧本事件列表缺失。")
            if self.game_state: self.game_state.active_event_ids = [] # Clear active events if state exists but scenario doesn't
            return

        current_stage_id = self.game_state.progress.current_stage_id
        new_active_event_ids = []

        self.logger.debug(f"开始根据当前阶段 '{current_stage_id}' 更新活动事件...")
        for event in self.game_state.scenario.events:
            # 检查事件是否应该在当前阶段激活
            # 假设事件模型有一个 'activation_stage_id' 字段
            activation_stage = getattr(event, 'activation_stage_id', None)
            is_active_in_current_stage = (activation_stage == current_stage_id)

            # 检查事件是否已经完成 (假设事件实例有 is_completed 标志)
            event_instance = self.game_state.event_instances.get(event.event_id) # Assuming instance ID matches event ID for simplicity here
            is_completed = getattr(event_instance, 'is_completed', False) if event_instance else False

            # 检查事件是否是一次性的 (假设事件模型有 'is_repeatable' 字段，默认为 False)
            is_repeatable = getattr(event, 'is_repeatable', False)

            if is_active_in_current_stage and (not is_completed or is_repeatable):
                new_active_event_ids.append(event.event_id)
                self.logger.debug(f"事件 '{event.event_id}' ({event.name}) 在阶段 '{current_stage_id}' 激活。")
            # else:
            #     if not is_active_in_current_stage:
            #         self.logger.debug(f"事件 '{event.event_id}' 在阶段 '{current_stage_id}' 不激活 (激活阶段: {activation_stage})。")
            #     elif is_completed and not is_repeatable:
            #         self.logger.debug(f"事件 '{event.event_id}' 已完成且不可重复，不激活。")


        old_active_ids = set(self.game_state.active_event_ids)
        new_active_ids = set(new_active_event_ids)

        if old_active_ids != new_active_ids:
            self.game_state.active_event_ids = new_active_event_ids
            self.logger.info(f"活动事件列表已更新为: {self.game_state.active_event_ids}")
        else:
            self.logger.debug("活动事件列表无需更新。")


    # --- 其他辅助方法 ---

    def get_characters_at_location(self, location_id: str) -> List[str]:
        """获取在指定位置的角色ID列表"""
        # --- 修改为从 game_state.characters 获取 ---
        if not self.game_state or not self.game_state.characters:
            return []
        return [char_id for char_id, char_instance in self.game_state.characters.items()
                if char_instance.location == location_id]
