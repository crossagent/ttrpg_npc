from typing import List, Dict, Any, Optional
from datetime import datetime

from src.models.game_state_models import GameState, GamePhase
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
        pass
    
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

    def is_event_trigger_condition_met(self, event_id: str) -> bool:
        """检查事件触发条件是否满足"""
        # 实现触发条件检查逻辑
        if not self.game_state or not self.scenario_manager:
            return False
            
        event = self.scenario_manager.get_event_info(event_id)
        if not event:
            return False
            
        # 解析触发条件并检查
        # 这里实现具体的条件检查逻辑
        condition = event.trigger_condition
        
        # 示例：检查游戏阶段条件
        if "探索阶段" in condition and self.game_state.current_phase != GamePhase.EXPLORATION:
            return False
        if "博弈阶段" in condition and self.game_state.current_phase != GamePhase.NEGOTIATION:
            return False
        if "冲突阶段" in condition and self.game_state.current_phase != GamePhase.CONFLICT:
            return False
        
        # 示例：检查角色位置条件
        for character_id, status in self.game_state.character_status.items():
            character_name = self.game_state.characters[character_id].name
            if f"{character_name}进入" in condition:
                location_name = condition.split("进入")[1].split()[0]
                if status.location != location_name:
                    return False
        
        # 更多条件检查...
        
        return True  # 通过所有检查后返回True