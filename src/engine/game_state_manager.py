from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from src.models.game_state_models import GameState, GamePhase, CharacterReference, CharacterStatus, EnvironmentStatus
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
        self.current_state = initial_state
        self.state_history = []
        self.game_state: GameState = None
    
    def initialize_game_state(self, scenario: Scenario) -> GameState:
        """
        初始化游戏状态
        
        Args:
            scenario: 要使用的剧本
            
        Returns:
            GameState: 初始化的游戏状态
        """
        # 创建基本游戏状态
        game_state = GameState(
            game_id=str(uuid.uuid4()),
            scenario_id=scenario.scenario_id if hasattr(scenario, 'scenario_id') else "default",
            environment=EnvironmentStatus(
                current_location_id=list(scenario.地点描述.keys())[0] if scenario.地点描述 else "主场景",
                time=datetime.now(),
                weather="晴朗"
            )
        )
        
        # 初始化角色
        self._initialize_characters_from_scenario(game_state, scenario)
        
        # 初始化场景
        self._initialize_locations_from_scenario(game_state, scenario)
        
        # 初始化事件
        self._initialize_events_from_scenario(game_state, scenario)
        
        # 设置游戏阶段
        game_state.current_phase = GamePhase.EXPLORATION
        
        # 存储场景信息到上下文
        game_state.context["scenario"] = {
            "story_info": scenario.story_info,
            "game_stages": scenario.游戏阶段
        }
        
        return game_state

    def _initialize_characters_from_scenario(self, scenario: Scenario):
        """
        从剧本中初始化角色到游戏状态
        
        Args:
            scenario: 剧本对象
        """
        # 清空现有角色信息
        self.game_state.characters = {}
        self.game_state.character_status = {}
        
        # 从剧本中加载角色
        for char_id, character_info in scenario.角色信息.items():
            # 创建角色引用
            character_ref = CharacterReference(
                character_id=char_id,  # 生成唯一ID
                scenario_character_id=char_id,  # 保存原始ID
                name=character_info.get('公开身份', character_info.get('name', f"角色_{char_id}")),
                player_controlled=False,  # 默认为NPC
                additional_info={
                    "secret_goal": character_info.get('秘密目标', ''),
                    "background": character_info.get('背景故事', ''),
                    "special_ability": character_info.get('特殊能力', ''),
                    "weakness": character_info.get('弱点', '')
                }
            )
            
            # 创建角色状态
            character_status = CharacterStatus(
                character_id=char_id,
                location=scenario.get('起始位置', list(scenario.地点描述.keys())[0] if scenario.地点描述 else "主场景"),
                health=100,  # 默认值
                items=[],  # 初始无物品
                conditions=[],
                relationships={}
            )
            
            # 将角色添加到游戏状态
            self.game_state.characters[char_id] = character_ref
            self.game_state.character_status[char_id] = character_status

    def get_current_state(self) -> GameState:
        """
        获取当前游戏状态
        
        Returns:
            GameState: 当前游戏状态
        """
        pass
    
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
    
    def save_state(self) -> bool:
        """
        保存当前游戏状态
        
        Returns:
            bool: 是否保存成功
        """
        # 将当前状态添加到历史记录
        if self.current_state:
            self.state_history.append(self.current_state.copy(deep=True))
            return True
        return False
    
    def load_state(self, index: int = -1) -> Optional[GameState]:
        """
        加载历史游戏状态
        
        Args:
            index: 历史索引，默认为-1（最新）
            
        Returns:
            Optional[GameState]: 加载的游戏状态，如果失败则为None
        """
        if not self.state_history or index >= len(self.state_history) or index < -len(self.state_history):
            return None
        
        self.current_state = self.state_history[index].copy(deep=True)
        return self.current_state
    
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
    
    def get_player_ids(self) -> List[str]:
        """
        获取所有玩家ID
        
        Returns:
            List[str]: 玩家ID列表
        """
        if not self.current_state:
            return []
        
        return list(self.current_state.characters.keys())

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