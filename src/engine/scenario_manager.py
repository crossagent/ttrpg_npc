import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.models.game_state_models import GameState
from src.models.scenario_models import (
    Scenario, StoryInfo, ScenarioEvent, ScenarioCharacterInfo, 
    LocationInfo, ItemInfo, GameStageInfo, StoryChapter, 
    StorySection, StoryStage, StoryStructure
)
from src.config.config_loader import load_config

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
    
    def get_current_scenario(self) -> Optional[Scenario]:
        """
        获取当前加载的完整剧本
        
        Returns:
            Optional[Scenario]: 当前加载的剧本对象，如果未加载任何剧本则返回None
        """
        return self.scenario
    
    # 以下是新增的方法，用于获取故事结构相关信息
    
    def get_chapter_info(self, chapter_id: str) -> Optional[StoryChapter]:
        """
        根据ID获取章节信息
        
        Args:
            chapter_id: 章节ID
            
        Returns:
            Optional[StoryChapter]: 章节信息对象，如果不存在则返回None
        """
        if self.scenario is None or self.scenario.story_structure is None:
            return None
        
        for chapter in self.scenario.story_structure.chapters:
            if chapter.id == chapter_id:
                return chapter
        return None
    
    def get_section_info(self, section_id: str) -> Optional[StorySection]:
        """
        根据ID获取小节信息
        
        Args:
            section_id: 小节ID
            
        Returns:
            Optional[StorySection]: 小节信息对象，如果不存在则返回None
        """
        if self.scenario is None or self.scenario.story_structure is None:
            return None
        
        for chapter in self.scenario.story_structure.chapters:
            for section in chapter.sections:
                if section.id == section_id:
                    return section
        return None
    
    def get_stage_info(self, stage_id: str) -> Optional[StoryStage]:
        """
        根据ID获取阶段信息
        
        Args:
            stage_id: 阶段ID
            
        Returns:
            Optional[StoryStage]: 阶段信息对象，如果不存在则返回None
        """
        if self.scenario is None or self.scenario.story_structure is None:
            return None
        
        return self.find_stage_by_id(stage_id)
    
    def find_stage_by_id(self, stage_id: str) -> Optional[StoryStage]:
        """
        在整个故事结构中查找特定阶段
        
        Args:
            stage_id: 阶段ID
            
        Returns:
            Optional[StoryStage]: 阶段信息对象，如果不存在则返回None
        """
        if self.scenario is None or self.scenario.story_structure is None:
            return None
        
        for chapter in self.scenario.story_structure.chapters:
            for section in chapter.sections:
                for stage in section.stages:
                    if stage.id == stage_id:
                        return stage
        return None
    
    def get_character_by_id(self, character_id: str) -> Optional[ScenarioCharacterInfo]:
        """
        根据ID获取角色信息（增强版）
        
        Args:
            character_id: 角色ID
            
        Returns:
            Optional[ScenarioCharacterInfo]: 角色信息对象，如果不存在则返回None
        """
        return self.get_character_info(character_id)
    
    def get_location_by_id(self, location_id: str) -> Optional[LocationInfo]:
        """
        根据ID获取地点信息
        
        Args:
            location_id: 地点ID
            
        Returns:
            Optional[LocationInfo]: 地点信息对象，如果不存在则返回None
        """
        return self.get_location_info(location_id)
    
    def get_event_by_id(self, event_id: str) -> Optional[ScenarioEvent]:
        """
        根据ID获取事件信息
        
        Args:
            event_id: 事件ID
            
        Returns:
            Optional[ScenarioEvent]: 事件信息对象，如果不存在则返回None
        """
        return self.get_event_info(event_id)
    
    def get_item_by_id(self, item_id: str) -> Optional[ItemInfo]:
        """
        根据ID获取物品信息
        
        Args:
            item_id: 物品ID
            
        Returns:
            Optional[ItemInfo]: 物品信息对象，如果不存在则返回None
        """
        return self.get_item_info(item_id)
    
    def get_stage_metadata(self, stage_id: str) -> Dict[str, Any]:
        """
        获取指定阶段的所有相关元数据
        
        Args:
            stage_id: 阶段ID
            
        Returns:
            Dict[str, Any]: 包含阶段相关元数据的字典
        """
        stage = self.get_stage_info(stage_id)
        if not stage:
            return {}
        
        result = {
            "stage": stage,
            "characters": [],
            "locations": [],
            "events": [],
            "items": []
        }
        
        # 收集相关角色
        for char_id in stage.characters:
            char = self.get_character_info(char_id)
            if char:
                result["characters"].append(char)
        
        # 收集相关地点
        for loc_id in stage.locations:
            loc = self.get_location_by_id(loc_id)
            if loc:
                result["locations"].append(loc)
        
        # 收集相关事件
        for evt_id in stage.events:
            evt = self.get_event_by_id(evt_id)
            if evt:
                result["events"].append(evt)
        
        # 收集相关物品
        if stage.available_items:
            for item_id in stage.available_items:
                item = self.get_item_by_id(item_id)
                if item:
                    result["items"].append(item)
        
        return result
    
    def get_all_chapters(self) -> List[StoryChapter]:
        """
        获取所有章节信息
        
        Returns:
            List[StoryChapter]: 章节信息列表
        """
        if self.scenario is None or self.scenario.story_structure is None:
            return []
        
        return self.scenario.story_structure.chapters
    
    def get_chapter_sections(self, chapter_id: str) -> List[StorySection]:
        """
        获取指定章节的所有小节
        
        Args:
            chapter_id: 章节ID
            
        Returns:
            List[StorySection]: 小节信息列表
        """
        chapter = self.get_chapter_info(chapter_id)
        if not chapter:
            return []
        
        return chapter.sections
    
    def get_section_stages(self, section_id: str) -> List[StoryStage]:
        """
        获取指定小节的所有阶段
        
        Args:
            section_id: 小节ID
            
        Returns:
            List[StoryStage]: 阶段信息列表
        """
        section = self.get_section_info(section_id)
        if not section:
            return []
        
        return section.stages

    def find_next_stage(self, current_stage_id: str, current_section_id: str, current_chapter_id: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """
        根据当前阶段、小节、章节ID，查找下一个阶段、小节、章节ID。

        Args:
            current_stage_id: 当前阶段ID
            current_section_id: 当前小节ID
            current_chapter_id: 当前章节ID

        Returns:
            一个元组 (next_stage_id, next_section_id, next_chapter_id)。
            如果找不到下一个阶段（例如已是最后一个），则返回 (None, None, None)。
        """
        if not self.scenario or not self.scenario.story_structure:
            return None, None, None

        found_current = False
        for chapter_idx, chapter in enumerate(self.scenario.story_structure.chapters):
            if chapter.id == current_chapter_id:
                for section_idx, section in enumerate(chapter.sections):
                    if section.id == current_section_id:
                        for stage_idx, stage in enumerate(section.stages):
                            if stage.id == current_stage_id:
                                found_current = True
                                # 检查当前小节内是否有下一个阶段
                                if stage_idx + 1 < len(section.stages):
                                    next_stage = section.stages[stage_idx + 1]
                                    return next_stage.id, section.id, chapter.id
                                else:
                                    # 检查当前章节内是否有下一个小节
                                    if section_idx + 1 < len(chapter.sections):
                                        next_section = chapter.sections[section_idx + 1]
                                        if next_section.stages: # 确保下一个小节有阶段
                                            next_stage = next_section.stages[0]
                                            return next_stage.id, next_section.id, chapter.id
                                    else:
                                        # 检查是否有下一个章节
                                        if chapter_idx + 1 < len(self.scenario.story_structure.chapters):
                                            next_chapter = self.scenario.story_structure.chapters[chapter_idx + 1]
                                            if next_chapter.sections and next_chapter.sections[0].stages: # 确保下一个章节有小节和阶段
                                                next_section = next_chapter.sections[0]
                                                next_stage = next_section.stages[0]
                                                return next_stage.id, next_section.id, next_chapter.id
                                # 如果所有检查都失败，说明这是最后一个阶段
                                return None, None, None
            # 如果已经找到当前阶段但跳出了循环（意味着当前阶段是章节/小节的最后一个），则不需要继续查找
            if found_current:
                 break

        # 如果遍历完所有章节都没找到当前阶段（理论上不应发生），或找到了但它是最后一个
        return None, None, None
