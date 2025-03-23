"""
上下文构建工具函数，提供共享的格式化和工具函数。
"""
from typing import List, Dict, Any
from src.models.message_models import Message
from src.models.game_state_models import CharacterInstance

def format_messages(messages: List[Message]) -> str:
    """
    格式化消息列表为文本
    
    Args:
        messages: 消息列表
        
    Returns:
        str: 格式化后的消息文本
    """
    if not messages:
        return "没有新消息"
    
    return "\n".join([f"{msg.source}: {msg.content}" for msg in messages])

def format_character_list(characters: Dict[str, CharacterInstance]) -> str:
    """
    格式化角色列表为文本
    
    Args:
        characters: 角色实例字典，键为角色ID
        
    Returns:
        str: 格式化后的角色列表文本
    """
    if not characters:
        return "未指定角色"
    
    return ", ".join([char.name for char in characters.values()])

def format_location_list(locations: Dict[str, Any]) -> str:
    """
    格式化位置列表为文本
    
    Args:
        locations: 位置字典，键为位置ID
        
    Returns:
        str: 格式化后的位置列表文本
    """
    if not locations:
        return "未指定场景"
    
    return ", ".join(locations.keys())

def format_environment_info(game_state) -> str:
    """
    格式化当前环境信息为文本
    
    Args:
        game_state: 游戏状态实例
        
    Returns:
        str: 格式化后的环境信息文本
    """
    if not game_state or not game_state.environment:
        return "环境信息不可用"
    
    env = game_state.environment
    current_location_id = env.current_location_id
    
    # 获取当前位置信息
    location_description = "未知位置"
    if game_state.scenario and game_state.scenario.locations and current_location_id in game_state.scenario.locations:
        location_info = game_state.scenario.locations.get(current_location_id)
        if location_info:
            location_description = location_info.description
        
        # 如果有位置状态变化，添加到描述中
        location_obj = game_state.location_states.get(current_location_id)
        if location_obj and location_obj.description_state:
            location_description += f" {location_obj.description_state}"
    
    time_str = env.time.strftime("%Y-%m-%d %H:%M")
    
    return f"当前位置: {current_location_id} ({location_description})\n" \
           f"时间: {time_str}\n" \
           f"天气: {env.weather}\n" \
           f"氛围: {env.atmosphere}\n" \
           f"光照: {env.lighting}"

def format_current_stage_summary(game_state) -> str:
    """
    格式化当前章节剧情大纲为文本
    
    Args:
        game_state: 游戏状态实例
        
    Returns:
        str: 格式化后的章节剧情大纲文本
    """
    if not game_state or not game_state.progress or not game_state.scenario or not game_state.scenario.story_structure:
        return "章节信息不可用"
    
    progress = game_state.progress
    story_structure = game_state.scenario.story_structure
    
    current_chapter_id = progress.current_chapter_id
    current_section_id = progress.current_section_id
    current_stage_id = progress.current_stage_id
    
    # 查找当前章节
    current_chapter = None
    current_section = None
    current_stage = None
    
    for chapter in story_structure.chapters:
        if chapter.id == current_chapter_id:
            current_chapter = chapter
            for section in chapter.sections:
                if section.id == current_section_id:
                    current_section = section
                    for stage in section.stages:
                        if stage.id == current_stage_id:
                            current_stage = stage
                            break
                    break
            break
    
    if not current_chapter or not current_section or not current_stage:
        return "无法找到当前章节信息"
    
    # 组合章节信息
    summary = f"章节: {current_chapter.name} - {current_chapter.description}\n" \
              f"小节: {current_section.name} - {current_section.description}\n" \
              f"阶段: {current_stage.name} - {current_stage.description}\n" \
              f"目标: {current_stage.objective}"
    
    return summary

