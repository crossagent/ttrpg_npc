from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from src.models.game_state_models import GameState, GamePhase, CharacterInstance, CharacterStatus, EnvironmentStatus
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
        scenario_id = getattr(scenario, 'scenario_id', "default")
        
        # 确定初始地点
        initial_location_id = None
        if hasattr(scenario, 'locations') and scenario.locations:
            # 使用第一个地点作为初始位置
            initial_location_id = next(iter(scenario.locations.keys()))
        elif hasattr(scenario, 'story_info') and hasattr(scenario.story_info, 'locations_description'):
            # 兼容：从locations_description获取第一个地点
            if scenario.story_info.locations_description:
                initial_location_id = next(iter(scenario.story_info.locations_description.keys()))
        
        # 如果没有找到任何地点，使用默认位置
        if not initial_location_id:
            initial_location_id = "main_location"
        
        # 创建环境状态
        environment = EnvironmentStatus(
            current_location_id=initial_location_id,
            time=datetime.now(),
            weather="晴朗"
        )
        
        # 创建游戏状态
        game_state = GameState(
            game_id=game_id,
            scenario_id=scenario_id,
            environment=environment
        )
        
        # 存储游戏状态
        self.game_state = game_state
        
        # 初始化角色
        self._initialize_characters_from_scenario(game_state, scenario)
        
        # 初始化场景
        self._initialize_locations_from_scenario(game_state, scenario)
        
        # 初始化事件
        self._initialize_events_from_scenario(game_state, scenario)
        
        # 设置游戏阶段
        game_state.current_phase = GamePhase.EXPLORATION
        
        # 存储场景信息到上下文 - 修复后的代码
        game_state.context["scenario"] = {
            "background": getattr(scenario.story_info, "background", "") if hasattr(scenario, "story_info") else "",
            "secret": getattr(scenario.story_info, "secrets", {}).get("main_secret", "") if hasattr(scenario, "story_info") else ""
        }
        
        # 存储游戏阶段信息
        if hasattr(scenario, 'game_stages'):
            game_phases = {}
            for phase_id, phase_info in scenario.game_stages.items():
                game_phases[phase_id] = {
                    "name": getattr(phase_info, "name", phase_id),
                    "description": getattr(phase_info, "description", ""),
                    "objective": getattr(phase_info, "objectives", ""),
                    "key_events": getattr(phase_info, "key_events", [])
                }
            game_state.context["game_phases"] = game_phases
        
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
                    relationships={}
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
        
        # 记录角色初始化信息
        game_state.metadata["character_count"] = len(game_state.characters)
    
    def _initialize_locations_from_scenario(self, game_state: GameState, scenario: Scenario):
        """
        从剧本中初始化位置到游戏状态
        
        Args:
            game_state: 游戏状态对象
            scenario: 剧本对象
        """
        # 初始化位置信息到游戏上下文
        locations = {}
        
        # 如果有locations属性，优先使用
        if hasattr(scenario, 'locations') and scenario.locations:
            for loc_id, location_info in scenario.locations.items():
                locations[loc_id] = {
                    "name": getattr(location_info, 'name', loc_id),
                    "description": getattr(location_info, 'description', ''),
                    "connected_to": getattr(location_info, 'connected_locations', []),
                    "available_items": getattr(location_info, 'available_items', []),
                    "properties": {
                        "danger_level": getattr(location_info, 'danger_level', 'low'),
                        "explored": False
                    }
                }
        # 如果没有locations属性，但有story_info.locations_description
        elif (hasattr(scenario, 'story_info') and 
              hasattr(scenario.story_info, 'locations_description') and 
              scenario.story_info.locations_description):
            for loc_id, description in scenario.story_info.locations_description.items():
                locations[loc_id] = {
                    "name": loc_id,
                    "description": description,
                    "connected_to": [],
                    "available_items": [],
                    "properties": {
                        "danger_level": "unknown",
                        "explored": False
                    }
                }
        
        # 存储位置信息到游戏状态
        game_state.context["locations"] = locations
        game_state.metadata["location_count"] = len(locations)
    
    def _initialize_events_from_scenario(self, game_state: GameState, scenario: Scenario):
        """
        从剧本中初始化事件到游戏状态
        
        Args:
            game_state: 游戏状态对象
            scenario: 剧本对象
        """
        # 初始化事件字典
        active_events = {}
        pending_events = {}
        
        # 如果有events属性，加载事件信息
        if hasattr(scenario, 'events') and scenario.events:
            for event in scenario.events:
                event_data = {
                    "id": getattr(event, 'event_id', str(uuid.uuid4())),
                    "description": getattr(event, 'description', ''),
                    "trigger_condition": getattr(event, 'trigger_condition', ''),
                    "perceptible_players": getattr(event, 'aware_players', ["all"]),
                    "content": getattr(event, 'content', ''),
                    "possible_outcomes": getattr(event, 'possible_outcomes', []),
                    "consequences": getattr(event, 'outcome_effects', {}),
                    "status": "pending"
                }
                
                # 添加到待触发事件字典
                event_id = event_data["id"]
                pending_events[event_id] = event_data
        
        # 存储事件信息
        game_state.context["event_definitions"] = pending_events
        game_state.metadata["total_events"] = len(pending_events)
        
        # 加载关键物品
        key_items = {}
        if hasattr(scenario, 'items') and scenario.items:
            for item_id, item_info in scenario.items.items():
                key_items[item_id] = {
                    "name": getattr(item_info, 'name', item_id),
                    "description": getattr(item_info, 'description', ''),
                    "location": getattr(item_info, 'location', ''),
                    "related_characters": getattr(item_info, 'related_characters', []),
                    "acquisition_difficulty": getattr(item_info, 'difficulty', 'medium'),
                    "discovered": False,
                    "possessed_by": None
                }
        
        # 存储关键物品
        game_state.context["key_items"] = key_items
        game_state.metadata["item_count"] = len(key_items)

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

    def get_current_phase_events(self) -> List[str]:
        """获取当前阶段的关键事件ID列表"""
        phase_name = self.game_state.current_phase.value
        return self.game_state.context.get("game_stages", {}).get(phase_name, {}).get("key_events", [])

    def advance_phase(self) -> None:
        """推进游戏阶段"""
        phases = list(GamePhase)
        current_index = phases.index(self.game_state.current_phase)
        if current_index < len(phases) - 1:
            self.game_state.current_phase = phases[current_index + 1]
            # 记录阶段变更
            self.game_state.metadata["phase_changes"] = self.game_state.metadata.get("phase_changes", [])
            self.game_state.metadata["phase_changes"].append({
                "from": phases[current_index].value,
                "to": self.game_state.current_phase.value,
                "round": self.game_state.round_number,
                "timestamp": datetime.now().isoformat()
            })

    def get_characters_at_location(self, location_id: str) -> List[str]:
        """获取在指定位置的角色ID列表"""
        return [char_id for char_id, status in self.game_state.character_status.items() 
                if status.location == location_id]