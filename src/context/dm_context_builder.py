"""
DM上下文构建模块，负责构建DM所需的各类上下文文本。
"""
from typing import List, Dict, Any, Optional
from src.models.scenario_models import Scenario
from src.models.game_state_models import GameState
from src.models.message_models import Message
from src.models.action_models import PlayerAction
from src.context.context_utils import format_messages, format_character_list, format_location_list

def build_narrative_system_prompt(scenario: Optional[Scenario]) -> str:
    """
    构建DM叙述生成的系统提示
    
    Args:
        scenario: 游戏剧本
        
    Returns:
        str: 系统提示文本
    """
    if not scenario:
        return "你是一个桌面角色扮演游戏的主持人(DM)，负责描述场景、推动故事情节发展，并处理玩家的行动。"
        
    # 提取NPC列表（角色名称）
    npc_list = list(scenario.characters.keys())
    
    # 提取地点列表
    location_list = list(scenario.locations.keys()) if scenario.locations else []
    
    return f"""你是一个桌面角色扮演游戏的主持人(DM)，负责描述场景、推动故事情节发展，并处理玩家的行动。
当前游戏的背景设定是：{scenario.story_info.background}
主要场景包括：{', '.join(location_list) if location_list else '未指定'}
主要NPC包括：{', '.join(npc_list) if npc_list else '未指定'}

你的任务是：
1. 生成生动的场景描述
2. 根据玩家行动给出合理的结果
3. 推动故事情节发展
4. 确保游戏体验有趣且具有挑战性

请记住，你是一个公正的裁判，不要偏袒任何玩家，也不要过于严苛或宽松。
"""

def build_narrative_user_prompt(
    game_state: GameState, 
    unread_messages: List[Message], 
    current_scene: str
) -> str:
    """
    构建DM叙述生成的用户提示
    
    Args:
        game_state: 游戏状态
        unread_messages: 未读消息列表
        current_scene: 当前场景描述
        
    Returns:
        str: 用户提示文本
    """
    # 格式化未读消息
    formatted_messages = format_messages(unread_messages)
    
    return f"""
【第{game_state.round_number}回合】

最近的玩家消息:
{formatted_messages}

当前场景:
{current_scene}

请基于以上信息，生成一段生动的场景描述。描述应该:
1. 提及重要的场景元素和NPC
2. 反映玩家之前行动的影响
3. 暗示可能的行动方向
4. 以一个引导性问题结束，如"你们看到了什么？你们将如何行动？"
"""

def build_action_resolve_system_prompt(scenario: Optional[Scenario]) -> str:
    """
    构建DM行动解析的系统提示
    
    Args:
        scenario: 游戏剧本
        
    Returns:
        str: 系统提示文本
    """
    if not scenario:
        return "你是一个桌面角色扮演游戏的主持人(DM)，负责解析玩家的行动并决定其结果。"
    
    return f"""你是一个桌面角色扮演游戏的主持人(DM)，负责解析玩家的行动并决定其结果。
当前游戏的背景设定是：{scenario.story_info.background}

你的任务是：
1. 分析玩家行动的意图和可能性
2. 根据游戏规则和角色能力，决定行动的成功或失败
3. 生成生动的行动结果描述
4. 确定行动对游戏状态的影响

请公正地评估行动，考虑角色能力、环境因素和随机性。
"""

def build_action_resolve_user_prompt(
    game_state: GameState, 
    action: PlayerAction
) -> str:
    """
    构建DM行动解析的用户提示
    
    Args:
        game_state: 游戏状态
        action: 玩家行动
        
    Returns:
        str: 用户提示文本
    """
    # 获取角色信息
    character_info = "未知角色"
    if action.character_id in game_state.characters:
        character = game_state.characters[action.character_id]
        character_info = f"{character.name}({character.character_id})"
    
    return f"""
【第{game_state.round_number}回合】

玩家{action.player_id}控制的角色{character_info}尝试执行以下行动:
行动类型: {action.action_type}
行动内容: {action.content}
目标对象: {action.target}

请解析这个行动并决定其结果。你的回应应该包括:
1. 行动是否成功(success: true/false)
2. 行动结果的详细描述(narrative)
3. 行动导致的游戏状态变化(state_changes)

请以JSON格式回复，例如:
```json
{{
  "success": true,
  "narrative": "角色成功地完成了行动，造成了...",
  "state_changes": {{
    "character_health": -10,
    "item_obtained": "宝剑",
    "location_changed": true
  }}
}}
```
"""

def get_current_scene(scenario: Scenario, round_number: int) -> str:
    """
    获取当前场景描述
    
    Args:
        scenario: 游戏剧本
        round_number: 当前回合数
        
    Returns:
        str: 当前场景描述
    """
    if not scenario.locations:
        return "未指定场景"
        
    location_keys = list(scenario.locations.keys())
    if not location_keys:
        return "未指定场景"
        
    current_loc_key = location_keys[min(round_number, len(location_keys) - 1)]
    return scenario.locations[current_loc_key].description
