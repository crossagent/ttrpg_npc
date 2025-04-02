# src/engine/round_phases/update_phase.py
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

from src.engine.round_phases.base_phase import BaseRoundPhase, PhaseContext
from src.engine.round_phases.judgement_phase import JudgementResult # Import the type alias
from src.models.action_models import ActionResult, PlayerAction, ActionType # Need PlayerAction for last_active_round check
from src.models.consequence_models import Consequence
from src.models.message_models import Message, MessageType, MessageVisibility
from src.models.scenario_models import Scenario, EventOutcome # Need Scenario models for consequence extraction
# Avoid direct GameState import if possible, use Any or TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.models.game_state_models import GameState


class UpdatePhase(BaseRoundPhase):
    """
    回合阶段：更新阶段。
    负责根据判定阶段的结果提取并应用所有后果，更新游戏状态，并检查剧本阶段推进。
    """
    def __init__(self, context: PhaseContext):
        super().__init__(context)

    async def execute(self, judgement_result: JudgementResult, declared_actions: List[PlayerAction]) -> None:
        """
        执行更新阶段逻辑。

        Args:
            judgement_result: 判定阶段返回的结果元组 (result_type, results)。
            declared_actions: 行动宣告阶段收集的行动列表 (用于检查 last_active_round)。
        """
        self.logger.info("--- 开始更新阶段 ---")
        result_type, results = judgement_result

        # 1. 提取所有后果
        all_round_consequences: List[Consequence] = []
        triggered_event_this_round = False # Flag to help update last_active_round

        if result_type == "event_outcomes":
            self.logger.info("根据触发的事件结局提取后果...")
            # Ensure results is treated as List[Dict[str, str]]
            triggered_events_with_outcomes: List[Dict[str, str]] = results if isinstance(results, list) else []
            current_scenario = self.scenario_manager.get_current_scenario()
            if current_scenario:
                 # Use the helper method to extract consequences from chosen outcomes
                 all_round_consequences = self._extract_consequences_for_chosen_outcomes(
                     triggered_events_with_outcomes, current_scenario
                 )
                 triggered_event_this_round = bool(triggered_events_with_outcomes) # Mark if events were triggered
            else:
                 self.logger.warning("无法获取当前剧本，无法从事件结局中提取后果。")

        elif result_type == "action_results":
            self.logger.info("根据行动直接结果提取后果...")
             # Ensure results is treated as List[ActionResult]
            action_results: List[ActionResult] = results if isinstance(results, list) else []
            for result in action_results:
                 # Check if result has consequences attribute before extending
                 if hasattr(result, 'consequences') and isinstance(result.consequences, list):
                     all_round_consequences.extend(result.consequences)
                 else:
                      self.logger.warning(f"行动结果对象缺少 'consequences' 列表: {result}")

        else:
            self.logger.error(f"未知的判定结果类型: {result_type}")

        # 2. 更新 last_active_round
        # 需要检查本回合是否有实质性行动 或 是否触发了事件
        current_state_before_apply = self.get_current_state() # Get state before applying consequences
        has_substantive_action = any(
            action.action_type not in [ActionType.TALK, ActionType.WAIT]
            for action in declared_actions
        )

        if has_substantive_action or triggered_event_this_round:
            # If there was a substantive action OR an event was triggered, update last_active_round
            # We modify the state object fetched via get_current_state()
            # GameStateManager needs to ensure this change persists when apply_consequences is called or state is saved.
            current_state_before_apply.last_active_round = self.current_round_id
            self.logger.info(f"回合 {self.current_round_id}: 有实质性活动或事件触发，更新 last_active_round 为 {self.current_round_id}")
        else:
             # No substantive action AND no event triggered, keep last_active_round as is
             self.logger.info(f"回合 {self.current_round_id}: 无实质性活动或事件触发，last_active_round 保持为 {current_state_before_apply.last_active_round}")


        # 3. 应用所有后果并获取描述
        change_descriptions: List[str] = []
        if all_round_consequences:
            self.logger.info(f"准备应用本回合所有后果 ({len(all_round_consequences)} 条)")
            try:
                # 应用后果并接收描述列表
                # Pass the potentially modified state object if apply_consequences needs it
                change_descriptions = await self.game_state_manager.apply_consequences(all_round_consequences)
            except Exception as apply_error:
                self.logger.exception(f"应用后果时出错: {apply_error}")
                change_descriptions = ["应用后果时发生内部错误。"] # Provide error feedback

            # --- 广播状态更新消息 ---
            if change_descriptions:
                self.logger.info(f"广播 {len(change_descriptions)} 条状态更新消息...")
                referee_instance = self.referee # Use stored referee
                system_source_id = referee_instance.agent_id if referee_instance else "referee_agent"
                all_agent_ids = self.agent_manager.get_all_agent_ids()

                for description in change_descriptions:
                    state_update_message = Message(
                        message_id=str(uuid.uuid4()),
                        type=MessageType.SYSTEM_EVENT,
                        source="裁判",
                        source_id=system_source_id,
                        content=description,
                        timestamp=datetime.now().isoformat(),
                        visibility=MessageVisibility.PUBLIC,
                        recipients=all_agent_ids,
                        round_id=self.current_round_id
                    )
                    try:
                        self.message_dispatcher.broadcast_message(state_update_message)
                    except Exception as broadcast_error:
                        self.logger.error(f"广播状态更新消息时出错: {broadcast_error}")
            # --- 状态更新消息广播结束 ---
        else:
            self.logger.info("本回合没有需要应用的后果。")

        # 4. 检查并推进剧本阶段
        self.logger.debug("应用后果后，检查阶段完成情况...")
        try:
            # advance_stage 内部包含检查逻辑
            stage_advanced = self.game_state_manager.advance_stage()
            if stage_advanced:
                self.logger.info("游戏剧本阶段已在本回合推进。")
                # TODO: Consider broadcasting a specific STAGE_ADVANCE message?
            else:
                self.logger.debug("当前剧本阶段未完成或已是最后阶段。")
        except Exception as stage_error:
            self.logger.exception(f"检查或推进剧本阶段时出错: {stage_error}")


        self.logger.info("--- 结束更新阶段 ---")


    def _extract_consequences_for_chosen_outcomes(self, triggered_events_with_outcomes: List[Dict[str, str]], scenario: Scenario) -> List[Consequence]:
        """
        内部辅助方法：根据裁判选定的事件结局，提取相应的后果。
        (逻辑从原 RoundManager._extract_consequences_for_chosen_outcomes 迁移过来)

        Args:
            triggered_events_with_outcomes: 包含 "event_id" 和 "chosen_outcome_id" 的字典列表。
            scenario: 当前剧本。

        Returns:
            List[Consequence]: 从触发事件的选定结局中提取的后果列表。
        """
        all_event_consequences: List[Consequence] = []
        if not scenario or not scenario.events:
            self.logger.warning("无法提取事件后果，剧本或事件列表为空。")
            return all_event_consequences

        # Create a quick lookup map for events
        event_map = {event.event_id: event for event in scenario.events}

        for trigger_info in triggered_events_with_outcomes:
            event_id = trigger_info.get("event_id")
            chosen_outcome_id = trigger_info.get("chosen_outcome_id")

            if not event_id or not chosen_outcome_id:
                self.logger.warning(f"无效的事件触发信息: {trigger_info}，跳过后果提取。")
                continue

            event = event_map.get(event_id)
            if not event:
                self.logger.warning(f"无法在剧本中找到触发的事件ID: {event_id}，跳过后果提取。")
                continue

            self.logger.info(f"处理已触发事件 '{event.name}' ({event.id}) 的选定结局 '{chosen_outcome_id}'。")

            # Find the chosen outcome
            chosen_outcome: Optional[EventOutcome] = None
            if event.possible_outcomes:
                chosen_outcome = next((outcome for outcome in event.possible_outcomes if outcome.id == chosen_outcome_id), None)

            if not chosen_outcome:
                self.logger.warning(f"无法在事件 '{event.name}' 中找到选定的结局ID: {chosen_outcome_id}。")
                continue

            # 提取后果
            if chosen_outcome.consequences:
                 # Ensure consequences is a list before extending
                 if isinstance(chosen_outcome.consequences, list):
                     self.logger.debug(f"从结局 '{chosen_outcome.id}' ({chosen_outcome.description}) 提取 {len(chosen_outcome.consequences)} 条后果。")
                     all_event_consequences.extend(chosen_outcome.consequences)
                 else:
                      self.logger.warning(f"事件 '{event.name}' 结局 '{chosen_outcome.id}' 的后果不是列表: {chosen_outcome.consequences}")
            else:
                self.logger.info(f"选定结局 '{chosen_outcome.id}' 没有定义后果。")

            # TODO: (可选) 广播事件结局描述消息 (如果 JudgementPhase 没广播的话)
            # outcome_message_content = f"事件 '{event.name}' 发生结局: {chosen_outcome.description}"
            # ... create and broadcast message ...

        self.logger.info(f"共提取 {len(all_event_consequences)} 条事件触发后果。")
        return all_event_consequences
