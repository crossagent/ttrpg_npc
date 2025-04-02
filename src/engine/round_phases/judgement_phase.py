# src/engine/round_phases/judgement_phase.py
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union

from src.engine.round_phases.base_phase import BaseRoundPhase, PhaseContext
from src.models.action_models import PlayerAction, ActionResult, ActionType
from src.models.message_models import Message, MessageType, MessageVisibility
from src.models.scenario_models import Scenario # Ensure Scenario is imported for type hinting
# Avoid direct GameState import if possible, use Any or TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.models.game_state_models import GameState


# Define a type alias for the return value of execute
JudgementResult = Tuple[str, Union[List[Dict[str, str]], List[ActionResult]]] # (result_type, results)
# result_type can be "event_outcomes" or "action_results"

class JudgementPhase(BaseRoundPhase):
    """
    回合阶段：判定阶段。
    负责根据宣告的行动进行判定，优先检查事件触发，其次判定行动直接结果。
    """
    def __init__(self, context: PhaseContext):
        super().__init__(context)
        # Store referee agent for convenience
        self.referee = self.referee_agent # Assuming context provides referee_agent

    async def execute(self, declared_actions: List[PlayerAction]) -> JudgementResult:
        """
        执行判定阶段逻辑。

        Args:
            declared_actions: 上一阶段宣告的行动列表。

        Returns:
            JudgementResult: 一个元组，包含结果类型 ("event_outcomes" 或 "action_results")
                             和对应的结果列表 (事件结局字典列表或行动结果对象列表)。
        """
        self.logger.info("--- 开始判定阶段 ---")

        current_state = self.get_current_state()
        current_scenario = self.scenario_manager.get_current_scenario()
        all_agent_ids = self.agent_manager.get_all_agent_ids()

        # 1. 优先检查事件触发
        triggered_events_with_outcomes: List[Dict[str, str]] = []
        if current_scenario and declared_actions: # Only check if there's a scenario and actions
            self.logger.debug("检查宣告的行动是否触发重大事件...")
            try:
                # Note: determine_triggered_events_and_outcomes might need adjustment
                # if it currently relies on ActionResult instead of PlayerAction.
                # Assuming it can work with PlayerAction list for now.
                # If not, we might need a preliminary light-weight action resolution first.
                # Let's assume RefereeAgent is adapted or can handle PlayerAction list.
                triggered_events_with_outcomes = await self.referee.determine_triggered_events_and_outcomes(
                    declared_actions, current_state, current_scenario
                )
            except Exception as e:
                 self.logger.exception(f"检查事件触发时出错: {e}")
                 triggered_events_with_outcomes = [] # Continue without event triggers on error

        # 2. 根据是否触发事件决定后续处理
        if triggered_events_with_outcomes:
            # --- 情况 A: 触发了重大事件 ---
            self.logger.info(f"判定阶段: 触发了 {len(triggered_events_with_outcomes)} 个重大事件。")
            # TODO: (可选) 在这里广播事件触发的消息？或者等 UpdatePhase 根据后果广播？
            # 目前仅返回事件结局信息，让 UpdatePhase 处理后果和广播。
            self.logger.info("--- 结束判定阶段 (事件触发) ---")
            return ("event_outcomes", triggered_events_with_outcomes)

        else:
            # --- 情况 B: 未触发重大事件，进行常规行动判定 ---
            self.logger.info("判定阶段: 未触发重大事件，进行常规行动判定。")
            action_results: List[ActionResult] = await self._resolve_direct_actions(
                declared_actions, current_state, current_scenario, all_agent_ids
            )
            self.logger.info("--- 结束判定阶段 (常规行动) ---")
            return ("action_results", action_results)


    async def _resolve_direct_actions(self,
                                      actions: List[PlayerAction],
                                      current_game_state: 'GameState', # Use type hint now
                                      current_scenario: Optional[Scenario],
                                      all_agent_ids: List[str]) -> List[ActionResult]:
        """
        内部方法：解析处理玩家行动的直接判定结果 (调用 RefereeAgent)。
        (逻辑从原 RoundManager.resolve_actions 迁移并适配)
        """
        processed_action_results: List[ActionResult] = []
        # 只处理非对话、非等待的实质性行动
        substantive_actions = [
            action for action in actions
            if action.action_type not in [ActionType.TALK, ActionType.WAIT]
        ]
        tasks = []
        action_map = {} # 用于在 gather 后关联结果和原始 action
        messages_to_broadcast = [] # 收集需要广播的消息

        if not substantive_actions:
            self.logger.info("没有实质性行动需要裁判进行直接判定。")
            # 返回空列表，但注意 TALK/WAIT 行动已在上一阶段处理并广播
            return []

        # 获取一次代理实例，避免在循环中重复获取
        referee_instance = self.referee # Already stored in self
        system_source_id = referee_instance.agent_id if referee_instance else "referee_agent"
        dm_agent_instance = self.agent_manager.get_dm_agent()
        dm_source_name = dm_agent_instance.agent_name if dm_agent_instance else "DM"
        dm_source_id = dm_agent_instance.agent_id if dm_agent_instance else "dm_agent"

        # 1. 收集所有判断任务
        for i, action in enumerate(substantive_actions):
            task = self.referee.judge_action(
                action=action,
                game_state=current_game_state,
                scenario=current_scenario
            )
            tasks.append(task)
            action_map[i] = action # 记录索引对应的 action

        # 2. 并发执行所有判断任务
        try:
            results_or_exceptions = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as gather_error:
            self.logger.exception(f"asyncio.gather 在 _resolve_direct_actions 中失败: {gather_error}")
            return [] # 返回空列表或根据需要处理

        # 3. 处理结果 (在 gather 完成后)
        for i, result_or_exc in enumerate(results_or_exceptions):
            original_action = action_map[i]
            action_result: Optional[ActionResult] = None

            if isinstance(result_or_exc, Exception):
                self.logger.exception(f"处理行动 '{original_action.content}' (来自 {original_action.character_id}) 时发生错误: {result_or_exc}")
                action_result = ActionResult(
                    character_id=original_action.character_id,
                    action=original_action,
                    success=False,
                    narrative=f"系统处理行动时发生内部错误。",
                    consequences=[]
                )
            elif result_or_exc is None:
                 self.logger.error(f"裁判未能解析行动: {original_action.content} 来自 {original_action.character_id}")
                 action_result = ActionResult(
                     character_id=original_action.character_id,
                     action=original_action,
                     success=False,
                     narrative=f"系统无法理解行动 '{original_action.content}'。",
                     consequences=[]
                 )
            else:
                action_result = result_or_exc # 成功的 ActionResult

            if action_result:
                processed_action_results.append(action_result)

                # --- 准备要广播的消息 ---
                # 1. 准备系统效果消息 (简述成功/失败)
                effect_description = f"角色 {action_result.action.character_id} 尝试 '{action_result.action.content}'。结果: {'成功' if action_result.success else '失败'}。"
                message_id_effect = str(uuid.uuid4())
                timestamp_effect = datetime.now().isoformat()
                system_effect_message = Message(
                    message_id=message_id_effect,
                    type=MessageType.SYSTEM_ACTION_RESULT,
                    source="裁判",
                    source_id=system_source_id,
                    content=effect_description,
                    timestamp=timestamp_effect,
                    visibility=MessageVisibility.PUBLIC,
                    recipients=all_agent_ids,
                    round_id=self.current_round_id
                )
                messages_to_broadcast.append(system_effect_message)

                # 2. 准备DM叙事结果消息 (详细描述)
                if action_result.narrative:
                    message_id_narrative = str(uuid.uuid4())
                    timestamp_narrative = datetime.now().isoformat()
                    result_message = Message(
                        message_id=message_id_narrative,
                        type=MessageType.RESULT,
                        source=dm_source_name, # 使用 DM 代理名称
                        source_id=dm_source_id, # 使用 DM 代理 ID
                        content=action_result.narrative,
                        timestamp=timestamp_narrative,
                        visibility=MessageVisibility.PUBLIC,
                        recipients=all_agent_ids,
                        round_id=self.current_round_id
                    )
                    messages_to_broadcast.append(result_message)

        # 4. 在所有结果处理完毕后，统一广播消息
        if messages_to_broadcast:
            self.logger.info(f"准备广播 {len(messages_to_broadcast)} 条行动直接结果相关消息...")
            for msg in messages_to_broadcast:
                try:
                    self.message_dispatcher.broadcast_message(msg)
                except Exception as broadcast_error:
                    self.logger.error(f"广播消息 (ID: {msg.message_id}) 时出错: {broadcast_error}")
        else:
            self.logger.info("没有需要广播的行动直接结果消息。")

        self.logger.info(f"完成对 {len(processed_action_results)} 个实质性行动的直接结果判定。")
        return processed_action_results
