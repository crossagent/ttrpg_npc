# src/engine/round_phases/judgement_phase.py
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union

from src.engine.round_phases.base_phase import BaseRoundPhase, PhaseContext
from src.models.action_models import PlayerAction, ActionResult, ActionType
from src.models.message_models import Message, MessageType, MessageVisibility, SenderRole # Import SenderRole
from src.models.scenario_models import Scenario # Ensure Scenario is imported for type hinting
from src.models.consequence_models import ConsequenceType # Import ConsequenceType
# Avoid direct GameState import if possible, use Any or TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.models.game_state_models import GameState


# Define a type alias for the return value of execute
# Now returns a dictionary containing both action results and triggered events
JudgementOutput = Dict[str, Union[List[ActionResult], List[Dict[str, str]]]]

class JudgementPhase(BaseRoundPhase):
    """
    回合阶段：判定阶段。
    负责判定宣告行动的属性后果，并判断活跃事件是否触发。
    """
    def __init__(self, context: PhaseContext):
        super().__init__(context)
        # Store referee agent for convenience
        self.referee = self.referee_agent # Assuming context provides referee_agent

    async def execute(self, declared_actions: List[PlayerAction]) -> JudgementOutput:
        """
        执行判定阶段逻辑。
        1. 判定所有行动的直接属性后果。
        2. 基于行动结果和状态，判断活跃事件是否触发。

        Args:
            declared_actions: 上一阶段宣告的行动列表。

        Returns:
            JudgementOutput: 一个字典，包含 "action_results" (属性后果列表)
                             和 "triggered_events" (触发的事件及结局列表)。
        """
        self.logger.info("--- 开始判定阶段 ---")

        current_state = self.get_current_state()
        current_scenario = self.scenario_manager.get_current_scenario()
        all_agent_ids = self.agent_manager.get_all_agent_ids() # Needed for message broadcasting in _resolve

        # 1. 判定所有行动的直接属性后果
        self.logger.info("步骤 1: 判定行动的直接属性后果...")
        action_results: List[ActionResult] = await self._resolve_direct_actions(
            declared_actions, current_state, current_scenario, all_agent_ids
        )
        self.logger.info(f"步骤 1 完成: 获得 {len(action_results)} 个行动的属性后果。")

        # 2. 基于行动结果和状态，判断活跃事件是否触发
        triggered_events_with_outcomes: List[Dict[str, str]] = []
        if current_scenario and current_state.active_event_ids: # Check active_event_ids directly
            self.logger.info("步骤 2: 基于行动结果判断活跃事件是否触发...")
            try:
                # Pass the action_results (with attribute consequences) to the event trigger check
                triggered_events_with_outcomes = await self.referee.determine_triggered_events_and_outcomes(
                    action_results, current_state, current_scenario
                )
                self.logger.info(f"步骤 2 完成: 触发了 {len(triggered_events_with_outcomes)} 个事件。")
            except Exception as e:
                 self.logger.exception(f"判断事件触发时出错: {e}")
                 triggered_events_with_outcomes = [] # Continue without event triggers on error
        else:
             self.logger.info("步骤 2: 无活跃事件需要检查触发。")


        # 3. 组合并返回结果
        output: JudgementOutput = {
            "action_results": action_results,
            "triggered_events": triggered_events_with_outcomes
        }
        self.logger.info("--- 结束判定阶段 ---")
        return output


    async def _resolve_direct_actions(self,
                                      actions: List[PlayerAction],
                                      current_game_state: 'GameState', # Use type hint now
                                      current_scenario: Optional[Scenario],
                                      all_agent_ids: List[str]) -> List[ActionResult]:
        """
        内部方法：解析处理玩家行动的直接 **属性** 判定结果 (调用 RefereeAgent.judge_action)。
        """
        processed_action_results: List[ActionResult] = []
        # 只处理非对话、非等待的实质性行动 (保持不变)
        substantive_actions = [
            action for action in actions
            if action.action_type not in [ActionType.TALK, ActionType.WAIT]
        ]
        tasks = []
        action_map = {} # 用于在 gather 后关联结果和原始 action
        messages_to_broadcast = [] # 收集需要广播的消息

        if not substantive_actions:
            self.logger.info("没有实质性行动需要裁判进行属性判定。")
            return []

        # 获取一次代理实例 (保持不变)
        referee_instance = self.referee
        system_source_id = referee_instance.agent_id if referee_instance else "referee_agent"
        dm_agent_instance = self.agent_manager.get_dm_agent()
        dm_source_name = dm_agent_instance.agent_name if dm_agent_instance else "DM"
        dm_source_id = dm_agent_instance.agent_id if dm_agent_instance else "dm_agent"

        # 1. 收集所有判断任务
        for i, action in enumerate(substantive_actions):
            # Call the simplified judge_action which only returns attribute consequences
            task = self.referee.judge_action(
                action=action,
                game_state=current_game_state,
                scenario=current_scenario
            )
            tasks.append(task)
            action_map[i] = action # 记录索引对应的 action

        # 2. 并发执行所有判断任务 (保持不变)
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
                self.logger.exception(f"处理行动 '{original_action.content}' (来自 {original_action.character_id}) 的属性后果时发生错误: {result_or_exc}")
                # Create a default error ActionResult
                action_result = ActionResult(
                    character_id=original_action.character_id,
                    action=original_action,
                    success=False,
                    narrative=f"系统处理行动属性后果时发生内部错误。",
                    consequences=[] # Ensure consequences is empty on error
                )
            elif result_or_exc is None:
                 self.logger.error(f"裁判未能解析行动的属性后果: {original_action.content} 来自 {original_action.character_id}")
                 action_result = ActionResult(
                     character_id=original_action.character_id,
                     action=original_action,
                     success=False,
                     narrative=f"系统无法理解行动 '{original_action.content}' 的属性后果。",
                     consequences=[]
                 )
            else:
                # We expect a valid ActionResult (with only attribute consequences)
                action_result = result_or_exc

            if action_result:
                # Ensure consequences only contain attribute types (double check)
                action_result.consequences = [
                    c for c in action_result.consequences if c.type != ConsequenceType.UPDATE_FLAG
                ]
                processed_action_results.append(action_result)

                # --- 准备要广播的消息 (保持不变, 但现在只基于属性后果) ---
                # 1. 准备系统效果消息 (简述成功/失败)
                effect_description = f"角色 {action_result.action.character_id} 尝试 '{action_result.action.content}'。结果: {'成功' if action_result.success else '失败'}。"
                message_id_effect = str(uuid.uuid4())
                timestamp_effect = datetime.now().isoformat()
                system_effect_message = Message(
                    message_id=message_id_effect,
                    sender_role=SenderRole.REFEREE, # 设置 sender_role
                    type=MessageType.ACTION_RESULT_SYSTEM, # 设置新的 message_type
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
                        sender_role=SenderRole.NARRATOR, # 设置 sender_role (DM 代理扮演叙述者)
                        type=MessageType.ACTION_RESULT_NARRATIVE, # 设置新的 message_type
                        source=dm_source_name, # 使用 DM 代理名称
                        source_id=dm_source_id, # 使用 DM 代理 ID
                        content=action_result.narrative,
                        timestamp=timestamp_narrative,
                        visibility=MessageVisibility.PUBLIC,
                        recipients=all_agent_ids,
                        round_id=self.current_round_id
                    )
                    messages_to_broadcast.append(result_message)

        # 4. 在所有结果处理完毕后，统一广播消息 (保持不变)
        if messages_to_broadcast:
            self.logger.info(f"准备广播 {len(messages_to_broadcast)} 条行动属性结果相关消息...")
            for msg in messages_to_broadcast:
                try:
                    self.message_dispatcher.broadcast_message(msg)
                except Exception as broadcast_error:
                    self.logger.error(f"广播消息 (ID: {msg.message_id}) 时出错: {broadcast_error}")
        else:
            self.logger.info("没有需要广播的行动属性结果消息。")

        self.logger.info(f"完成对 {len(processed_action_results)} 个实质性行动的属性后果判定。")
        return processed_action_results
