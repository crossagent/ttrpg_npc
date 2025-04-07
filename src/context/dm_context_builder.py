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
from src.models.message_models import Message
# +++ Import necessary types +++
from src.models.consequence_models import (
    AppliedConsequenceRecord, TriggeredEventRecord, AnyConsequence,
    ChangeLocationConsequence, TriggerEventConsequence, UpdateFlagConsequence # Add others if needed
)
from src.models.scenario_models import Scenario, LocationInfo, ScenarioEvent, EventOutcome
from typing import Optional, List, Set # Ensure Set is imported if used internally

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
    relevant_messages: List[Message],
    # scenario: Scenario # Removed, get scenario via manager
) -> str:
    """构建DM叙述生成的用户提示"""
    # Format the relevant historical messages
    formatted_messages = format_messages(relevant_messages)

    # --- Extract Narrative Focus Points ---
    focus_points: List[str] = []
    # Correct method name to get the scenario object
    scenario = scenario_manager.get_current_scenario()
    if not scenario:
        # Log error if scenario is not loaded in the manager
        print(f"错误：ScenarioManager 未加载剧本 (ID: {game_state.scenario_id})，无法提取焦点。")
        # Handle error appropriately, maybe add a default focus point
        focus_points.append("错误：无法加载剧本信息。")
    else:
        # Process Applied Consequences from the *current* round temporary record
        if hasattr(game_state, 'current_round_applied_consequences'):
            for record in game_state.current_round_applied_consequences:
                # Ensure applied_consequence is the correct object, not just details
                consequence = record.applied_consequence

                if isinstance(consequence, ChangeLocationConsequence):
                    char_id = consequence.target_entity_id
                    new_loc_id = consequence.value
                    if char_id in game_state.characters:
                        character = game_state.characters[char_id]
                        # Use the visited_locations list (treat as set for check)
                        if hasattr(character, 'visited_locations') and new_loc_id not in character.visited_locations:
                            if scenario.locations and new_loc_id in scenario.locations:
                                location_info = scenario.locations[new_loc_id]
                                focus_points.append(f"首次进入地点 '{location_info.name}' ({new_loc_id}): {location_info.description}")
                            else:
                                focus_points.append(f"首次进入未知地点: {new_loc_id}")

                # Example: Add focus for important flag updates if needed later
                # elif isinstance(consequence, UpdateFlagConsequence):
                #     if consequence.flag_name in ["some_important_flag"]:
                #         focus_points.append(f"关键剧情标志更新: '{consequence.flag_name}' 设为 {consequence.flag_value}.")

        # Process Triggered Events from the *current* round temporary record
        if hasattr(game_state, 'current_round_triggered_events'):
             for record in game_state.current_round_triggered_events:
                 event_id = record.event_id
                 outcome_id = record.outcome_id
                 event_name = f"事件 {event_id}"
                 outcome_desc = f"结局 {outcome_id}"

                 if scenario.events:
                     found_event = next((evt for evt in scenario.events if evt.event_id == event_id), None)
                     if found_event:
                         event_name = found_event.name
                         found_outcome = next((out for out in found_event.possible_outcomes if out.id == outcome_id), None)
                         if found_outcome:
                             outcome_desc = found_outcome.description
                 focus_points.append(f"事件触发: '{event_name}' ({event_id}) 发生结局 '{outcome_desc}' ({outcome_id})。")

    formatted_focus_points = "\n".join([f"- {fp}" for fp in focus_points]) if focus_points else "无特别关注的焦点变化。"

    # --- Build Context Sections ---
    # (Keep existing formatting functions, ensure they use scenario_manager)
    stage_description = format_current_stage_summary(game_state, scenario_manager)
    characters_description = format_current_stage_characters(game_state, scenario_manager)
    environment_description = format_environment_info(game_state, scenario_manager)
    location_description = format_current_stage_locations(game_state, scenario_manager)

    # --- Get other context info ---
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

**本回合关键变化焦点:**
{formatted_focus_points}

**当前状态摘要:**

玩家角色及主要伙伴信息：
{characters_description}

当前地点关键信息：
{location_description}

当前环境状况：
{environment_description}

当前主要剧情阶段：
{stage_description}

近期场景变化记录:
{scene_changes if scene_changes else "无明显变化"} # Consider removing if focus points cover major changes

**当前活跃/相关事件:**
{formatted_active_events}

**叙述任务:**

请基于以上提供的**当前状态摘要**（包含角色、地点、环境、剧情、事件信息）和**近期重要活动记录**，并**特别注意将“本回合关键变化焦点”中提到的具体描述或摘要自然地融入**到你的叙事中，生成一段生动的场景描述(约300字)。请严格遵守以下指示：

**核心原则：GameState 是客观事实的唯一来源。近期活动记录用于理解上下文，关键变化焦点用于突出重要进展。**

1.  **事实来源**: 你描述的所有**客观事实**（谁在哪里、拥有什么、状态如何）**必须**严格来源于上面提供的“**当前状态摘要**”。**禁止**虚构与 GameState 不符的事实。**“本回合关键变化焦点”部分提供了本回合发生的、需要你在叙事中明确提及或反映的关键新信息、地点描述或事件摘要。**
2.  **聚焦变化，避免重复**:
    *   **首要任务**: 利用“**近期重要活动记录**”来理解**自上次叙述以来发生了哪些行动**。利用“**本回合关键变化焦点**”来了解**世界发生了哪些重要变化**。你的描述**必须**反映这些活动和变化带来的**新信息**或**状态进展**。
    *   **关键指令**: **绝对不要**简单重复上一回合的场景描述。如果场景核心要素（地点、环境、在场人物）没有巨大变化（即没有出现在焦点中），应侧重于描述**人物的行动、互动或状态的细微变化**。
    *   **处理静态信息**: 对于玩家已知且未发生显著变化的静态环境信息（例如，“房间还是那个房间”，且未作为焦点提及），请**务必简略带过或完全省略**。
3.  **区分转述与描述**:
    *   对于玩家角色（Player）和主要 NPC 伙伴（Companion）的行动（参考“近期重要活动记录”），请**客观、简洁地转述**发生了什么及其直接、明显的结果。**不要**猜测他们的内心想法或添加 GameState 中没有的后果。
    *   对于其他次要 NPC 的行为、环境的自然变化、需要渲染的氛围或基于“当前活跃/相关事件”和“本回合关键变化焦点”的暗示，你可以进行更具**描述性**的生成，但仍需与 GameState 的整体情况保持一致。
4.  **核心要素**: 在聚焦变化的同时，确保描绘出场景的**氛围**和关键的**感官体验**，并点明场景中的**关键元素**和**在场角色**（特别是新出现的或状态有显著变化的）。**务必将“本回合关键变化焦点”中的具体文本片段或摘要自然地、无缝地融入到你的整体叙事中。**
5.  **引导探索 (可选)**: 如果合适，可以通过环境细节**暗示**（而非明示）可能的探索方向、潜在的危险或与“当前活跃/相关事件”相关的线索。
6.  **结尾**: 可以考虑以一个开放性的观察或简短问句结束，引导玩家思考。

请确保叙述**连贯**，风格符合剧本设定，并且所有事实性描述都**严格基于**提供的 GameState 信息，同时**必须体现**近期活动记录中的动态进展和**关键变化焦点**中提供的具体内容。
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
