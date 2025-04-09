# src/engine/round_phases/judgement_phase.py
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union

from src.engine.round_phases.base_phase import BaseRoundPhase, PhaseContext
from src.models.action_models import PlayerAction, ActionResult, ActionType
from src.models.message_models import Message, MessageType, MessageVisibility, SenderRole # Import SenderRole
from src.models.scenario_models import Scenario, EventOutcome # Ensure Scenario is imported for type hinting
# +++ Import consequence and record models +++
from src.models.consequence_models import (
    AnyConsequence, ConsequenceType, # Updated import
    AppliedConsequenceRecord, TriggeredEventRecord
)
from src.models.game_state_models import GameState
# +++ Import Agent types for checking +++
from src.agents.companion_agent import CompanionAgent
# PlayerAgent might not be strictly needed if we just check against player_character_id
from pydantic import BaseModel # +++ Import BaseModel +++


# +++ Define Pydantic model for action context +++
class ActionJudgementContext(BaseModel):
    action: PlayerAction
    needs_check: bool
    check_attribute: Optional[str]
    dice_roll_result: Optional[int]
    dice_type: str


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
        self.referee = self.agent_manager.get_referee_agent() # Assuming context provides referee_agent

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

        # 1 & 2. 评估检定、获取投骰、判定行动的直接属性后果
        self.logger.info("步骤 1 & 2: 评估检定、获取投骰、判定行动属性后果...")
        action_results: List[ActionResult] = await self._resolve_direct_actions(
            declared_actions, current_state, current_scenario, all_agent_ids
        )
        self.logger.info(f"步骤 1 & 2 完成: 获得 {len(action_results)} 个行动的属性后果。")

        # 3. 【应用】行动产生的后果 (包括属性后果和 Agent 内部生成的后果)
        all_action_consequences: List[AnyConsequence] = [] # Updated type hint
        for ar in action_results:
            # 添加裁判判定的属性后果
            all_action_consequences.extend(ar.consequences)
            # 添加 Agent 在行动宣告时生成的后果 (例如关系评估产生的)
            if ar.action and ar.action.generated_consequences:
                all_action_consequences.extend(ar.action.generated_consequences)

        if all_action_consequences:
            self.logger.info(f"步骤 3: 准备应用 {len(all_action_consequences)} 条行动产生的后果...")
            try:
                # 调用 GameStateManager 应用后果 (假设它会处理记录 AppliedConsequenceRecord)
                await self.game_state_manager.apply_consequences(all_action_consequences)
                self.logger.info("步骤 3 完成: 行动产生的后果已应用。")
            except Exception as e:
                self.logger.exception(f"应用行动产生的后果时出错: {e}")
        else:
            self.logger.info("步骤 3: 没有行动产生的后果需要应用。")


        # 4. 基于行动结果和【更新后】的状态，判断活跃事件是否触发
        triggered_events_with_outcomes: List[Dict[str, str]] = []
        if current_scenario and current_state.active_event_ids: # Check active_event_ids directly
            self.logger.info("步骤 4: 基于行动结果和当前状态判断活跃事件是否触发...")
            try:
                # Pass the action_results (with attribute consequences) to the event trigger check
                triggered_events_with_outcomes = await self.referee.determine_triggered_events_and_outcomes(
                    action_results, current_state, current_scenario # 使用更新后的 current_state
                )
                self.logger.info(f"步骤 4 完成: 触发了 {len(triggered_events_with_outcomes)} 个事件。")
            except Exception as e:
                 self.logger.exception(f"判断事件触发时出错: {e}")
                 triggered_events_with_outcomes = [] # Continue without event triggers on error
        else:
             self.logger.info("步骤 4: 无活跃事件需要检查触发。")

        # 5. 【应用】触发事件的后果，并【记录】触发的事件
        all_event_consequences: List[AnyConsequence] = [] # Updated type hint
        if triggered_events_with_outcomes:
            self.logger.info(f"步骤 5: 准备应用 {len(triggered_events_with_outcomes)} 个触发事件的后果并记录事件...")
            for event_trigger in triggered_events_with_outcomes:
                event_id = event_trigger.get("event_id")
                outcome_id = event_trigger.get("outcome_id")
                trigger_source_desc = event_trigger.get("trigger_source", "未知来源") # 获取触发来源

                if not event_id or not outcome_id:
                    self.logger.warning(f"跳过无效的事件触发记录: {event_trigger}")
                    continue

                # 获取事件结局的详细信息
                outcome: Optional[EventOutcome] = self.scenario_manager.get_event_outcome(event_id, outcome_id)

                if outcome:
                    # 收集事件结局的后果
                    if outcome.consequences:
                        all_event_consequences.extend(outcome.consequences)

                    # 创建 TriggeredEventRecord 并记录到 GameState
                    event_record = TriggeredEventRecord(
                        round_number=self.current_round_id,
                        event_id=event_id,
                        outcome_id=outcome_id,
                        trigger_source=trigger_source_desc # 使用从裁判处获取的来源描述
                    )
                    current_state.current_round_triggered_events.append(event_record)
                    self.logger.debug(f"已记录触发事件: {event_id}, 结局: {outcome_id}")
                else:
                    self.logger.warning(f"无法找到事件 '{event_id}' 的结局 '{outcome_id}'，无法应用其后果或记录。")

            # 统一应用所有事件后果
            if all_event_consequences:
                try:
                    await self.game_state_manager.apply_consequences(all_event_consequences)
                    self.logger.info(f"步骤 5 完成: 应用了 {len(all_event_consequences)} 条事件后果，记录了 {len(current_state.current_round_triggered_events)} 个触发事件。")
                except Exception as e:
                    self.logger.exception(f"应用事件产生的后果时出错: {e}")
            else:
                 self.logger.info("步骤 5 完成: 没有事件产生的后果需要应用，但记录了触发事件。")
        else:
            self.logger.info("步骤 5: 没有触发的事件需要处理。")


        # 6. 组合并返回原始判定结果 (可能不再需要，但暂时保留)
        output: JudgementOutput = {
            "action_results": action_results, # 包含属性后果
            "triggered_events": triggered_events_with_outcomes # 包含事件ID和结局ID
        }
        self.logger.info("--- 结束判定阶段 ---")
        return output


    async def _resolve_direct_actions(self,
                                      actions: List[PlayerAction],
                                      current_game_state: 'GameState', # Use type hint now
                                      current_scenario: Optional[Scenario],
                                      all_agent_ids: List[str]) -> List[ActionResult]:
        """
        内部方法：
        1. 评估每个实质性行动的检定必要性。
        2. 如果需要检定，获取投骰结果（玩家输入或AI模拟）。
        3. 调用 RefereeAgent.judge_action 判定行动的直接 **属性** 后果（传入投骰结果）。
        4. 广播结果消息。
        """
        processed_action_results: List[ActionResult] = []
        # 只处理非对话、非等待的实质性行动
        substantive_actions = [
            action for action in actions
            if action.action_type not in [ActionType.TALK, ActionType.WAIT]
        ]
        tasks = []
        # Store context needed for the judge_action call after assessment and dice roll
        # Use the new Pydantic model for type hinting
        action_context_map: Dict[int, ActionJudgementContext] = {}

        if not substantive_actions:
            self.logger.info("没有实质性行动需要裁判进行属性判定。")
            return []

        # 获取一次代理实例
        referee_instance = self.referee
        system_source_id = referee_instance.agent_id if referee_instance else "referee_agent"
        dm_agent_instance = self.agent_manager.get_dm_agent()
        dm_source_name = dm_agent_instance.agent_name if dm_agent_instance else "DM"
        dm_source_id = dm_agent_instance.agent_id if dm_agent_instance else "dm_agent"

        # 1. 评估检定必要性并准备上下文
        self.logger.info(f"评估 {len(substantive_actions)} 个实质性行动的检定必要性...")
        for i, action in enumerate(substantive_actions):
            needs_check = False
            check_attribute: Optional[str] = None
            dice_roll_result: Optional[int] = None
            dice_type = "d20" # Default dice type
            reason_for_check = f"执行行动 '{action.content}'" # Default reason

            try:
                needs_check, check_attribute = await self.referee.assess_check_necessity(action, current_game_state)

                if needs_check:
                    # Determine dice type (simple default for now)
                    if check_attribute:
                        # TODO: Could add logic here to map attributes to dice types if needed
                        reason_for_check = f"执行行动 '{action.content}' (检定: {check_attribute})"
                    else:
                        reason_for_check = f"执行行动 '{action.content}' (通用检定)"
                        self.logger.warning(f"行动 '{action.content}' 需要检定，但未指定具体属性，将使用通用检定 ({dice_type})。")

                    # Get the agent instance
                    agent = self.agent_manager.get_agent(action.character_id)
                    if not agent:
                        self.logger.warning(f"无法找到行动发起者 {action.character_id} 的 Agent 实例，跳过检定。")
                        needs_check = False # Override needs_check
                    else:
                        actor_char_instance = current_game_state.characters.get(action.character_id)
                        actor_name = actor_char_instance.name if actor_char_instance else action.character_id

                        # Check if it's the player character
                        if action.character_id == current_game_state.player_character_id:
                            self.logger.info(f"请求玩家 {actor_name} ({action.character_id}) 进行 {dice_type} 投骰...")
                            dice_roll_result = await self.context.input_handler.get_dice_roll_input(
                                character_name=actor_name,
                                character_id=action.character_id,
                                dice_type=dice_type,
                                reason=reason_for_check
                            )
                            if dice_roll_result is None:
                                 self.logger.warning(f"未能从玩家获取 {dice_type} 投骰结果，跳过检定。")
                                 needs_check = False # Override needs_check
                            else:
                                 self.logger.info(f"玩家 {actor_name} 投骰结果: {dice_roll_result}")

                        # Check if it's a CompanionAgent
                        elif isinstance(agent, CompanionAgent):
                            self.logger.info(f"请求伙伴 {agent.agent_name} ({action.character_id}) 模拟 {dice_type} 投骰...")
                            dice_roll_result = agent.simulate_dice_roll(dice_type)
                            # simulate_dice_roll already logs the result
                        else:
                            self.logger.warning(f"行动发起者 {action.character_id} ({agent.agent_name}) 不是玩家或 CompanionAgent，无法自动获取投骰结果，跳过检定。")
                            needs_check = False # Override needs_check
                else:
                     self.logger.info(f"行动 '{action.content}' 不需要检定。")

            except Exception as assess_err:
                self.logger.exception(f"评估行动 '{action.content}' 的检定必要性或获取投骰时出错: {assess_err}")
                needs_check = False # Skip check on error

            # Store context needed for the judge_action call later using the Pydantic model
            action_context_map[i] = ActionJudgementContext(
                action=action,
                needs_check=needs_check, # Store if check was performed (or intended but skipped)
                check_attribute=check_attribute,
                dice_roll_result=dice_roll_result,
                dice_type=dice_type # Store dice type for potential logging/messaging
            )

        # 2. 创建 judge_action 任务
        self.logger.info("准备调用裁判判定行动属性后果...")
        for i, context in action_context_map.items():
            # Access context using dot notation
            action = context.action
            dice_roll = context.dice_roll_result
            attribute = context.check_attribute

            # TODO: Modify RefereeAgent.judge_action to accept dice_roll_result and check_attribute
            #       and update referee_context_builder prompts accordingly.
            task = self.referee.judge_action(
                action=action,
                game_state=current_game_state,
                scenario=current_scenario,
                dice_roll_result=dice_roll,   # Pass the result (can be None)
                check_attribute=attribute     # Pass the attribute (can be None)
            )
            tasks.append(task)

        # 3. 并发执行所有判断任务
        self.logger.info(f"并发执行 {len(tasks)} 个行动属性后果判定任务...")
        try:
            results_or_exceptions = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as gather_error:
            self.logger.exception(f"asyncio.gather 在 _resolve_direct_actions 中失败: {gather_error}")
            return [] # 返回空列表或根据需要处理

        # 4. 处理结果并准备广播消息
        self.logger.info("处理判定结果并准备广播消息...")
        messages_to_broadcast = [] # 收集需要广播的消息
        for i, result_or_exc in enumerate(results_or_exceptions):
            context = action_context_map[i]
            # Access context using dot notation
            original_action = context.action
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

                # --- 准备要广播的消息 (加入投骰信息) ---
                dice_roll_info = ""
                # Access context using dot notation
                if context.needs_check and context.dice_roll_result is not None:
                     dice_roll_info = f" (检定: {context.dice_type}={context.dice_roll_result})"

                # 1. 准备系统效果消息 (简述成功/失败 + 投骰信息)
                actor_char_instance = current_game_state.characters.get(action_result.action.character_id)
                actor_name = actor_char_instance.name if actor_char_instance else action_result.action.character_id
                effect_description = f"角色 {actor_name} 尝试 '{action_result.action.content}'{dice_roll_info}。结果: {'成功' if action_result.success else '失败'}。"
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

        # 5. 在所有结果处理完毕后，统一广播消息
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
