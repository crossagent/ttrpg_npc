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
# +++ Import Optional if not already imported for the helper function type hint +++
from typing import Optional 

from src.engine.scenario_manager import ScenarioManager

# +++ Helper function to format event info +++
def _format_active_events(game_state: Optional[GameState]) -> str:
    if not game_state or not hasattr(game_state, 'event_instances') or not game_state.event_instances:
        return "无特别活跃的事件实例。"
    
    active_events = []
    for event_id, instance in game_state.event_instances.items():
        # Example: Format based on instance status or other relevant fields
        # This needs refinement based on the actual structure and meaning of EventInstance
        status = getattr(instance, 'status', '未知状态') 
        description = getattr(instance, 'description', event_id) # Use description if available
        active_events.append(f"- {description} (ID: {event_id}, 状态: {status})") 
        
    if not active_events:
        return "无特别活跃的事件实例。"
        
    return "\n".join(active_events)

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
    # Note: DMNarrativeUserContext might not be strictly necessary if we build the prompt string directly
    # Keeping it for now, but ensure its fields align with the prompt content.
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
    # Check if game_state is not None before accessing attributes
    if game_state and hasattr(game_state, "environment") and hasattr(game_state.environment, "recent_changes"):
        scene_changes = "\n".join(game_state.environment.recent_changes)
        
    # +++ Format active events using the helper +++
    formatted_active_events = _format_active_events(game_state) # Pass the snapshot here
    
    return f"""
【第{game_state.round_number if game_state else 1}回合 | {game_time} | {current_stage}】 # Handle None game_state for round 1

**近期重要活动记录 (最近 {len(relevant_messages)} 条消息):**
{formatted_messages if formatted_messages else "无重要活动记录（例如，游戏刚开始或长时间无实质交互）"}

**当前状态摘要:**

玩家角色及主要伙伴信息：
{narrative_user_prompt.characters_description}

当前地点关键信息：
{narrative_user_prompt.location_description}

当前环境状况：
{narrative_user_prompt.environment_description}

当前主要剧情阶段：
{narrative_user_prompt.stage_decribertion}

近期场景变化记录:
{scene_changes if scene_changes else "无明显变化"}

**当前活跃/相关事件:**
{formatted_active_events}

**叙述任务:**

请基于以上提供的**当前状态摘要**（包含角色、地点、环境、剧情、事件信息）和**近期重要活动记录**，生成一段生动的场景描述(约300字)。请严格遵守以下指示：

**核心原则：GameState 是事实的唯一来源，近期活动记录用于聚焦变化和风格调整。**

1.  **事实来源**: 你描述的所有**客观事实**（谁在哪里、拥有什么、状态如何、发生了什么固定后果）**必须**严格来源于上面提供的“**当前状态摘要**”和“**近期场景变化记录**”。**禁止**虚构与 GameState 不符的事实。
2.  **聚焦变化，避免重复**: 利用“**近期重要活动记录**”来理解**自上次叙述以来的主要变化**。你的首要任务是描述这些**新信息**：新出现的人物/地点/物品、状态的显著改变、首次进入的场景等。对于玩家已知且未发生显著变化的静态环境信息，请**务必简略带过或完全省略**。
3.  **区分转述与描述**:
    *   对于玩家角色（Player）和主要 NPC 伙伴（Companion）的行动（参考“近期重要活动记录”和“近期场景变化记录”），请**客观、简洁地转述**其行动过程和已发生的、记录在 GameState 中的直接结果。**不要**猜测他们的内心想法或添加 GameState 中没有的后果。
    *   对于其他次要 NPC 的行为、环境的自然变化、需要渲染的氛围或基于“当前活跃/相关事件”的暗示，你可以进行更具**描述性**的生成，但仍需与 GameState 的整体情况保持一致。
4.  **核心要素**: 在聚焦变化的同时，确保描绘出场景的**氛围**和关键的**感官体验**，并点明场景中的**关键元素**和**在场角色**（特别是新出现的或状态有显著变化的）。
5.  **引导探索 (可选)**: 如果合适，可以通过环境细节**暗示**（而非明示）可能的探索方向、潜在的危险或与“当前活跃/相关事件”相关的线索。
6.  **结尾**: 可以考虑以一个开放性的观察或简短问句结束，引导玩家思考。

请确保叙述**连贯**，风格符合剧本设定，并且所有事实性描述都**严格基于**提供的 GameState 信息。
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
