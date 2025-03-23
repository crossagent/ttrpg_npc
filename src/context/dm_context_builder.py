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
    """构建DM叙述生成的系统提示"""
    if not scenario:
        return "你是一个桌面角色扮演游戏的主持人(DM)，负责生成生动的场景描述，推动故事发展。"
        
    # 提取基础信息
    npc_list = list(scenario.characters.keys())
    location_list = list(scenario.locations.keys()) if scenario.locations else []
    
    return f"""你是一个桌面角色扮演游戏的主持人(DM)，专注于场景描述和故事叙述。
当前游戏的背景设定是：{scenario.story_info.background}

你的核心任务是：
1. 创造沉浸式的场景体验，运用感官描述增强游戏世界的真实感
2. 清晰呈现场景中的关键元素，包括环境、NPC和可交互物品
3. 基于玩家行动反馈世界的变化，确保叙事的连贯性
4. 通过细节和氛围塑造适合当前情境的情绪基调
5. 引导而非限制玩家行动，提供探索的方向但保留选择的自由

叙事风格指导：
- 使用具体而生动的描述，避免空泛和模糊
- 平衡细节与节奏，不要过度冗长也不要过于简略
- 适应当前情境的情绪基调(紧张、神秘、轻松等)
- 通过环境细节暗示而非直接陈述可能的危险或机会

请专注于"呈现什么发生了"而非"计算什么应该发生"。
"""

def build_narrative_user_prompt(
    game_state: GameState, 
    unread_messages: List[Message], 
    current_scene: str
) -> str:
    """构建DM叙述生成的用户提示"""
    # 格式化未读消息
    formatted_messages = format_messages(unread_messages)
    
    # 获取当前故事阶段(如果有)
    current_stage = "未知阶段"
    if hasattr(game_state, "progress") and hasattr(game_state.progress, "current_stage"):
        if game_state.progress.current_stage:
            current_stage = game_state.progress.current_stage.name
    
    # 获取游戏内时间(如果有)
    game_time = "未指定时间"
    if hasattr(game_state, "environment") and hasattr(game_state.environment, "current_time"):
        game_time = game_state.environment.current_time
    
    # 获取重要场景变化
    scene_changes = ""
    if hasattr(game_state, "environment") and hasattr(game_state.environment, "recent_changes"):
        scene_changes = "\n".join(game_state.environment.recent_changes)
    
    return f"""
【第{game_state.round_number}回合 | {game_time} | {current_stage}】

最近的玩家活动:
{formatted_messages}

当前场景:
{current_scene}

场景变化:
{scene_changes if scene_changes else "无明显变化"}

请基于以上信息，生成一段生动的场景描述(300字左右)。描述应该:
1. 创造当前场景的氛围和感官体验
2. 突出场景中的关键元素和存在的角色
3. 反映玩家行动对环境和NPC的影响
4. 暗示可能的探索方向和隐藏的机会
5. 以引导性问题结束，激发玩家思考下一步行动

请确保叙述连贯且与之前的情节保持一致。
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
