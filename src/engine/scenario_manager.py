import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.models.game_state_models import GameState
from src.models.scenario_models import Scenario, StoryInfo, ScenarioEvent
from src.config.config_loader import load_config
from src.models.scenario_models import ScenarioCharacterInfo, LocationInfo, ItemInfo, GameStageInfo

class ScenarioManager:
    """
    剧本管理器类，负责管理游戏剧本，提供事件和剧情线索。
    """
    
    def __init__(self, scenario: Optional[Scenario] = None):
        """
        初始化剧本管理器
        
        Args:
            scenario: 初始剧本，如果为None则创建空剧本
        """
        self.config = load_config()
        self.scenario = scenario
        self.scenarios_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scenarios')
    
    def load_scenario(self, scenario_id: Optional[str] = None) -> Scenario:
        """
        加载剧本
        
        Args:
            scenario_id: 剧本ID，如果为None则加载默认剧本
            
        Returns:
            Scenario: 加载的游戏剧本对象
        """
        if scenario_id is None:
            scenario_id = self.config.get('default_scenario', 'rust')
        
        scenario_path = os.path.join(self.scenarios_path, f"{scenario_id}.json")
        
        try:
            with open(scenario_path, 'r', encoding='utf-8') as f:
                scenario_data = json.load(f)
            
            # 使用Scenario.from_json方法创建Scenario对象
            self.scenario = Scenario.from_json(scenario_data)
            return self.scenario
            
        except FileNotFoundError:
            raise ValueError(f"找不到指定的剧本文件: {scenario_path}")
        except json.JSONDecodeError:
            raise ValueError(f"剧本文件格式错误: {scenario_path}")
    
    def get_character_info(self, character_id: str) -> Optional[ScenarioCharacterInfo]:
        """
        获取角色信息
        
        Args:
            character_id: 角色ID
            
        Returns:
            Optional[ScenarioCharacterInfo]: 角色信息对象，如果不存在则返回None
        """
        if self.scenario is None:
            return None
        
        return self.scenario.characters.get(character_id)
    
    def get_event_info(self, event_id: str) -> Optional[ScenarioEvent]:
        """
        获取事件信息
        
        Args:
            event_id: 事件ID
            
        Returns:
            Optional[ScenarioEvent]: 事件信息对象，如果不存在则返回None
        """
        if self.scenario is None:
            return None
        
        for event in self.scenario.events:
            if event.event_id == event_id:
                return event
        
        return None
    
    def get_story_info(self) -> Optional[StoryInfo]:
        """
        获取故事背景信息
        
        Returns:
            Optional[StoryInfo]: 故事背景信息对象
        """
        if self.scenario is None:
            return None
        
        return self.scenario.story_info
    
    def get_location_info(self, location_id: str) -> Optional[LocationInfo]:
        """
        获取地点信息
        
        Args:
            location_id: 地点ID
            
        Returns:
            Optional[LocationInfo]: 地点信息对象，如果不存在则返回None
        """
        if self.scenario is None or self.scenario.locations is None:
            return None
        
        return self.scenario.locations.get(location_id)
    
    def get_item_info(self, item_id: str) -> Optional[ItemInfo]:
        """
        获取物品信息
        
        Args:
            item_id: 物品ID
            
        Returns:
            Optional[ItemInfo]: 物品信息对象，如果不存在则返回None
        """
        if self.scenario is None or self.scenario.items is None:
            return None
        
        return self.scenario.items.get(item_id)
    
    def get_game_stage_info(self, stage_name: str) -> Optional[GameStageInfo]:
        """
        获取游戏阶段信息
        
        Args:
            stage_name: 阶段名称
            
        Returns:
            Optional[GameStageInfo]: 游戏阶段信息对象，如果不存在则返回None
        """
        if self.scenario is None or self.scenario.game_stages is None:
            return None
        
        return self.scenario.game_stages.get(stage_name)