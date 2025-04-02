# src/agents/player_agent.py
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import json
import traceback
import logging # Import logging

from src.agents.base_agent import BaseAgent
from src.models.scenario_models import ScenarioCharacterInfo, LocationInfo # Import LocationInfo
from src.models.game_state_models import GameState
from src.models.action_models import ActionType, ActionOption # Import ActionOption from action_models
from src.models.llm_validation import create_validator_for, LLMOutputError
from src.models.context_models import ActionOptionsLLMOutput # Now this should work
# Add imports for the revised approach
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken

# Assume BaseAgent initializes self.logger or get logger here
logger = logging.getLogger(__name__) # Or use self.logger if available from BaseAgent

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
        # Ensure logger is available (assuming BaseAgent provides it)
        # If not, initialize it here or use the module-level logger
        self.logger = getattr(self, 'logger', logger)


    async def generate_action_options(self, game_state: GameState, chara_info: ScenarioCharacterInfo) -> List[ActionOption]:
        """
        根据当前游戏状态和角色信息，生成供玩家选择的行动选项。

        Args:
            game_state: 当前游戏状态
            chara_info: 当前玩家角色的静态信息

        Returns:
            List[ActionOption]: 包含多个行动选项的列表 (例如 3 个)
        """
        self.logger.info(f"PlayerAgent ({self.agent_name}) generating action options for {self.character_id}...") # Use logger

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

        # --- 1b. 创建验证器并获取格式指令 ---
        # 在调用 LLM 之前创建验证器，以获取格式化指令
        validator = create_validator_for(ActionOptionsLLMOutput)
        format_instructions = validator.get_prompt_instruction() # 获取包含 Markdown 指令的文本

        # --- 1c. 构建最终的 Prompt ---
        system_prompt = f"""你是角色 {chara_info.name} ({chara_info.public_identity})。你的目标是: {chara_info.secret_goal}。
你当前的背景是: {chara_info.background or '无'}
你的特殊能力: {chara_info.special_ability or '无'}
你的弱点: {chara_info.weakness or '无'}

根据以下情境，为玩家生成 3 个清晰、具体、可执行的行动选项。
选项必须符合你的角色个性和目标。

当前情境:
你在 {current_location_desc}。
附近可见角色: {visible_chars_str}。
最近发生的事件或对话:
{recent_events}

你的当前状态: {status_str}
你的物品栏: {inventory_str}

{format_instructions}
"""
        # User prompt 可以保持简单，因为主要信息都在 system prompt 中
        user_prompt = "请根据以上信息生成行动选项。"

        # --- 2. 调用 LLM ---
        response_content = ""
        parsed_options: List[ActionOption] = []
        try:
            if not self.model_client:
                 raise ValueError("LLM model client is not configured for PlayerAgent.")

            # 采用与 dm_agent 类似的模式：创建临时 AssistantAgent
            # Imports moved to top

            # 创建临时助手
            assistant = AssistantAgent(
                name=f"{self.agent_name}_options_helper", # Give a unique name
                model_client=self.model_client,
                system_message=system_prompt # Pass the constructed system prompt
            )

            # 构建用户消息
            user_message = TextMessage(
                content=user_prompt,
                source="system" # Or perhaps self.agent_id? Check consistency if needed.
            )

            # 调用 on_messages 获取响应
            response = await assistant.on_messages([user_message], CancellationToken())

            # 从响应中提取内容
            if response and response.chat_message and response.chat_message.content:
                response_content = response.chat_message.content
            else:
                self.logger.error("LLM did not return a valid response structure via AssistantAgent.")
                response_content = ""
            # self.logger.debug(f"LLM Raw Response for options: {response_content[:300]}...") # Removed print, use logger.debug if needed

            # --- 3. 解析和验证 LLM 输出 ---
            # 使用之前创建的 validator 进行验证
            try:
                validated_output: ActionOptionsLLMOutput = validator.validate_response(response_content)
                parsed_options = validated_output.options
                # Limit to 3 options if LLM returns more
                if len(parsed_options) > 3:
                     self.logger.warning(f"LLM 返回了超过 3 个选项，将只取前 3 个。")
                     parsed_options = parsed_options[:3]
            except LLMOutputError as val_err:
                 self.logger.error(f"LLM options output validation failed: {val_err.message}. Raw: {response_content[:200]}...") # Use logger
                 # 注意：这里不再尝试 json.loads，因为 validate_response 内部会处理提取和解析
                 parsed_options = self._get_default_options(game_state)
            except Exception as inner_e: # Catch other potential errors during validation
                 self.logger.warning(f"Error during options validation: {inner_e}") # Use logger
                 self.logger.exception(inner_e) # Log traceback if needed
                 parsed_options = self._get_default_options(game_state)

        except Exception as e:
            self.logger.error(f"Error during PlayerAgent {self.agent_id} option generation (LLM call or validation): {str(e)}") # Use logger
            self.logger.exception(e) # Log traceback if needed
            # Fallback to default options on any major error
            parsed_options = self._get_default_options(game_state)

        # Ensure we always return a list, even if empty or default
        if not parsed_options:
             self.logger.warning("No valid options generated or parsed, returning default options.") # Use logger
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
            self.logger.error(f"Error parsing LLM options: {e}. Response: {response_content[:100]}...") # Use logger
            return [] # Return empty list on error
