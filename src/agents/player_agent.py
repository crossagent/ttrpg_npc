# src/agents/player_agent.py
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import json
import traceback

from src.agents.base_agent import BaseAgent
from src.models.scenario_models import ScenarioCharacterInfo, LocationInfo # Import LocationInfo
from src.models.game_state_models import GameState
from src.models.action_models import ActionType, ActionOption # Import ActionOption from action_models
from src.models.llm_validation import create_validator_for, LLMOutputError
from src.models.context_models import ActionOptionsLLMOutput # Now this should work

class PlayerAgent(BaseAgent):
    """
    代表人类玩家控制的角色 (PC) 的 Agent。
    主要职责是根据当前游戏状态为玩家生成可选的行动。
    实际的行动由玩家从选项中选择，并通过外部机制（如UI）传递给裁判。
    """
    def __init__(self, agent_id: str, agent_name: str, character_id: str, model_client=None):
        """
        初始化玩家 Agent
        Args:
            agent_id: Agent 唯一标识符
            agent_name: Agent 名称
            character_id: 对应的角色 ID
            model_client: 模型客户端
        """
        super().__init__(agent_id=agent_id, agent_name=agent_name, model_client=model_client)
        self.character_id = character_id
        # PlayerAgent might not need complex message memory like CompanionAgent,
        # but basic context handling might still be useful.

    async def generate_action_options(self, game_state: GameState, chara_info: ScenarioCharacterInfo) -> List[ActionOption]:
        """
        根据当前游戏状态和角色信息，生成供玩家选择的行动选项。

        Args:
            game_state: 当前游戏状态
            chara_info: 当前玩家角色的静态信息

        Returns:
            List[ActionOption]: 包含多个行动选项的列表 (例如 3 个)
        """
        print(f"PlayerAgent ({self.agent_name}) generating action options for {self.character_id}...")

        # --- 1. 构建 Prompt (需要新的 Context Builder 或调整) ---
        # TODO: Implement dedicated context builders for option generation
        # system_prompt = build_options_system_prompt(chara_info, game_state)
        # user_prompt = build_options_user_prompt(game_state, self.character_id)

        # Placeholder prompts for now
        # Extract relevant game state info for the prompt
        # Correctly get location from character_states
        current_location_id = game_state.character_states[self.character_id].location
        current_location_desc = game_state.scenario.locations.get(current_location_id, LocationInfo(description="未知地点")).description if game_state.scenario.locations else "未知地点"
        # Correctly check location in character_states for visible characters
        visible_characters = [
            f"{char_instance.name} ({char_instance.public_identity})" # Use char_instance from game_state.characters
            for char_id, char_instance in game_state.characters.items() # Iterate through CharacterInstance
            if game_state.character_states[char_id].location == current_location_id and char_id != self.character_id
        ]
        visible_chars_str = ", ".join(visible_characters) if visible_characters else "无"
        recent_events = "\n".join([f"- {msg.content}" for msg in game_state.chat_history[-5:]]) # Last 5 messages as recent events

        # Get current character status and inventory correctly from character_states
        current_char_status = game_state.character_states[self.character_id]
        status_str = f"Health: {current_char_status.health}, Known Info: {current_char_status.known_information}" # Example status string
        inventory_str = ", ".join([item.name for item in current_char_status.items]) if current_char_status.items else "无"

        system_prompt = f"""你是角色 {chara_info.name} ({chara_info.public_identity})。你的目标是: {chara_info.secret_goal}。
你当前的背景是: {chara_info.background or '无'}
你的特殊能力: {chara_info.special_ability or '无'}
你的弱点: {chara_info.weakness or '无'}

根据以下情境，为玩家生成 3 个清晰、具体、可执行的行动选项。
选项必须符合你的角色个性和目标。
选项格式必须是 JSON 列表，每个对象包含 'action_type' (必须是 'TALK', 'ACTION', 或 'WAIT' 之一), 'content' (行动的简短描述), 'target' (行动目标的角色ID, 'environment', 'all', 或物品ID)。

当前情境:
你在 {current_location_desc}。
附近可见角色: {visible_chars_str}。
最近发生的事件或对话:
{recent_events}

你的当前状态: {status_str}
你的物品栏: {inventory_str}

请严格按照 JSON 列表格式返回 3 个选项:
[
  {{"action_type": "...", "content": "...", "target": "..."}},
  {{"action_type": "...", "content": "...", "target": "..."}},
  {{"action_type": "...", "content": "...", "target": "..."}}
]
"""
        user_prompt = "请根据以上信息生成行动选项。" # User prompt might be simple if context is in system prompt

        # --- 2. 调用 LLM ---
        response_content = ""
        parsed_options: List[ActionOption] = []
        try:
            if not self.model_client:
                 raise ValueError("LLM model client is not configured for PlayerAgent.")

            # Use a generic call method if available, or adapt as needed
            # Assuming a method like `generate_text` exists
            # response = await self.model_client.generate_text(system_prompt + "\n" + user_prompt) # Combine prompts if needed
            # response_content = response if isinstance(response, str) else str(response) # Adjust based on actual return type

            # --- Placeholder LLM Response (REMOVE IN ACTUAL IMPLEMENTATION) ---
            print("  WARNING: Using placeholder LLM response for action options!")
            response_content = json.dumps([
                {"action_type": "TALK", "content": f"与 {visible_characters[0].split(' ')[0] if visible_characters else '某人'} 交谈，试探其口风。", "target": visible_characters[0].split(' ')[0] if visible_characters else "char_002"},
                {"action_type": "ACTION", "content": "仔细观察周围环境，寻找线索。", "target": "environment"},
                {"action_type": "WAIT", "content": "保持低调，继续观察。", "target": "environment"}
            ], ensure_ascii=False)
            # --- End Placeholder ---

            # --- 3. 解析和验证 LLM 输出 ---
            # Attempt to parse the JSON response
            try:
                options_data = json.loads(response_content)
                if not isinstance(options_data, list):
                    raise ValueError("LLM response is not a JSON list.")

                # Validate the entire list structure using ActionOptionsLLMOutput
                validator = create_validator_for(ActionOptionsLLMOutput)
                try:
                    validated_output: ActionOptionsLLMOutput = validator.validate_response(response_content)
                    parsed_options = validated_output.options
                    # Limit to 3 options if LLM returns more
                    if len(parsed_options) > 3:
                         self.logger.warning(f"LLM 返回了超过 3 个选项，将只取前 3 个。")
                         parsed_options = parsed_options[:3]
                except LLMOutputError as val_err:
                     print(f"  Error: LLM options output validation failed: {val_err.message}. Raw: {response_content[:200]}...")
                     parsed_options = self._get_default_options(game_state)
                except Exception as inner_e:
                     print(f"  Warning: Error validating options structure: {inner_e}")
                     parsed_options = self._get_default_options(game_state)

                # Old validation logic removed:
                # validator = create_validator_for(ActionOption) # Validator for individual options
                # for option_dict in options_data:
                #      if len(parsed_options) >= 3: # Limit to 3 options
                 #         break
                 #     try:
                 #         # Validate dict against ActionOption model
                 #         validated_option = validator.validate_response(json.dumps(option_dict)) # Validate each dict
                 #         parsed_options.append(validated_option)
                 #     except LLMOutputError as val_err:
                 #         print(f"  Warning: Skipping invalid action option from LLM: {val_err.message}. Data: {option_dict}")
                 #     except Exception as inner_e:
                 #          print(f"  Warning: Error validating option {option_dict}: {inner_e}")

            except json.JSONDecodeError: # Keep this for initial JSON parsing failure
                print(f"  Error: Failed to decode LLM JSON response for options: {response_content[:200]}...")
                # Fallback: Try to extract options using regex or return default options
                parsed_options = self._get_default_options(game_state)
            except ValueError as ve:
                 print(f"  Error: Invalid JSON structure from LLM: {ve}. Response: {response_content[:200]}...")
                 parsed_options = self._get_default_options(game_state)


        except Exception as e:
            print(f"Error during PlayerAgent {self.agent_id} option generation: {str(e)}")
            print(traceback.format_exc())
            # Fallback to default options on any major error
            parsed_options = self._get_default_options(game_state)

        # Ensure we always return a list, even if empty or default
        if not parsed_options:
             print("  Warning: No valid options generated or parsed, returning default options.")
             parsed_options = self._get_default_options(game_state)

        # Limit to exactly 3 options if more were somehow generated
        return parsed_options[:3]

    def _get_default_options(self, game_state: GameState) -> List[ActionOption]:
        """Provides default fallback action options."""
        # Try to find another character to talk to (Corrected location check)
        target_char_id = "environment"
        current_player_location = game_state.character_states[self.character_id].location
        for char_id in game_state.characters.keys():
            if char_id != self.character_id and game_state.character_states[char_id].location == current_player_location:
                target_char_id = char_id
                break

        return [
            ActionOption(action_type=ActionType.TALK, content="尝试与人交谈。", target=target_char_id if target_char_id != "environment" else "all"),
            ActionOption(action_type=ActionType.ACTION, content="观察周围环境。", target="environment"),
            ActionOption(action_type=ActionType.WAIT, content="保持警惕，等待时机。", target="environment"),
        ]

    def _parse_llm_options(self, response_content: str) -> List[ActionOption]:
        """
        (Helper function - needs implementation)
        Parses the LLM response string (expected to be JSON) into a list of ActionOption objects.
        Includes validation.
        """
        # TODO: Implement robust JSON parsing and validation using Pydantic models
        # Example (basic):
        try:
            options_list = json.loads(response_content)
            validated_options = [ActionOption(**opt) for opt in options_list if isinstance(opt, dict)]
            return validated_options[:3] # Return max 3 options
        except Exception as e:
            print(f"Error parsing LLM options: {e}. Response: {response_content[:100]}...")
            return [] # Return empty list on error
