# src/agents/referee_agent.py

from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from typing import Optional, Dict, Any, List # Added List
import json
import re
import uuid # Import uuid for unique assistant names
import traceback # Import traceback for error logging
import logging # Import logging

# +++ 更新导入 +++
from src.models.scenario_models import Scenario, ScenarioCharacterInfo # Keep Scenario for context if needed by prompt, Add ScenarioCharacterInfo
from src.models.game_state_models import GameState, CharacterInstance # Add CharacterInstance
from src.models.action_models import PlayerAction, ActionResult, RelationshipImpactAssessment # Add RelationshipImpactAssessment
from src.models.consequence_models import Consequence, ConsequenceType # Import Consequence and ConsequenceType
from src.agents.base_agent import BaseAgent
from src.engine.scenario_manager import ScenarioManager # Import ScenarioManager
from src.engine.chat_history_manager import ChatHistoryManager # Import ChatHistoryManager
# Import prompt builders from the new referee context builder
from src.context.referee_context_builder import (
    build_action_resolve_system_prompt, # Will be simplified
    build_action_resolve_user_prompt,   # Will be simplified
    # +++ Import new prompt builder for relationship assessment +++
    build_relationship_assessment_system_prompt,
    build_relationship_assessment_user_prompt,
    # Import the new combined prompt builders
    build_event_trigger_and_outcome_system_prompt, # Will be used by determine_triggered_events_and_outcomes
    build_event_trigger_and_outcome_user_prompt  # Will be used by determine_triggered_events_and_outcomes
)
# from src.models.scenario_models import Scenario # Ensure Scenario is imported - Already imported above
from autogen_agentchat.agents import AssistantAgent # Import AssistantAgent


