from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from src.models.game_state_models import (
    GameState, CharacterInstance, CharacterStatus, 
    EnvironmentStatus, EventInstance, ProgressStatus,
    LocationStatus, ItemStatus
)
from src.models.scenario_models import Scenario
from src.models.context_models import StateChanges, Inconsistency, StateUpdateRequest
from src.models.action_models import ItemQuery, ItemResult

class GameStateManager:
    """
    游戏状态管理器类，负责维护游戏状态的一致性、解析DM叙述中的状态变化、提供状态查询。
    """
    
    def __init__(self, initial_state: Optional[GameState] = None):
        """
        初始化游戏状态管理器
        
        Args:
            initial_state: 初始游戏状态，如果为None则创建新状态
        """
        self.game_state = initial_state
        self.state_history = []
    
    def initialize_game_state(self, scenario: Scenario) -> GameState:
        """
        初始化游戏状态
        
        Args:
            scenario: 要使用的剧本
            
        Returns:
            GameState: 初始化的游戏状态
        """
        # 创建基本游戏状态
        game_id = str(uuid.uuid4())
        
        # 确定初始地点
        initial_location_id = None
        if hasattr(scenario, 'locations') and scenario.locations:
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
        # 如果剧本中有故事结构，则使用其中的第一个章节、小节、阶段
        current_chapter_id = "chapter_1"
        current_section_id = "section_1"
        current_stage_id = "stage_1"
        
        if (hasattr(scenario, 'story_structure') and 
            scenario.story_structure and 
            scenario.story_structure.chapters):
            
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
            scenario=scenario,
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
        game_state.character_states = {}
        
        # 从剧本中加载角色
        if hasattr(scenario, 'characters') and scenario.characters:
            for char_id, character_info in scenario.characters.items():
                # 获取公开身份
                public_identity = getattr(character_info, 'public_identity', f"角色_{char_id}")
                
                # 确定初始位置
                initial_location = getattr(game_state.environment, 'current_location_id', "main_location")
                
                character_id=f"char_{uuid.uuid4().hex[:8]}"

                # 创建角色状态
                character_status = CharacterStatus(
                    character_id=character_id,
                    location=initial_location,
                    health=100,  # 默认值
                    items=[],  # 初始无物品
                    conditions=[],
                    relationships={},
                    known_information=[],
                    goal="",
                    plans=""
                )

                # 创建角色引用，直接嵌套状态
                character_ref = CharacterInstance(
                    character_id=character_id,
                    public_identity=public_identity,
                    name=char_id,
                    player_controlled=False,  # 默认为NPC
                    status=character_status,  # 直接嵌套状态
                )
                
                # 将角色添加到游戏状态
                game_state.characters[character_id] = character_ref
                game_state.character_states[character_id] = character_status
    
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
            # 创建位置状态
            location_status = LocationStatus(
                location_id=loc_id,
                search_status="未搜索",
                available_items=getattr(location_info, 'available_items', []),
                present_characters=[]
            )
            
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
        pass
    
    def check_item(self, player_id: str, item_id: str) -> ItemResult:
        """
        检查玩家物品状态
        
        Args:
            player_id: 玩家ID
            item_id: 物品ID
            
        Returns:
            ItemResult: 物品查询结果
        """
        pass
    
    def check_consistency(self, proposed_state: GameState) -> List[Inconsistency]:
        """
        检查状态一致性，确认DM生成的状态变更是否合法
        
        Args:
            proposed_state: 提议的游戏状态
            
        Returns:
            List[Inconsistency]: 不一致列表
        """
        pass

    def update_state(self, update_request: StateUpdateRequest) -> GameState:
        """
        更新游戏状态
        
        Args:
            update_request: 状态更新请求
            
        Returns:
            GameState: 更新后的游戏状态
        """
        # 提取状态变化
        changes = self.extract_state_changes(update_request.dm_narrative)
        
        # 应用状态变化
        updated_state = self._apply_changes(changes)
        
        # 检查一致性
        inconsistencies = self.check_consistency(updated_state)
        if inconsistencies:
            # 处理不一致情况
            pass
        
        return updated_state

    def get_characters_at_location(self, location_id: str) -> List[str]:
        """获取在指定位置的角色ID列表"""
        return [char_id for char_id, char_status in self.game_state.character_states.items() 
                if char_status.location == location_id]
