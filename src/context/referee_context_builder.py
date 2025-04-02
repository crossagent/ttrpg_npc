# src/context/referee_context_builder.py
"""
构建裁判代理 (Referee Agent) 所需的上下文和 Prompt。
包括行动判定和事件触发判断的 Prompt。
"""
from typing import List, Dict, Any, Optional
from enum import Enum # Import Enum

import json # Added for formatting flags if needed later
from src.models.scenario_models import Scenario, ScenarioEvent
from src.models.game_state_models import GameState
from src.models.action_models import PlayerAction, ActionResult
from src.models.consequence_models import ConsequenceType # Import ConsequenceType
from src.context.context_utils import (
    format_messages,
    format_character_list,
    format_location_list,
    format_environment_info,
    format_current_stage_summary,
    format_current_stage_characters,
    format_current_stage_locations,
    format_trigger_condition # Import the new function
)

# --- 行动判定 Prompts ---

def build_action_resolve_system_prompt(scenario: Optional[Scenario] = None) -> str:
    """
    构建用于裁判代理判断【单个行动的直接属性后果】的系统 Prompt。
    指示 LLM 专注于成功/失败判断、结果叙述和 **属性类** 后果。
    **严格禁止** 判断 Flag 设置或事件触发。
    """
    base_prompt = """
你是一个 TTRPG 游戏的裁判（Referee）。你的职责是根据玩家的行动描述和当前游戏状态，判断该行动的直接 **属性后果**。
你需要判断行动是否成功，并提供一段简洁的叙事来描述结果。
【重要】你的判断【仅限于】该行动本身的直接 **属性效果** (例如HP变化、物品增减、关系值变化等)。
【严格禁止】判断此行动是否会设置任何叙事 Flag 或触发任何剧本事件 (`ScenarioEvent`)。这些将由后续步骤处理。

请根据用户提供的信息（游戏状态摘要、玩家行动）进行判断。

输出一个 JSON 对象，包含以下键：
- "success": 布尔值，表示行动是否成功。
- "narrative": 字符串，描述行动的直接结果和叙述。
- "attribute_consequences": 一个列表，包含由该行动直接引发的 **属性类** 结构化后果。如果无直接属性后果，则为空列表 `[]`。

JSON 输出格式示例：
```json
{
  "success": true,
  "narrative": "你成功撬开了锁，门吱呀一声打开了。",
  "attribute_consequences": []
}
```
或
```json
{
  "success": false,
  "narrative": "你尝试说服守卫，但他毫不动摇，反而更加警惕。",
  "attribute_consequences": [
      {"type": "change_relationship", "target_entity_id": "guard_01", "secondary_entity_id": "player", "value": -5}
  ]
}
```
或
```json
{
    "success": true,
    "narrative": "你挥舞长剑击中了哥布林，它发出痛苦的嚎叫。",
    "attribute_consequences": [
        {"type": "update_attribute", "target_entity_id": "goblin_1", "attribute_name": "health", "value": -15}
    ]
}
```

**关于 `attribute_consequences` 列表的重要说明：**
如果包含后果，每个后果对象中的 `type` 字段的值**必须**严格从以下 **属性类** 列表中选择：
- 'update_attribute'  (例如: 修改 health, mana, location 等)
- 'add_item'
- 'remove_item'
- 'change_relationship'
- 'send_message'      (用于裁判需要发送的系统消息或特定叙述)
**绝对不允许** 包含 'update_flag' 或 'trigger_event' 类型。
请确保使用这些预定义的属性类后果类型，并根据类型提供必要的其他字段（如 `target_entity_id`, `attribute_name`, `item_id`, `value` 等）。
"""
    # Add scenario specific rules or context if available
    # if scenario and scenario.rules:
    #     base_prompt += f"\n游戏规则参考:\n{scenario.rules}"

    return base_prompt

def build_action_resolve_user_prompt(game_state: GameState, action: PlayerAction) -> str:
    """
    构建用于裁判代理判断【单个行动的直接属性后果】的用户 Prompt。
    """
    # 格式化基础信息 - 提供足够判断属性后果的上下文
    environment_info = format_environment_info(game_state)
    stage_summary = format_current_stage_summary(game_state)
    # 获取行动者和目标的状态信息可能有助于判断
    actor_status = game_state.character_states.get(action.character_id)
    actor_status_text = f"行动者状态: {actor_status.model_dump_json(indent=2)}" if actor_status else "行动者状态未知。"
    # TODO: Handle target being a list or specific entity ID to fetch target status if needed

    prompt = f"""
## 当前游戏状态摘要
{environment_info}
{stage_summary}
当前回合: {game_state.round_number}
{actor_status_text}
{format_current_stage_characters(game_state)}
{format_current_stage_locations(game_state)}

## 待判断的玩家行动
玩家: {action.character_id}
行动类型: {action.action_type.value if isinstance(action.action_type, Enum) else action.action_type}
行动目标: {action.target}
行动内容: {action.content}

## 你的任务
请根据上述信息，判断该行动的直接 **属性后果**。输出 JSON 对象，包含 "success" (bool), "narrative" (str), 和 "attribute_consequences" (List[dict])。
记住，【不要】判断 Flag 设置或事件触发。只关注直接的属性变化。
"""
    return prompt.strip()


# --- 事件触发与结局选择 Prompts ---

