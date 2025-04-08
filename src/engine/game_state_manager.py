import json # Import json for saving/loading
import os   # Import os for path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging # Add logging import
# from operator import add, sub, mul, truediv # No longer needed here
import copy # +++ Import copy for deepcopy +++

from src.models.game_state_models import (
    GameState, CharacterInstance,
    EnvironmentStatus, EventInstance, ProgressStatus,
    LocationStatus, ItemInstance # Add ItemInstance
)
from src.models.scenario_models import Scenario, StoryStage # Import StoryStage
from src.models.context_models import StateChanges, Inconsistency
from src.models.action_models import ItemResult
# Import the new union type and specific types if needed
from src.models.consequence_models import AnyConsequence, ConsequenceType
import uuid # Import uuid for message IDs
from datetime import datetime # Import datetime for timestamps

from src.engine.scenario_manager import ScenarioManager
# +++ Import the handler getter function +++
from src.engine.consequence_handlers import get_handler
# +++ Import the handler getter function +++
from src.engine.consequence_handlers import get_handler


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
        self.game_state: Optional[GameState] = initial_state # Add type hint
        self.scenario_manager = scenario_manager # Store the scenario manager
        # self.message_dispatcher = message_dispatcher # Removed dispatcher dependency
        self.logger = logging.getLogger("GameStateManager") # Add logger
        self.round_snapshots: Dict[int, GameState] = {} # +++ Add dictionary to store snapshots +++

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
            # scenario=scenario, # Removed direct scenario reference
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
                        # Use ScenarioManager to get item definition
                        item_definition = self.scenario_manager.get_item_info(item_id)
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

    async def apply_consequences(self, consequences: List[AnyConsequence]) -> List[str]: # Updated type hint
        """
        应用一系列结构化的后果到当前游戏状态，使用注册的 Handler 处理。

        Args:
            consequences: 后果对象的列表。

        Returns:
            List[str]: 应用后果产生的描述信息列表 (由 Handler 返回)。
        """
        if not self.game_state:
            self.logger.error("无法应用后果：游戏状态未初始化。")
            return []

        change_descriptions: List[str] = []
        self.logger.info(f"开始应用 {len(consequences)} 条后果...")

        for i, cons in enumerate(consequences):
            self.logger.debug(f"处理后果 {i+1}/{len(consequences)}: {cons.type.value} - {cons.target_entity_id}")
            description = None
            handler = None
            try:
                # 获取并实例化对应的 Handler
                handler = get_handler(cons.type)
                if handler:
                    # 调用 Handler 的 apply 方法，该方法负责应用和记录
                    description = await handler.apply(cons, self.game_state)
                    if description: # Handler 成功应用并返回了描述
                         change_descriptions.append(description)
                    # else: Handler 应用失败或无描述返回，Handler 内部应已记录失败
                else:
                    self.logger.warning(f"未找到后果类型 '{cons.type.value}' 的处理程序。跳过此后果。")
                    # 可以在这里创建一个通用的失败记录，如果需要的话
                    # self._create_generic_failure_record(cons, "未找到处理器")

            except Exception as e:
                # 捕获 Handler 执行期间的意外错误
                self.logger.exception(f"应用后果 '{cons.type.value}' 时发生意外错误: {e}")
                # 尝试让 Handler (如果已实例化) 记录失败，否则记录通用失败
                # if handler and hasattr(handler, '_create_record'):
                #     try:
                #         # Assuming _create_record is synchronous and part of base class
                #         handler._create_record(cons, self.game_state, success=False, description=f"应用时发生意外错误: {e}")
                #     except Exception as record_e:
                #         self.logger.error(f"尝试记录意外错误时再次出错: {record_e}")
                # else:
                #      self._create_generic_failure_record(cons, f"应用时发生意外错误: {e}")


        # 更新最后修改时间
        if consequences: # Only update if there were consequences to apply
             self.game_state.last_updated = datetime.now()

        self.logger.info(f"后果应用流程完成。共处理 {len(consequences)} 条，产生 {len(change_descriptions)} 条有效状态变更描述。")
        # 注意：实际记录的 AppliedConsequenceRecord 数量可能与 len(change_descriptions) 不同，
        # 因为 Handler 可能在失败时也创建记录。
        return change_descriptions

    async def apply_single_consequence_immediately(self, consequence: AnyConsequence, game_state: GameState) -> Optional[str]:
        """
        立即应用单个后果到游戏状态，通过对应的 Handler 处理。
        主要用于 Agent 内部评估产生的、需要即时反馈的后果（如关系变化）。

        Args:
            consequence: 要应用的后果对象。
            game_state: 当前游戏状态。

        Returns:
            Optional[str]: 如果 Handler 成功应用并返回描述，则返回描述字符串，否则返回 None。
        """
        if not game_state: # Check the passed game_state argument
            self.logger.error("无法立即应用后果：传入的游戏状态为 None。")
            return None

        # Use consequence.type directly as it's already a string
        self.logger.info(f"尝试立即应用单个后果: {consequence.type} - {consequence.target_entity_id}")
        description = None
        handler = None
        try:
            handler = get_handler(consequence.type)
            if handler:
                # 调用 Handler 的 apply 方法
                description = await handler.apply(consequence, game_state) # Pass the provided game_state
                if description:
                    self.logger.info(f"立即应用后果成功: {description}")
                    # 注意：这里应用的是传入的 game_state，如果需要同步到 self.game_state，
                    # 且 game_state 不是 self.game_state 的引用，则需要额外处理。
                    # 但通常 Agent 调用时会传入 self.game_state_manager.get_state()。
                    # 同时，Handler 内部应该已经修改了传入的 game_state 对象。
                    # Handler 内部也负责记录 AppliedConsequenceRecord 到 game_state.current_round_applied_consequences
                else:
                    self.logger.warning(f"立即应用后果 '{consequence.type.value}' 时，Handler 未返回描述 (可能应用失败或无描述)。")
            else:
                self.logger.warning(f"未找到后果类型 '{consequence.type.value}' 的处理程序。无法立即应用。")

        except Exception as e:
            self.logger.exception(f"立即应用后果 '{consequence.type.value}' 时发生意外错误: {e}")
            # 可以在这里尝试记录失败，如果 Handler 支持的话

        # 更新最后修改时间 (即使只应用一个后果也更新)
        game_state.last_updated = datetime.now() # Update the passed game_state

        return description


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
        # Get scenario from ScenarioManager
        scenario = self.scenario_manager.get_current_scenario()
        if not self.game_state or not scenario or not scenario.events:
            self.logger.warning("无法更新活动事件：游戏状态或剧本/事件列表缺失。")
            if self.game_state: self.game_state.active_event_ids = [] # Clear active events if state exists but scenario doesn't
            return

        current_stage_id = self.game_state.progress.current_stage_id
        new_active_event_ids = []

        self.logger.debug(f"开始根据当前阶段 '{current_stage_id}' 更新活动事件...")
        # Iterate through events from the scenario obtained from the manager
        for event in scenario.events:
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

    # +++ 新增保存和加载状态的方法 +++
    def save_state(self, file_path: str):
        """
        将当前游戏状态（不含聊天记录）保存到 JSON 文件。

        Args:
            file_path: 保存文件的路径。
        """
        if not self.game_state:
            self.logger.error("无法保存状态：游戏状态未初始化。")
            return

        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            # 使用 Pydantic 的 model_dump_json 进行序列化
            state_json = self.game_state.model_dump_json(indent=4)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(state_json)
            self.logger.info(f"游戏状态已保存到: {file_path}")
        except Exception as e:
            self.logger.exception(f"保存游戏状态到 '{file_path}' 时出错: {e}")

    # +++ 新增快照管理方法 +++
    def create_snapshot(self) -> Optional[GameState]:
        """
        创建当前游戏状态的深拷贝快照。

        Returns:
            Optional[GameState]: 游戏状态的深拷贝，如果当前状态不存在则返回 None。
        """
        if not self.game_state:
            self.logger.error("无法创建快照：游戏状态未初始化。")
            return None
        try:
            # 使用 copy.deepcopy 确保完全独立
            snapshot = copy.deepcopy(self.game_state)
            self.logger.debug(f"已为回合 {snapshot.round_number} 创建游戏状态快照。")
            return snapshot
        except Exception as e:
            self.logger.exception(f"创建游戏状态快照时出错: {e}")
            return None

    def store_snapshot(self, round_number: int, snapshot: GameState):
        """
        将游戏状态快照存储在内存中。

        Args:
            round_number: 快照对应的回合数。
            snapshot: 要存储的游戏状态快照。
        """
        self.round_snapshots[round_number] = snapshot
        self.logger.info(f"已存储回合 {round_number} 的游戏状态快照。")

    def get_snapshot(self, round_number: int) -> Optional[GameState]:
        """
        获取指定回合的游戏状态快照。

        Args:
            round_number: 要获取快照的回合数。

        Returns:
            Optional[GameState]: 指定回合的快照，如果不存在则返回 None。
        """
        snapshot = self.round_snapshots.get(round_number)
        if snapshot:
            self.logger.debug(f"已检索到回合 {round_number} 的游戏状态快照。")
        else:
            self.logger.warning(f"未找到回合 {round_number} 的游戏状态快照。")
        return snapshot

    def load_state(self, file_path: str) -> bool:
        """
        从 JSON 文件加载游戏状态（不含聊天记录）。

        Args:
            file_path: 加载文件的路径。

        Returns:
            bool: 如果加载成功则返回 True，否则返回 False。
        """
        if not os.path.exists(file_path):
            self.logger.error(f"加载状态失败：文件未找到 '{file_path}'。")
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                state_json = f.read()
            # 使用 Pydantic 的 model_validate_json 进行反序列化和验证
            loaded_state = GameState.model_validate_json(state_json)
            
            # 验证加载的 scenario_id 是否与 ScenarioManager 中的一致
            current_scenario = self.scenario_manager.get_current_scenario()
            if not current_scenario or loaded_state.scenario_id != current_scenario.story_info.id:
                 self.logger.warning(f"加载状态警告：加载的剧本ID '{loaded_state.scenario_id}' 与 ScenarioManager 当前加载的剧本ID '{current_scenario.story_info.id if current_scenario else 'None'}' 不匹配。请确保加载了正确的剧本。")
                 # 可以选择在这里停止加载或继续，取决于设计决策
                 # return False # Example: Stop loading if scenario mismatch

            self.game_state = loaded_state
            self.logger.info(f"游戏状态已从 '{file_path}' 加载。")
            # 加载后可能需要重新初始化某些运行时状态或检查一致性
            # 例如，重新计算活动事件
            self.update_active_events()
            return True
        except json.JSONDecodeError:
            self.logger.error(f"加载状态失败：文件 '{file_path}' 格式错误。")
            return False
        except Exception as e: # Catch Pydantic validation errors and others
            self.logger.exception(f"加载游戏状态从 '{file_path}' 时发生错误: {e}")
            return False
