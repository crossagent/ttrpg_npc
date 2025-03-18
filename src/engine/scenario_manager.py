import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.models.game_state_models import GameState, Event, CharacterInfo
from src.models.scenario_models import GameScenario, StoryInfo, ScenarioEvent
from src.config.config_loader import load_config

class ScenarioManager:
    """
    剧本管理器类，负责管理游戏剧本，提供事件和剧情线索。
    """
    
    def __init__(self, scenario: Optional[GameScenario] = None):
        """
        初始化剧本管理器
        
        Args:
            scenario: 初始剧本，如果为None则创建空剧本
        """
        pass
    
    def check_event_triggers(self, game_state: GameState) -> List[Event]:
        """
        检查状态是否触发新事件
        
        Args:
            game_state: 游戏状态
            
        Returns:
            List[Event]: 触发的事件列表
        """
        pass
    
    def get_character_info(self, character_id: str) -> Optional[CharacterInfo]:
        """
        获取角色信息
        
        Args:
            character_id: 角色ID
            
        Returns:
            Optional[CharacterInfo]: 角色信息，如果不存在则为None
        """
        pass
    
    def get_current_scenario(self) -> GameScenario:
        """
        获取当前剧本
        
        Returns:
            scenario: 当前剧本
        """
        pass
    
    def load_scenario(self, scenario_id: Optional[str] = None) -> GameScenario:
        """
        加载剧本
        
        Args:
            scenario_id: 剧本ID，如果为None则加载默认剧本
            
        Returns:
            GameScenario: 加载的游戏剧本对象
        """
        # 如果未指定剧本ID，则使用配置中的默认剧本
        if scenario_id is None:
            config = load_config('game_config.yaml')
            scenario_id = config['scenario']['default_name']
            
        # 构建剧本文件路径
        scenario_path = os.path.join('scenarios', scenario_id)
        
        try:
            # 加载剧本JSON文件
            with open(scenario_path, 'r', encoding='utf-8') as f:
                scenario_data = json.load(f)
            
            # 转换故事信息
            story_info = StoryInfo(
                background=scenario_data["story_info"]["背景"],
                secrets={"货轮秘密": scenario_data["story_info"]["货轮秘密"]}
            )
            
            # 转换角色信息
            characters = {}
            for name, info in scenario_data["角色信息"].items():
                characters[name] = CharacterInfo(
                    background=info["公开身份"],
                    goals=info["秘密目标"]
                )
            
            # 转换事件信息
            events = []
            for event_data in scenario_data["剧本事件"]:
                events.append(ScenarioEvent(
                    event_id=event_data["事件ID"],
                    description=event_data["描述"],
                    trigger_condition=event_data["触发条件"],
                    possible_outcomes=event_data["可能结局"]
                ))
            
            # 创建完整剧本
            return GameScenario(
                story_info=story_info,
                characters=characters,
                events=events
            )
        except FileNotFoundError:
            raise FileNotFoundError(f"剧本文件 '{scenario_path}' 未找到")
        except json.JSONDecodeError:
            raise ValueError(f"剧本文件 '{scenario_path}' 格式错误")
        except KeyError as e:
            raise KeyError(f"剧本文件缺少必要字段: {str(e)}")
    
    def get_active_events(self) -> List[Event]:
        """
        获取当前活跃事件
        
        Returns:
            List[Event]: 活跃事件列表
        """
        pass
    
    def complete_event(self, event_id: str) -> bool:
        """
        完成事件
        
        Args:
            event_id: 事件ID
            
        Returns:
            bool: 是否成功完成
        """
        pass
    
    def get_location_info(self, location_id: str) -> Dict[str, Any]:
        """
        获取位置信息
        
        Args:
            location_id: 位置ID
            
        Returns:
            Dict[str, Any]: 位置信息
        """
        pass