def build_event_trigger_and_outcome_system_prompt(scenario: Optional[Scenario] = None) -> str:
    """
    构建用于裁判代理判断【活跃 ScenarioEvent 触发】和【选择结局】的系统 Prompt。
    """
    prompt = """
你是一个 TTRPG 游戏的裁判（Referee）。你的职责是根据本回合发生的所有行动的 **属性后果**，以及当前的游戏状态（包括当前的叙事 Flags），判断哪些 **活跃的** `ScenarioEvent` 的触发条件被满足了，并为每个触发的事件选择一个最合适的结局。
【重要】你 **只** 需要评估用户提供的【当前活动事件列表】中的事件，**不要** 评估剧本中其他未激活的事件或独立的 Flag 定义。

请根据以下信息：
1.  当前游戏状态摘要（包含当前的 `flags`）。
2.  本回合所有玩家行动的 **属性后果** 结果列表 (`ActionResult`)。
3.  当前 **活动中** 的事件列表 (`active_event_ids`)，包含每个事件的触发条件 (`trigger_condition`) 和 **所有可能的结局描述** (`possible_outcomes`)。

你的任务：
1.  **判断触发**: 分析每个 **活动事件** 的 `trigger_condition`，结合本回合行动的属性后果和当前游戏状态（包括 `flags`），判断该条件是否满足。
2.  **选择结局**: 对于每一个被触发的事件，根据当前情况（游戏状态、行动结果等）从其 `possible_outcomes` 列表中选择一个最合理的结局 ID (`outcome.id`)。

输出一个 JSON 对象，包含一个键 `"triggered_events"`，其值为一个列表。列表中的每个元素都是一个字典，包含 `"event_id"` (被触发的事件ID) 和 `"chosen_outcome_id"` (你为该事件选择的结局ID)。如果没有任何活动事件被触发，则返回空列表 `[]`。

JSON 输出格式示例：
```json
{
  "triggered_events": [
    {
      "event_id": "event_forest_ambush",
      "chosen_outcome_id": "outcome_ambush_success"
    },
    {
      "event_id": "event_find_hidden_note",
      "chosen_outcome_id": "outcome_note_found_read"
    }
  ]
}
```
或（无事件触发）:
```json
{
  "triggered_events": []
}
```
"""
    return prompt.strip()


def build_event_trigger_and_outcome_user_prompt(game_state: GameState, action_results: List[ActionResult], scenario: Scenario) -> str:
    """
    构建用于裁判代理判断【活跃 ScenarioEvent 触发】和【选择结局】的用户 Prompt。
    """
    environment_info = format_environment_info(game_state)
    stage_summary = format_current_stage_summary(game_state)

    # Format action results summary (focus on attribute consequences)
    action_summary_lines = []
    if action_results:
        for res in action_results:
            consequence_summary = ", ".join([f"{c.type.value}({c.attribute_name}={c.value})" if c.type == ConsequenceType.UPDATE_ATTRIBUTE else f"{c.type.value}" for c in res.consequences])
            action_summary_lines.append(
                f"- 玩家 {res.character_id} 执行 '{res.action.content}': {'成功' if res.success else '失败'}. "
                f"叙述: {res.narrative}. "
                f"属性后果: [{consequence_summary if consequence_summary else '无'}]"
            )
    else:
        action_summary_lines.append("本回合无实质性玩家行动。")
    action_summary = "\n".join(action_summary_lines)


    # Format active events, their conditions, AND possible outcomes
    active_events_details = []
    if game_state.active_event_ids and scenario and scenario.events:
        active_event_ids_set = set(game_state.active_event_ids) # Use set for faster lookup
        scenario_event_map = {event.event_id: event for event in scenario.events if hasattr(event, 'event_id')}

        for event_id in game_state.active_event_ids:
            event = scenario_event_map.get(event_id)
            if event:
                # Format trigger condition (assuming natural language string for now)
                condition_text = event.trigger_condition if isinstance(event.trigger_condition, str) else "复杂条件(非文本)"
                # TODO: If trigger_condition can be structured, use format_trigger_condition

                # Format possible outcomes
                outcomes_text = "\n".join([
                    f"    - 结局 ID: {outcome.id}, 描述: {outcome.description}"
                    for outcome in event.possible_outcomes if hasattr(outcome, 'id') and hasattr(outcome, 'description')
                ]) if hasattr(event, 'possible_outcomes') and isinstance(event.possible_outcomes, list) else "    - (无定义的结局)"

                active_events_details.append(
                    f"- 事件 ID: {event.event_id}\n"
                    f"  名称: {event.name if hasattr(event, 'name') else '未知'}\n"
                    f"  描述: {event.description if hasattr(event, 'description') else '无'}\n"
                    f"  触发条件 (自然语言): {condition_text}\n"
                    f"  可能的结局:\n{outcomes_text}"
                )
            else:
                active_events_details.append(f"- 事件 ID: {event_id} (未在剧本中找到详情)")
    else:
        active_events_details.append("当前无活动事件。")

    active_events_text = "\n".join(active_events_details)

    prompt = f"""
## 当前游戏状态摘要
{environment_info}
{stage_summary}
当前回合: {game_state.round_number}
{format_current_stage_characters(game_state)}
{format_current_stage_locations(game_state)}
{format_character_list(game_state.characters)}

## 本回合行动的属性后果摘要
{action_summary}

## 当前活动事件、触发条件及可能结局
{active_events_text}

## 你的任务
1.  根据本回合行动的 **属性后果** 和当前游戏状态（包括 **Flags**），判断【当前活动事件列表】中的哪些事件的 **自然语言触发条件** 被满足了。
2.  对于每一个被触发的事件，从其“可能的结局”列表中选择一个最合理的结局 ID。
3.  输出 JSON 对象，包含 `"triggered_events"` 列表，每个元素包含 `"event_id"` 和 `"chosen_outcome_id"`。
"""
    return prompt.strip()
