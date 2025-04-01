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


def format_trigger_condition(conditions: List[Dict[str, Any]], game_state) -> str:
    """
    将结构化的触发条件列表转换为自然语言描述。

    Args:
        conditions: 结构化条件字典的列表。
            示例: [{"type": "attribute", "entity_id": "player", "attribute": "health", "op": "<=", "value": 10}, ...]
        game_state: 当前游戏状态实例，用于查找实体名称和状态。

    Returns:
        str: 格式化后的自然语言条件描述。
    """
    if not conditions:
        return "无特定触发条件。"

    descriptions = []
    for condition in conditions:
        condition_type = condition.get("type")
        entity_id = condition.get("entity_id")
        op = condition.get("op")
        value = condition.get("value")
        desc = f"条件({condition_type})" # Default description

        # Helper to get entity name
        def get_entity_name(ent_id):
            if not game_state: return ent_id
            if ent_id == "player": # Assuming 'player' is a special ID
                # Find the player character ID
                player_char_id = None
                for char_id, char_instance in game_state.characters.items():
                    if char_instance.player_controlled:
                        player_char_id = char_id
                        break
                if player_char_id and player_char_id in game_state.characters:
                     return f"玩家({game_state.characters[player_char_id].name})"
                else:
                    return "玩家" # Fallback
            elif game_state.characters and ent_id in game_state.characters:
                return f"角色'{game_state.characters[ent_id].name}'({ent_id})"
            elif game_state.items and ent_id in game_state.items:
                 # Assuming items have a 'name' attribute in scenario.items
                 item_info = game_state.scenario.items.get(ent_id) if game_state.scenario else None
                 return f"物品'{getattr(item_info, 'name', ent_id)}'({ent_id})"
            elif game_state.locations and ent_id in game_state.locations:
                 # Assuming locations have a 'name' attribute in scenario.locations
                 loc_info = game_state.scenario.locations.get(ent_id) if game_state.scenario else None
                 return f"地点'{getattr(loc_info, 'name', ent_id)}'({ent_id})"
            return ent_id # Fallback to ID

        try:
            if condition_type == "attribute":
                attribute = condition.get("attribute")
                entity_name = get_entity_name(entity_id)
                # TODO: Get actual attribute value from game_state for comparison context?
                # current_value = get_attribute_value(game_state, entity_id, attribute) # Need helper
                desc = f"{entity_name} 的属性 '{attribute}' {op} {value}"
            elif condition_type == "item":
                item_id = condition.get("item_id")
                entity_name = get_entity_name(entity_id)
                item_name = get_entity_name(item_id) # Use helper for item name too
                has_item_str = "拥有" if op == "has" else "不拥有" if op == "not_has" else f"{op}"
                desc = f"{entity_name} {has_item_str} {item_name}"
            elif condition_type == "location":
                location_id = condition.get("location_id")
                entity_name = get_entity_name(entity_id)
                location_name = get_entity_name(location_id)
                is_at_str = "位于" if op == "is_at" else "不位于" if op == "not_at" else f"{op}"
                desc = f"{entity_name} {is_at_str} {location_name}"
            elif condition_type == "relationship":
                target_entity_id = condition.get("target_entity_id")
                entity_name = get_entity_name(entity_id)
                target_name = get_entity_name(target_entity_id)
                # TODO: Get actual relationship value from game_state
                desc = f"{entity_name} 与 {target_name} 的关系值 {op} {value}"
            # Add more condition types as needed (e.g., game_state variable, time)
            else:
                 desc = f"未知条件类型: {condition_type} ({condition})"

        except Exception as e:
            print(f"错误: 格式化条件时出错: {e}, 条件: {condition}")
            desc = f"格式化条件出错 ({condition.get('type', '未知类型')})"

        descriptions.append(desc)

    return " 并且 ".join(descriptions) + "。"
