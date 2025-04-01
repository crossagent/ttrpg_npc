# src/context/referee_context_builder.py
"""
构建裁判代理 (Referee Agent) 所需的上下文和 Prompt。
包括行动判定和事件触发判断的 Prompt。
"""
from typing import List, Dict, Any, Optional
from enum import Enum # Import Enum

from src.models.scenario_models import Scenario, ScenarioEvent
from src.models.game_state_models import GameState
from src.models.action_models import PlayerAction, ActionResult
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
    构建用于裁判代理判断【单个行动直接结果】的系统 Prompt。
    指示 LLM 专注于成功/失败判断和结果叙述，不处理事件触发。
    """
    # TODO: Refine this prompt significantly.
    # It should clearly state the Referee's limited role:
    # - Judge success/failure of the given action based on context.
    # - Provide a narrative description of the immediate outcome.
    # - Optionally, list *direct* consequences (if the LLM is capable and instructed).
    # - Explicitly state NOT to determine event triggers.
    # - Define the expected JSON output format: { "success": bool, "narrative": str, "direct_consequences": [...] } (optional consequences)

    base_prompt = """
你是一个 TTRPG 游戏的裁判（Referee）。你的职责是根据玩家的行动描述和当前游戏状态，判断该行动的直接结果。
你需要判断行动是否成功，并提供一段简洁的叙事来描述结果。
【重要】你的判断【仅限于】该行动本身的直接效果，【不要】考虑或判断此行动是否会触发任何后续的剧本事件。事件触发将由其他系统处理。

请根据以下信息：
1.  当前游戏状态摘要。
2.  玩家执行的行动。

输出一个 JSON 对象，包含以下键：
- "success": 布尔值，表示行动是否成功。
- "narrative": 字符串，描述行动的直接结果和叙述。
- "direct_consequences": (可选) 一个列表，包含由该行动直接引发的结构化后果（如果适用且你能确定）。如果无直接后果，则为空列表 []。

JSON 输出格式示例：
```json
{
  "success": true,
  "narrative": "你成功撬开了锁，门吱呀一声打开了。",
  "direct_consequences": []
}
```
或
```json
{
  "success": false,
  "narrative": "你尝试说服守卫，但他毫不动摇，反而更加警惕。",
  "direct_consequences": [
      {"type": "change_relationship", "entity_id": "guard_01", "target_entity_id": "player", "op": "-=", "value": 5}
  ]
}
```
"""
    # Add scenario specific rules or context if available
    # if scenario and scenario.rules:
    #     base_prompt += f"\n游戏规则参考:\n{scenario.rules}"

    return base_prompt

def build_action_resolve_user_prompt(game_state: GameState, action: PlayerAction) -> str:
    """
    构建用于裁判代理判断【单个行动直接结果】的用户 Prompt。
    """
    # TODO: Refine context provided. Maybe less detail is needed if only judging direct action.
    # Focus on information relevant to the specific action.

    # 格式化基础信息
    environment_info = format_environment_info(game_state)
    stage_summary = format_current_stage_summary(game_state)
    # Consider adding character status for the acting character and target?

    prompt = f"""
## 当前游戏状态摘要
{environment_info}
{stage_summary}
当前回合: {game_state.round_number}

## 待判断的玩家行动
玩家: {action.character_id}
行动类型: {action.action_type.value if isinstance(action.action_type, Enum) else action.action_type}
行动目标: {action.target}
行动内容: {action.content}

## 你的任务
请根据上述信息，判断该行动的直接结果。输出 JSON 对象，包含 "success" (bool), "narrative" (str), 和可选的 "direct_consequences" (List[dict])。
记住，【不要】判断事件触发。
"""
    return prompt.strip()


# --- 事件触发与结局选择 Prompts ---

def build_event_trigger_and_outcome_system_prompt(scenario: Optional[Scenario] = None) -> str:
    """
    构建用于裁判代理判断【事件触发】和【选择结局】的系统 Prompt。
    """
    # TODO: Refine this prompt significantly.
    # It should instruct the LLM to:
    # - Review game state, actions, active events, trigger conditions, AND possible outcomes.
    # - Identify triggered events.
    # - For EACH triggered event, select the most appropriate outcome ID from its possible_outcomes.
    # - Output a JSON object containing a list of {"event_id": "...", "chosen_outcome_id": "..."}.

    prompt = """
你是一个 TTRPG 游戏的裁判（Referee）。你的职责是根据本回合发生的所有行动及其结果，以及当前的游戏状态，判断哪些【活动中】的剧本事件的触发条件被满足了，并为每个触发的事件选择一个最合适的结局。

请根据以下信息：
1.  当前游戏状态摘要。
2.  本回合所有玩家行动的【直接结果】列表。
3.  当前【活动中】的事件列表，包含每个事件的触发条件和**所有可能的结局描述**。

你的任务：
1.  **判断触发**: 分析每个活动事件的触发条件，判断它们是否在本回合被满足。
2.  **选择结局**: 对于每一个被触发的事件，根据当前情况（游戏状态、玩家行动等）从其“可能的结局”列表中选择一个最合理的结局 ID。

输出一个 JSON 对象，包含一个键 "triggered_events"，其值为一个列表。列表中的每个元素都是一个字典，包含 "event_id" (被触发的事件ID) 和 "chosen_outcome_id" (你为该事件选择的结局ID)。如果没有任何事件被触发，则返回空列表。

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
    构建用于裁判代理判断【事件触发】和【选择结局】的用户 Prompt。
    """
    # TODO: Refine context provided. Ensure possible outcomes are formatted clearly.

    environment_info = format_environment_info(game_state)
    stage_summary = format_current_stage_summary(game_state)

    # Format action results summary
    action_summary = "\n".join([
        f"- 玩家 {res.character_id} 执行 '{res.action.content}': {'成功' if res.success else '失败'}. {res.narrative}"
        for res in action_results
    ]) if action_results else "本回合无实质性玩家行动。"

    # Format active events, their conditions, AND possible outcomes
    active_events_details = []
    if game_state.active_event_ids and scenario and scenario.events:
        for event_id in game_state.active_event_ids:
            event = next((e for e in scenario.events if e.event_id == event_id), None)
            if event:
                # Format trigger condition
                condition_text = ""
                if isinstance(event.trigger_condition, str):
                    condition_text = event.trigger_condition
                elif isinstance(event.trigger_condition, list):
                    condition_text = format_trigger_condition(event.trigger_condition, game_state)

                # Format possible outcomes
                outcomes_text = "\n".join([
                    f"    - 结局 ID: {outcome.id}, 描述: {outcome.description}"
                    for outcome in event.possible_outcomes
                ]) if event.possible_outcomes else "    - (无定义的结局)"

                active_events_details.append(
                    f"- 事件 ID: {event.event_id}\n"
                    f"  名称: {event.name}\n"
                    f"  描述: {event.description}\n"
                    f"  触发条件: {condition_text}\n"
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

## 本回合行动结果摘要
{action_summary}

## 当前活动事件、触发条件及可能结局
{active_events_text}

## 你的任务
1.  根据上述所有信息，判断【当前活动事件列表】中的哪些事件的触发条件在本回合被满足了。
2.  对于每一个被触发的事件，从其“可能的结局”列表中选择一个最合理的结局 ID。
3.  输出 JSON 对象，包含 "triggered_events" 列表，每个元素包含 "event_id" 和 "chosen_outcome_id"。
"""
    return prompt.strip()