class RefereeAgent(BaseAgent):
    """
    裁判代理类，负责解析和判断玩家或NPC的行动，并生成结果。
    使用LLM进行判断。包括行动直接结果判定和事件触发判定。
    """

    def __init__(self, agent_id: str, agent_name: str, scenario_manager: ScenarioManager, chat_history_manager: ChatHistoryManager, model_client=None): # Add chat_history_manager
        """
        初始化 RefereeAgent

        Args:
            agent_id (str): Agent唯一标识符
            agent_name (str): Agent名称
            scenario_manager: ScenarioManager 实例 # Add doc
            chat_history_manager: ChatHistoryManager 实例 # Add doc
            model_client: 模型客户端
        """
        super().__init__(agent_id=agent_id, agent_name=agent_name, chat_history_manager=chat_history_manager, model_client=model_client) # Pass chat_history_manager
        self.scenario_manager = scenario_manager # Store scenario_manager
        # Setup logger for this agent
        self.logger = logging.getLogger(f"RefereeAgent_{agent_name}")
        # Configure logging level if needed, e.g., self.logger.setLevel(logging.DEBUG)

    async def judge_action(self, action: PlayerAction, game_state: GameState, scenario: Optional[Scenario] = None) -> ActionResult:
        """
        使用LLM判断单个行动的直接 **属性后果** (成功/失败, 叙述, 属性类后果)。
        **注意：此方法严格不处理 Flag 设置或事件触发。**

        Args:
            action (PlayerAction): 需要判断的玩家行动
            game_state (GameState): 当前游戏状态
            scenario (Optional[Scenario]): 当前剧本 (可选)

        Returns:
            ActionResult: 行动结果 (只包含直接后果)
        """
        # 生成系统消息 (需要简化 Prompt，只关注属性后果)
        # TODO: Update build_action_resolve_system_prompt and build_action_resolve_user_prompt
        #       in referee_context_builder.py to reflect this simplification.
        #       The prompt should explicitly tell the LLM *not* to evaluate flags or events.
        system_message_content: str = build_action_resolve_system_prompt(scenario) # Placeholder, needs update

        # 创建临时的AssistantAgent实例用于本次调用
        assistant_name = f"{self.agent_name}_attribute_resolver_helper_{uuid.uuid4().hex}" # Renamed for clarity
        assistant = AssistantAgent(
            name=assistant_name,
            model_client=self.model_client,
            system_message=system_message_content
        )

        # 构建用户消息 (需要简化 Prompt, 并传递 scenario_manager)
        # TODO: Update build_action_resolve_user_prompt
        user_message_content: str = build_action_resolve_user_prompt(game_state, action, self.scenario_manager) # Pass scenario_manager
        user_message = TextMessage(
            content=user_message_content,
            source="system" # 源头标记为系统，表示这是内部调用
        )

        response_content: str = "" # Initialize response content
        try:
            # 调用LLM获取响应
            response = await assistant.on_messages([user_message], CancellationToken())
            if not response or not response.chat_message or not response.chat_message.content:
                self.logger.warning(f"未能从LLM获取有效的行动判断响应。Action: {action.content}")
                return ActionResult(
                    character_id=action.character_id,
                    action=action,
                    success=False,
                    narrative="系统错误：无法判断行动结果 (LLM无响应)。",
                    consequences=[] # Use consequences list
                )

            response_content = response.chat_message.content

            # 尝试解析JSON响应
            json_str: str = response_content
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_content, re.IGNORECASE)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                self.logger.warning(f"judge_action LLM响应未包含 ```json ``` 标记。尝试直接解析。响应: {response_content[:100]}...")

            try:
                response_data: Dict[str, Any] = json.loads(json_str)
            except json.JSONDecodeError as e:
                self.logger.error(f"judge_action JSON解析失败。错误信息: {e}。导致错误的JSON字符串: ```json\n{json_str}\n```")
                error_narrative = f"系统错误：裁判未能正确解析行动的属性后果格式。错误详情: {e}。"
                return ActionResult(
                    character_id=action.character_id,
                    action=action,
                    success=False, # Parsing failure implies action couldn't be properly judged
                    narrative=error_narrative,
                    consequences=[] # No consequences could be parsed
                )

            # --- 行动属性后果处理 ---
            attribute_consequences: List[Consequence] = []
            # Expecting "attribute_consequences" key now, instead of "direct_consequences"
            if "attribute_consequences" in response_data and isinstance(response_data["attribute_consequences"], list):
                for cons_data in response_data["attribute_consequences"]:
                    try:
                        consequence = Consequence(**cons_data)
                        # **Crucially, filter out any UPDATE_FLAG consequences here**
                        if consequence.type != ConsequenceType.UPDATE_FLAG:
                            attribute_consequences.append(consequence)
                        else:
                            self.logger.warning(f"judge_action LLM 错误地返回了 UPDATE_FLAG 后果，已忽略: {cons_data}")
                    except Exception as parse_err:
                        self.logger.warning(f"解析属性后果失败: {parse_err}. Data: {cons_data}")
            else:
                 self.logger.warning(f"judge_action LLM响应JSON缺少 'attribute_consequences' 列表。响应数据: {response_data}")


            # 验证 LLM 响应的基本字段 (success, narrative)
            required_keys = ['success', 'narrative']
            if not all(k in response_data for k in required_keys):
                 self.logger.warning(f"judge_action LLM响应JSON缺少必要字段 ({required_keys})。响应数据: {response_data}")
                 # Provide defaults if missing
                 response_data.setdefault('success', False)
                 response_data.setdefault('narrative', '行动结果描述缺失。')

            # 创建并返回行动结果 (只包含属性后果)
            return ActionResult(
                character_id=action.character_id,
                action=action,
                success=bool(response_data.get("success", False)),
                narrative=str(response_data.get("narrative", "行动结果未描述")),
                # dice_result 字段暂时不处理
                consequences=attribute_consequences # 只包含属性后果
            )
        except Exception as e:
            self.logger.exception(f"判断行动属性后果时发生意外错误: {str(e)}")
            # traceback.print_exc() # logger.exception includes traceback
            return ActionResult(
                character_id=action.character_id,
                action=action,
                success=False,
                narrative=f"系统内部错误：裁判处理行动时发生异常: {str(e)}",
                consequences=[] # Return empty consequences on error
            )

    async def determine_triggered_events_and_outcomes(self, action_results: List[ActionResult], game_state: GameState, scenario: Scenario) -> List[Dict[str, str]]:
        """
        使用LLM判断本回合触发了哪些 **活跃的 ScenarioEvent**，并为每个触发的事件选择一个结局。
        **注意：此方法不处理独立的 Flag 定义，只处理结构化的 ScenarioEvent。**

        Args:
            action_results: 本回合所有行动的 **属性后果** 结果列表 (来自 judge_action)。
            game_state: 当前游戏状态 (包含 flags)。
            scenario: 当前剧本 (包含 events)。

        Returns:
            List[Dict[str, str]]: 一个列表，每个元素是包含 "event_id" 和 "chosen_outcome_id" 的字典。
        """
        if not game_state.active_event_ids:
            self.logger.info("没有活动事件需要检查触发。")
            self.logger.info("没有活动事件需要检查触发。")
            return []

        # 构建 Prompt (Prompt 需要知道本回合的行动结果和当前 flags)
        # TODO: Update build_event_trigger_and_outcome_system_prompt and build_event_trigger_and_outcome_user_prompt
        #       to correctly use action_results and game_state.flags
        system_message_content = build_event_trigger_and_outcome_system_prompt(scenario) # Placeholder, needs update
        user_message_content = build_event_trigger_and_outcome_user_prompt(game_state, action_results, scenario, self.scenario_manager) # Pass scenario_manager

        # 创建临时 Agent
        assistant_name = f"{self.agent_name}_event_trigger_helper_{uuid.uuid4().hex}"
        assistant = AssistantAgent(
            name=assistant_name,
            model_client=self.model_client,
            system_message=system_message_content
        )
        user_message = TextMessage(content=user_message_content, source="system")

        response_content: str = ""
        triggered_events_with_outcomes: List[Dict[str, str]] = []

        try:
            # 调用 LLM
            response = await assistant.on_messages([user_message], CancellationToken())
            if not response or not response.chat_message or not response.chat_message.content:
                self.logger.warning(f"未能从LLM获取有效的事件触发与结局选择响应。")
                return [] # Return empty list on LLM error

            response_content = response.chat_message.content

            # 解析 JSON
            json_str = response_content
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_content, re.IGNORECASE)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                self.logger.warning(f"determine_triggered_events LLM响应未包含 ```json ``` 标记。尝试直接解析。响应: {response_content[:100]}...")

            try:
                response_data = json.loads(json_str)
                # Expecting {"triggered_events": [{"event_id": "...", "chosen_outcome_id": "..."}, ...]}
                if "triggered_events" in response_data and isinstance(response_data["triggered_events"], list):
                    raw_triggered_list = response_data["triggered_events"]
                    valid_results = []
                    active_event_ids_set = set(game_state.active_event_ids)
                    # Create scenario_event_map safely
                    scenario_event_map = {}
                    if scenario and scenario.events and isinstance(scenario.events, list):
                         scenario_event_map = {event.event_id: event for event in scenario.events if hasattr(event, 'event_id')}
                    else:
                         self.logger.warning("Scenario or scenario.events is missing or not a list, cannot validate event IDs.")


                    for item in raw_triggered_list:
                        if isinstance(item, dict) and "event_id" in item and "chosen_outcome_id" in item:
                            event_id = str(item["event_id"])
                            outcome_id = str(item["chosen_outcome_id"])

                            # Validate: event_id must be active
                            if event_id not in active_event_ids_set:
                                self.logger.warning(f"LLM 返回了非活动的事件ID: {event_id}")
                                continue

                            # Validate: event_id must exist in scenario (if possible)
                            if scenario_event_map and event_id not in scenario_event_map:
                                 self.logger.warning(f"LLM 返回了剧本中不存在的事件ID: {event_id}")
                                 continue

                            # Validate: chosen_outcome_id must exist for the given event_id (if possible)
                            if scenario_event_map:
                                event = scenario_event_map[event_id]
                                if not hasattr(event, 'possible_outcomes') or not isinstance(event.possible_outcomes, list):
                                     self.logger.warning(f"事件 {event_id} 缺少有效的 possible_outcomes 列表，无法验证结局ID。")
                                     # Decide whether to proceed or skip based on requirements
                                     # continue # Option: Skip if outcomes cannot be validated
                                elif not any(hasattr(outcome, 'id') and outcome.id == outcome_id for outcome in event.possible_outcomes):
                                    self.logger.warning(f"LLM 为事件 {event_id} 返回了无效的结局ID: {outcome_id}")
                                    continue

                            valid_results.append({"event_id": event_id, "chosen_outcome_id": outcome_id})
                        else:
                             self.logger.warning(f"LLM 返回的 triggered_events 列表包含无效项: {item}")

                    triggered_events_with_outcomes = valid_results
                else:
                    self.logger.warning(f"determine_triggered_events LLM响应JSON格式不正确或缺少 'triggered_events' 列表。响应数据: {response_data}")

            except json.JSONDecodeError as e:
                self.logger.error(f"determine_triggered_events JSON解析失败。错误: {e}。原始JSON: '{json_str}'. LLM响应: {response_content}")

        except Exception as e:
            self.logger.exception(f"判断事件触发与结局选择时发生意外错误: {str(e)}")

        if triggered_events_with_outcomes:
             self.logger.info(f"LLM 判断触发的事件及选定结局: {triggered_events_with_outcomes}")
        else:
             self.logger.info("LLM 判断本回合无 ScenarioEvent 触发或未能选择结局。")

        return triggered_events_with_outcomes