def format_current_stage_characters(game_state) -> str:
    """
    格式化当前阶段相关角色的公开信息为文本
    
    Args:
        game_state: 游戏状态实例
        
    Returns:
        str: 格式化后的角色公开信息文本
    """
    if not game_state or not game_state.progress or not game_state.scenario or not game_state.scenario.story_structure:
        return "角色信息不可用"
    
    # 获取当前阶段
    progress = game_state.progress
    story_structure = game_state.scenario.story_structure
    
    current_chapter_id = progress.current_chapter_id
    current_section_id = progress.current_section_id
    current_stage_id = progress.current_stage_id
    current_stage = None
    
    # 遍历查找当前阶段
    for chapter in story_structure.chapters:
        if chapter.id == current_chapter_id:
            for section in chapter.sections:
                if section.id == current_section_id:
                    for stage in section.stages:
                        if stage.id == current_stage_id:
                            current_stage = stage
                            break
                    break
            break
    
    if not current_stage or not hasattr(current_stage, 'characters') or not current_stage.characters:
        return "当前阶段没有关联角色"
    
    # 获取阶段相关角色的详细信息
    character_info_list = []
    
    for char_id in current_stage.characters:
        # 检查角色是否存在于游戏状态中
        if char_id not in game_state.characters:
            continue
            
        char_instance = game_state.characters[char_id]
        char_info = f"- {char_instance.name} ({char_instance.public_identity})\n"
        
        # 获取角色当前位置
        status = char_instance.status
        if status and status.location:
            # 获取位置名称
            location_name = status.location
            if game_state.scenario.locations and status.location in game_state.scenario.locations:
                location_obj = game_state.scenario.locations.get(status.location)
                if location_obj and hasattr(location_obj, 'name'):
                    location_name = location_obj.name
            
            char_info += f"  当前位置: {location_name}\n"
        
        # 添加角色可见状态信息
        if status and status.conditions:
            visible_conditions = ", ".join(status.conditions)
            char_info += f"  状态: {visible_conditions}\n"
        
        character_info_list.append(char_info)
    
    if not character_info_list:
        return "未找到角色详细信息"
    
    return "\n".join(character_info_list)

def format_current_stage_locations(game_state) -> str:
    """
    格式化当前阶段关联的地点信息为文本
    
    Args:
        game_state: 游戏状态实例
        
    Returns:
        str: 格式化后的地点信息文本
    """
    if not game_state or not game_state.progress or not game_state.scenario:
        return "地点信息不可用"
    
    progress = game_state.progress
    story_structure = game_state.scenario.story_structure
    
    # 查找当前阶段
    current_chapter_id = progress.current_chapter_id
    current_section_id = progress.current_section_id
    current_stage_id = progress.current_stage_id
    current_stage = None
    
    # 遍历查找当前阶段
    for chapter in story_structure.chapters:
        if chapter.id == current_chapter_id:
            for section in chapter.sections:
                if section.id == current_section_id:
                    for stage in section.stages:
                        if stage.id == current_stage_id:
                            current_stage = stage
                            break
                    break
            break
    
    if not current_stage or not hasattr(current_stage, 'locations') or not current_stage.locations:
        return "当前阶段没有关联地点"
    
    # 获取地点详细信息
    location_details = []
    for loc_id in current_stage.locations:
        location_info = None
        if game_state.scenario.locations and loc_id in game_state.scenario.locations:
            location_info = game_state.scenario.locations.get(loc_id)
        
        # 获取位置状态信息
        location_state = ""
        if game_state.location_states and loc_id in game_state.location_states:
            loc_state_obj = game_state.location_states.get(loc_id)
            if loc_state_obj and loc_state_obj.description_state:
                location_state = f" - {loc_state_obj.description_state}"
        
        if location_info:
            location_name = getattr(location_info, 'name', loc_id)
            location_desc = getattr(location_info, 'description', "无描述")
            location_details.append(f"- {location_name} ({loc_id}){location_state}\n  {location_desc}")
        else:
            location_details.append(f"- {loc_id}{location_state}")
    
    if not location_details:
        return "未找到地点详细信息"
    
    return "\n".join(location_details)