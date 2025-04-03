# src/engine/round_phases/update_phase.py
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

from src.engine.round_phases.base_phase import BaseRoundPhase, PhaseContext
from src.engine.round_phases.judgement_phase import JudgementOutput # Import the new type alias
from src.models.action_models import ActionResult, PlayerAction, ActionType # Need PlayerAction for last_active_round check
from src.models.consequence_models import Consequence, ConsequenceType # Import ConsequenceType for potential filtering if needed
from src.models.message_models import Message, MessageType, MessageVisibility, SenderRole # Import SenderRole
from src.models.scenario_models import Scenario, EventOutcome # Need Scenario models for consequence extraction
from src.models.game_state_models import GameState


class UpdatePhase(BaseRoundPhase):
    """
    回合阶段：更新阶段。
    负责根据判定阶段的结果提取并应用所有后果，更新游戏状态，并检查剧本阶段推进。
    """
    def __init__(self, context: PhaseContext):
        super().__init__(context)

    async def execute(self, judgement_output: JudgementOutput, declared_actions: List[PlayerAction]) -> None:
        """
        执行更新阶段逻辑。
        1. 应用行动的属性后果。
        2. 应用触发事件的后果 (包括 Flag 设置)。
        3. 检查阶段推进。

        Args:
            judgement_output: 判定阶段返回的字典，包含 "action_results" 和 "triggered_events"。
            declared_actions: 行动宣告阶段收集的行动列表 (用于检查 last_active_round)。
        """
        self.logger.info("--- 开始更新阶段 ---")

        action_results: List[ActionResult] = judgement_output.get("action_results", [])
        triggered_events: List[Dict[str, str]] = judgement_output.get("triggered_events", [])

        all_change_descriptions: List[str] = [] # Collect all descriptions for unified broadcast

        # 1. 应用行动的属性后果
        attribute_consequences: List[Consequence] = []
        for result in action_results:
            if hasattr(result, 'consequences') and isinstance(result.consequences, list):
                # Double check: Ensure only attribute consequences are included
                attr_cons = [c for c in result.consequences if c.type != ConsequenceType.UPDATE_FLAG]
                attribute_consequences.extend(attr_cons)
            else:
                self.logger.warning(f"行动结果对象缺少 'consequences' 列表: {result}")

        if attribute_consequences:
            self.logger.info(f"步骤 1: 应用 {len(attribute_consequences)} 条行动属性后果...")
            try:
                # Access game_state_manager via context
                descriptions = await self.context.game_state_manager.apply_consequences(attribute_consequences)
                all_change_descriptions.extend(descriptions)
                self.logger.info("步骤 1 完成: 属性后果已应用。")
            except Exception as apply_error:
                self.logger.exception(f"应用行动属性后果时出错: {apply_error}")
                all_change_descriptions.append("应用行动属性后果时发生内部错误。")
        else:
            self.logger.info("步骤 1: 无行动属性后果需要应用。")

        # 2. 应用触发事件的后果 (包括 Flag 设置)
        event_consequences: List[Consequence] = []
        # Access scenario_manager via context
        current_scenario = self.context.scenario_manager.get_current_scenario()
        if triggered_events and current_scenario:
            self.logger.info(f"步骤 2: 提取并应用 {len(triggered_events)} 个触发事件的后果...")
            try:
                event_consequences = self._extract_consequences_for_chosen_outcomes(
                    triggered_events, current_scenario
                )
                if event_consequences:
                    # Access game_state_manager via context
                    descriptions = await self.context.game_state_manager.apply_consequences(event_consequences)
                    all_change_descriptions.extend(descriptions)
                    self.logger.info("步骤 2 完成: 事件后果已应用。")
                else:
                    self.logger.info("步骤 2: 触发的事件没有产生后果。")
            except Exception as apply_error:
                self.logger.exception(f"应用事件后果时出错: {apply_error}")
                all_change_descriptions.append("应用事件后果时发生内部错误。")
        elif triggered_events and not current_scenario:
             self.logger.warning("步骤 2: 触发了事件，但无法获取当前剧本，无法应用事件后果。")
        else:
            self.logger.info("步骤 2: 无事件触发，无需应用事件后果。")

        # 3. 更新 last_active_round (基于是否有实质行动或事件触发)
        current_state = self.get_current_state() # Get state after applying consequences
        has_substantive_action = any(
            action.action_type not in [ActionType.TALK, ActionType.WAIT]
            for action in declared_actions
        )
        triggered_event_this_round = bool(triggered_events)

        if has_substantive_action or triggered_event_this_round:
            current_state.last_active_round = self.current_round_id
            self.logger.info(f"回合 {self.current_round_id}: 有实质性活动或事件触发，更新 last_active_round 为 {self.current_round_id}")
        else:
             self.logger.info(f"回合 {self.current_round_id}: 无实质性活动或事件触发，last_active_round 保持为 {current_state.last_active_round}")
        # Note: GameStateManager needs to handle saving this updated state.

        # 4. 统一广播状态更新消息
        if all_change_descriptions:
            self.logger.info(f"广播 {len(all_change_descriptions)} 条状态更新消息...")
            referee_instance = self.context.referee_agent
            system_source_id = referee_instance.agent_id if referee_instance else "referee_agent"
            all_agent_ids = self.context.agent_manager.get_all_agent_ids()

            for description in all_change_descriptions:
                state_update_message = Message(
                    message_id=str(uuid.uuid4()),
                    sender_role=SenderRole.REFEREE, # 状态更新由裁判/系统触发
                    type=MessageType.EVENT_NOTIFICATION, # 使用新的类型
                    source="裁判", # 来源保持为裁判
                    source_id=system_source_id,
                    content=description,
                    timestamp=datetime.now().isoformat(),
                    visibility=MessageVisibility.PUBLIC,
                    recipients=all_agent_ids,
                    round_id=self.current_round_id
                ) # Ensure parenthesis is at the correct level
                # Correct indentation for try/except relative to the for loop
                try:
                    # Access message_dispatcher via context
                    self.context.message_dispatcher.broadcast_message(state_update_message)
                except Exception as broadcast_error:
                    self.logger.error(f"广播状态更新消息时出错: {broadcast_error}")
        else: # Ensure else aligns with the 'if all_change_descriptions:'
            self.logger.info("本回合没有状态更新消息需要广播。")

        # 5. 检查并推进剧本阶段 (在所有状态更新后)
        self.logger.debug("步骤 5: 检查阶段完成情况...")
        try:
            # advance_stage 内部包含检查逻辑，应读取更新后的 GameState.flags
            # Access game_state_manager via context
            stage_advanced = self.context.game_state_manager.advance_stage()
            if stage_advanced:
                self.logger.info("步骤 5 完成: 游戏剧本阶段已在本回合推进。")
                # TODO: Consider broadcasting a specific STAGE_ADVANCE message?
            else:
                self.logger.info("步骤 5 完成: 当前剧本阶段未完成或已是最后阶段。") # Corrected log message number
        except Exception as stage_error:
            self.logger.exception(f"检查或推进剧本阶段时出错: {stage_error}")

        self.logger.info("--- 结束更新阶段 ---")


    def _extract_consequences_for_chosen_outcomes(self, triggered_events_with_outcomes: List[Dict[str, str]], scenario: Scenario) -> List[Consequence]:
        """
        内部辅助方法：根据裁判选定的事件结局，提取相应的后果。
        (逻辑基本保持不变)
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
