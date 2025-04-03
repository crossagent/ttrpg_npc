"""
DM上下文构建模块，负责构建DM所需的各类上下文文本。
"""
from typing import List, Dict, Any, Optional
from src.models.scenario_models import Scenario
from src.models.game_state_models import GameState
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from src.models.scenario_models import Scenario
from src.models.game_state_models import GameState
from src.models.message_models import Message
from src.models.action_models import PlayerAction
from src.context.context_utils import (format_messages, format_character_list, format_location_list, 
                                       format_environment_info, format_current_stage_summary, 
                                       format_current_stage_characters, format_current_stage_locations)
from src.models.context_models import DMNarrativeSystemContext, DMNarrativeUserContext
from src.models.message_models import Message # Ensure Message is imported for type hint

from src.engine.scenario_manager import ScenarioManager

def build_narrative_system_prompt(scenario: Optional[Scenario]) -> str:
    """构建DM叙述生成的系统提示"""
    
    narrative_system_prompt = DMNarrativeSystemContext(
        story_background=scenario.story_info.background if scenario else "未知背景",
        narrative_style=scenario.story_info.narrative_style if scenario else "未知风格"
    )

    return f"""你是一个桌面角色扮演游戏的主持人(DM)，专注于场景描述和故事叙述。
当前游戏的背景设定是：{narrative_system_prompt.story_background},故事的风格是：{narrative_system_prompt.narrative_style}。

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
    scenario_manager: ScenarioManager, # Add scenario_manager parameter
    relevant_messages: List[Message], # Changed parameter name from unread_messages
    scenario: Scenario # Keep scenario for now, might be removable later if all utils use manager
) -> str:
    """构建DM叙述生成的用户提示"""
    # Format the relevant historical messages
    formatted_messages = format_messages(relevant_messages) 

    # Create the context object (consider if DMNarrativeUserContext needs update)
    narrative_user_prompt = DMNarrativeUserContext(
        recent_messages=formatted_messages, # Use formatted relevant messages
        stage_decribertion=format_current_stage_summary(game_state, scenario_manager), # Pass manager
        characters_description=format_current_stage_characters(game_state, scenario_manager), # Pass manager
        environment_description=format_environment_info(game_state, scenario_manager), # Pass manager
        location_description=format_current_stage_locations(game_state, scenario_manager) # Pass manager
    )
    
    # No need to format again, already done above
    # formatted_messages = format_messages(relevant_messages) 

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

自上次重要事件/行动以来的活动记录: 
{formatted_messages if formatted_messages else "无（或仅有非实质性对话）"}

玩家角色信息：
{narrative_user_prompt.characters_description}

当前地点描述：
{narrative_user_prompt.location_description}

当前环境：
{narrative_user_prompt.environment_description}

当前主要剧情描述:
{narrative_user_prompt.stage_decribertion}

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

玩家{action.character_id}控制的角色{character_info}尝试执行以下行动:
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
