# src/agents/referee_agent.py

from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from typing import Optional, Dict, Any, List # Added List
import json
import re
import uuid # Import uuid for unique assistant names
import traceback # Import traceback for error logging
import logging # Import logging

from src.models.scenario_models import Scenario # Keep Scenario for context if needed by prompt
from src.models.game_state_models import GameState
from src.models.action_models import PlayerAction, ActionResult
from src.models.consequence_models import Consequence # Import Consequence
from src.agents.base_agent import BaseAgent
# Import prompt builders from the new referee context builder
from src.context.referee_context_builder import (
    build_action_resolve_system_prompt,
    build_action_resolve_user_prompt,
    # Import the new combined prompt builders
    build_event_trigger_and_outcome_system_prompt,
    build_event_trigger_and_outcome_user_prompt
)
from src.models.scenario_models import Scenario # Ensure Scenario is imported
from autogen_agentchat.agents import AssistantAgent # Import AssistantAgent


class RefereeAgent(BaseAgent):
    """
    裁判代理类，负责解析和判断玩家或NPC的行动，并生成结果。
    使用LLM进行判断。包括行动直接结果判定和事件触发判定。
    """

    def __init__(self, agent_id: str, agent_name: str, model_client=None):
        """
        初始化 RefereeAgent

        Args:
            agent_id (str): Agent唯一标识符
            agent_name (str): Agent名称
            model_client: 模型客户端
        """
        super().__init__(agent_id=agent_id, agent_name=agent_name, model_client=model_client)
        # Setup logger for this agent
        self.logger = logging.getLogger(f"RefereeAgent_{agent_name}")
        # Configure logging level if needed, e.g., self.logger.setLevel(logging.DEBUG)

    async def judge_action(self, action: PlayerAction, game_state: GameState, scenario: Optional[Scenario] = None) -> ActionResult:
        """
        使用LLM判断单个行动的直接结果 (成功/失败, 叙述, 直接后果)。
        注意：此方法不处理事件触发。

        Args:
            action (PlayerAction): 需要判断的玩家行动
            game_state (GameState): 当前游戏状态
            scenario (Optional[Scenario]): 当前剧本 (可选)

        Returns:
            ActionResult: 行动结果 (只包含直接后果)
        """
        # 生成系统消息
        system_message_content: str = build_action_resolve_system_prompt(scenario)

        # 创建临时的AssistantAgent实例用于本次调用
        assistant_name = f"{self.agent_name}_action_resolver_helper_{uuid.uuid4()}" # Ensure unique name
        assistant = AssistantAgent(
            name=assistant_name,
            model_client=self.model_client,
            system_message=system_message_content
        )

        # 构建用户消息
        user_message_content: str = build_action_resolve_user_prompt(game_state, action)
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
                self.logger.warning(f"LLM响应未包含 ```json ``` 标记。尝试直接解析。响应: {response_content[:100]}...")

            try:
                response_data: Dict[str, Any] = json.loads(json_str)
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON解析失败。错误信息: {e}。原始JSON字符串: '{json_str}'。完整LLM响应: {response_content}")
                return ActionResult(
                    character_id=action.character_id,
                    action=action,
                    success=False,
                    narrative=f"系统错误：无法解析行动结果格式。原始响应: {response_content}",
                    consequences=[] # Use consequences list
                )

            # --- 行动直接后果处理 ---
            direct_consequences: List[Consequence] = []
            if "direct_consequences" in response_data and isinstance(response_data["direct_consequences"], list):
                try:
                    # Assuming direct_consequences is a list of dicts matching Consequence structure
                    direct_consequences = [Consequence(**c) for c in response_data["direct_consequences"]]
                except Exception as parse_err:
                    self.logger.warning(f"解析直接后果失败: {parse_err}. Data: {response_data['direct_consequences']}")

            # 验证 LLM 响应的基本字段 (success, narrative)
            required_keys = ['success', 'narrative']
            if not all(k in response_data for k in required_keys):
                 self.logger.warning(f"LLM响应JSON缺少必要字段 ({required_keys})。响应数据: {response_data}")
                 response_data.setdefault('success', False)
                 response_data.setdefault('narrative', '行动结果描述缺失。')

            # 创建并返回行动结果 (只包含直接后果)
            return ActionResult(
                character_id=action.character_id,
                action=action,
                success=bool(response_data.get("success", False)),
                narrative=str(response_data.get("narrative", "行动结果未描述")),
                # dice_result 字段暂时不处理
                consequences=direct_consequences # 只包含直接后果
            )
        except Exception as e:
            self.logger.exception(f"判断行动时发生意外错误: {str(e)}")
            print(f"LLM Response Content (if any): {response_content[:200]}...") # Keep print for traceback context
            # traceback.print_exc() # logger.exception includes traceback
            return ActionResult(
                character_id=action.character_id,
                action=action,
                success=False,
                narrative=f"系统内部错误：裁判处理行动时发生异常: {str(e)}",
                consequences=[]
            )

    async def determine_triggered_events_and_outcomes(self, action_results: List[ActionResult], game_state: GameState, scenario: Scenario) -> List[Dict[str, str]]:
        """
        使用LLM判断本回合触发了哪些活动事件，并为每个触发的事件选择一个结局。

        Args:
            action_results: 本回合所有行动的直接结果列表。
            game_state: 当前游戏状态。
            scenario: 当前剧本。

        Returns:
            List[Dict[str, str]]: 一个列表，每个元素是包含 "event_id" 和 "chosen_outcome_id" 的字典。
        """
        if not game_state.active_event_ids:
            self.logger.info("没有活动事件需要检查触发。")
            return []

        # 构建 Prompt using the new combined builders
        system_message_content = build_event_trigger_and_outcome_system_prompt(scenario)
        user_message_content = build_event_trigger_and_outcome_user_prompt(game_state, action_results, scenario)

        # 创建临时 Agent
        assistant_name = f"{self.agent_name}_event_trigger_helper_{uuid.uuid4()}"
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
                self.logger.warning(f"事件触发与结局选择LLM响应未包含 ```json ``` 标记。尝试直接解析。响应: {response_content[:100]}...")

            try:
                response_data = json.loads(json_str)
                # Expecting {"triggered_events": [{"event_id": "...", "chosen_outcome_id": "..."}, ...]}
                if "triggered_events" in response_data and isinstance(response_data["triggered_events"], list):
                    raw_triggered_list = response_data["triggered_events"]
                    valid_results = []
                    active_event_ids_set = set(game_state.active_event_ids)
                    scenario_event_map = {event.event_id: event for event in scenario.events} if scenario and scenario.events else {}

                    for item in raw_triggered_list:
                        if isinstance(item, dict) and "event_id" in item and "chosen_outcome_id" in item:
                            event_id = str(item["event_id"])
                            outcome_id = str(item["chosen_outcome_id"])

                            # Validate: event_id must be active and exist in scenario
                            if event_id not in active_event_ids_set or event_id not in scenario_event_map:
                                self.logger.warning(f"LLM 返回了无效或非活动的事件ID: {event_id}")
                                continue

                            # Validate: chosen_outcome_id must exist for the given event_id
                            event = scenario_event_map[event_id]
                            if not any(outcome.id == outcome_id for outcome in event.possible_outcomes):
                                self.logger.warning(f"LLM 为事件 {event_id} 返回了无效的结局ID: {outcome_id}")
                                continue

                            valid_results.append({"event_id": event_id, "chosen_outcome_id": outcome_id})
                        else:
                             self.logger.warning(f"LLM 返回的 triggered_events 列表包含无效项: {item}")

                    triggered_events_with_outcomes = valid_results
                else:
                    self.logger.warning(f"事件触发与结局选择LLM响应JSON格式不正确或缺少 'triggered_events' 列表。响应数据: {response_data}")

            except json.JSONDecodeError as e:
                self.logger.error(f"事件触发与结局选择JSON解析失败。错误: {e}。原始JSON: '{json_str}'. LLM响应: {response_content}")

        except Exception as e:
            self.logger.exception(f"判断事件触发与结局选择时发生意外错误: {str(e)}")
            print(f"LLM Response Content (if any): {response_content[:200]}...") # Keep print for traceback context

        if triggered_events_with_outcomes:
             self.logger.info(f"LLM 判断触发的事件及选定结局: {triggered_events_with_outcomes}")
        else:
             self.logger.info("LLM 判断本回合无事件触发或未能选择结局。")

        return triggered_events_with_outcomes
