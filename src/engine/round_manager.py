# src/engine/round_manager.py
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
import asyncio
import logging

from src.models.game_state_models import GameState
from src.models.message_models import Message, MessageType, MessageVisibility
from src.models.action_models import PlayerAction, ActionResult, ItemQuery, DiceResult
from src.models.consequence_models import Consequence # Import Consequence
from src.models.context_models import StateUpdateRequest # May need adjustment later if state_changes format changes
from src.engine.game_state_manager import GameStateManager
from src.communication.message_dispatcher import MessageDispatcher
from src.models.scenario_models import Scenario, ScenarioEvent, EventOutcome # Ensure Scenario models are imported
from src.engine.agent_manager import AgentManager
from src.engine.scenario_manager import ScenarioManager
from src.models.action_models import ActionType
from src.agents import RefereeAgent # 导入 RefereeAgent

class RoundManager:
    """
    回合管理器类，负责协调整个回合的执行流程，调度各个模块之间的交互。
    """

    def __init__(self, game_state_manager: GameStateManager = None,
                 message_dispatcher: MessageDispatcher = None,
                 agent_manager: AgentManager = None,
                 scenario_manager: ScenarioManager = None):
        """
        初始化回合管理器

        Args:
            game_state_manager: 游戏状态管理器
            message_dispatcher: 消息分发器
            agent_manager: Agent系统
            scenario_manager: 剧本管理器
        """
        self.game_state_manager = game_state_manager
        self.message_dispatcher = message_dispatcher
        self.agent_manager = agent_manager
        self.scenario_manager = scenario_manager
        self.referee_agent: RefereeAgent = self.agent_manager.get_referee_agent() # 获取 RefereeAgent 实例
        if not self.referee_agent:
            raise ValueError("AgentManager未能提供RefereeAgent实例")

        # 回合状态相关变量
        self.current_round_id: int = 0
        self.round_start_time: datetime = None

        # 日志配置
        self.logger = logging.getLogger("RoundManager")

    def start_round(self, round_id: int) -> None:
        """
        启动新回合，初始化状态

        Args:
            round_id: 回合ID
        """
        self.current_round_id = round_id
        self.round_start_time = datetime.now()
        game_state = self.game_state_manager.get_state()
        game_state.round_number = round_id
        self.logger.info(f"回合 {round_id} 开始于 {self.round_start_time}")

    async def process_dm_turn(self, historical_messages: Optional[List[Message]] = None) -> Optional[Message]:
        """
        处理DM回合，获取DM的叙述推进

        Args:
            historical_messages: 自上次活跃回合以来的历史消息 (可选)

        Returns:
            Optional[Message]: DM的叙述消息, 如果DM未叙述则为None
        """
        game_state = self.game_state_manager.get_state()
        scenario = self.scenario_manager.get_current_scenario()
        dm_agent = self.agent_manager.get_dm_agent()

        dm_narrative = await dm_agent.dm_generate_narrative(game_state, scenario, historical_messages=historical_messages)

        if not dm_narrative:
            self.logger.info("DM决定本回合不进行叙述。")
            return None

        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        dm_message = Message(
            message_id=message_id,
            type=MessageType.DM,
            source="DM",
            content=dm_narrative,
            timestamp=timestamp,
            visibility=MessageVisibility.PUBLIC,
            recipients=self.agent_manager.get_all_player_ids(),
            round_id=self.current_round_id
        )
        self.message_dispatcher.broadcast_message(dm_message)
        # Note: State update via StateUpdateRequest might be handled elsewhere or implicitly by message broadcasting
        return dm_message

    async def process_player_turns(self) -> List[PlayerAction]:
        """
        处理所有玩家回合，收集玩家行动
        使用gather模式并行处理所有玩家行动，统一处理结果

        Returns:
            List[PlayerAction]: 玩家行动列表
        """
        player_ids = self.agent_manager.get_all_player_ids()
        player_tasks = []
        player_id_to_index = {}

        for i, player_id in enumerate(player_ids):
            player_agent = self.agent_manager.get_player_agent(player_id)
            if not player_agent:
                continue
            character_info = self.scenario_manager.get_character_info(player_agent.character_id) if self.scenario_manager else None
            task = player_agent.player_decide_action(self.game_state_manager.get_state(), character_info)
            player_tasks.append(task)
            player_id_to_index[player_id] = i

        try:
            action_results_from_players = await asyncio.gather(*player_tasks)
            player_actions = []
            player_messages = []

            for i, player_id in enumerate(list(player_id_to_index.keys())):
                player_action = action_results_from_players[i]
                if player_action is None:
                    self.logger.warning(f"玩家 {player_id} 未能决定行动。")
                    continue
                player_actions.append(player_action)

                message_id = str(uuid.uuid4())
                timestamp = datetime.now().isoformat()
                player_message = Message(
                    message_id=message_id,
                    type=MessageType.PLAYER if player_action.action_type == ActionType.TALK else MessageType.ACTION,
                    source=player_id,
                    content=player_action.content,
                    timestamp=timestamp,
                    visibility=MessageVisibility.PUBLIC,
                    recipients=self.agent_manager.get_all_agent_ids(),
                    round_id=self.current_round_id
                )
                player_messages.append(player_message)

            for message in player_messages:
                self.message_dispatcher.broadcast_message(message)

            self.logger.info(f"所有玩家行动已完成并广播，共 {len(player_actions)} 个")
            return player_actions

        except Exception as e:
            self.logger.exception(f"处理玩家行动时出错: {str(e)}")
            return []

    async def resolve_actions(self, actions: List[PlayerAction]) -> List[ActionResult]:
        """
        解析处理玩家行动的直接判定结果 (调用 RefereeAgent)。
        不处理事件触发或状态应用。

        Args:
            actions: 玩家行动列表

        Returns:
            List[ActionResult]: 处理后的行动结果列表 (包含直接后果)
        """
        processed_action_results: List[ActionResult] = []
        substantive_actions = [action for action in actions if action.action_type == ActionType.ACTION]

        for action in substantive_actions:
            try:
                current_game_state = self.game_state_manager.get_state()
                action_result = await self.referee_agent.judge_action(
                    action=action,
                    game_state=current_game_state,
                    scenario=self.scenario_manager.get_current_scenario()
                )

                if action_result is None: # Should not happen if judge_action handles errors, but check anyway
                    self.logger.error(f"Referee未能解析行动: {action.content} 来自 {action.character_id}")
                    action_result = ActionResult(
                        character_id=action.character_id,
                        action=action,
                        success=False,
                        narrative=f"系统无法理解行动 '{action.content}'。",
                        consequences=[]
                    )

                processed_action_results.append(action_result)

                # --- 根据裁判结果广播消息 ---
                # 1. 广播系统效果消息 (客观结果)
                effect_description = f"玩家 {action.character_id} 执行 '{action.content}'。结果: {'成功' if action_result.success else '失败'}。"
                message_id_effect = str(uuid.uuid4())
                timestamp_effect = datetime.now().isoformat()
                system_effect_message = Message(
                    message_id=message_id_effect,
                    type=MessageType.SYSTEM_ACTION_RESULT,
                    source="system",
                    content=effect_description,
                    timestamp=timestamp_effect,
                    visibility=MessageVisibility.PUBLIC,
                    recipients=self.agent_manager.get_all_agent_ids(),
                    round_id=self.current_round_id
                )
                self.message_dispatcher.broadcast_message(system_effect_message)

                # 2. 广播DM叙事结果 (如果裁判代理提供了)
                if action_result.narrative:
                    message_id_narrative = str(uuid.uuid4())
                    timestamp_narrative = datetime.now().isoformat()
                    result_message = Message(
                        message_id=message_id_narrative,
                        type=MessageType.RESULT,
                        source="DM", # 叙事通常来自DM视角
                        content=action_result.narrative,
                        timestamp=timestamp_narrative,
                        visibility=MessageVisibility.PUBLIC,
                        recipients=self.agent_manager.get_all_agent_ids(),
                        round_id=self.current_round_id
                    )
                    self.message_dispatcher.broadcast_message(result_message)

            except Exception as e:
                self.logger.exception(f"处理行动 '{action.content}' (来自 {action.character_id}) 时发生意外错误: {e}")
                # Create a default failure result if an exception occurs during processing
                processed_action_results.append(ActionResult(
                    character_id=action.character_id,
                    action=action,
                    success=False,
                    narrative=f"系统处理行动时发生内部错误。",
                    consequences=[]
                ))

        self.logger.info(f"完成对 {len(processed_action_results)} 个实质性行动的直接结果判定。")
        return processed_action_results

    # --- 更新: 结局选择与后果提取辅助方法 ---
    def _extract_consequences_for_chosen_outcomes(self, triggered_events_with_outcomes: List[Dict[str, str]], scenario: Scenario) -> List[Consequence]:
        """
        根据裁判选定的事件结局，提取相应的后果。

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
                self.logger.debug(f"从结局 '{chosen_outcome.id}' ({chosen_outcome.description}) 提取 {len(chosen_outcome.consequences)} 条后果。")
                all_event_consequences.extend(chosen_outcome.consequences)
            else:
                self.logger.info(f"选定结局 '{chosen_outcome.id}' 没有定义后果。")

            # TODO: (可选) 广播事件结局消息
            # outcome_message_content = f"事件 '{event.name}' 发生结局: {chosen_outcome.description}"
            # ... create and broadcast message ...

        self.logger.info(f"共提取 {len(all_event_consequences)} 条事件触发后果。")
        return all_event_consequences


    def end_round(self) -> GameState:
        """
        结束回合，返回最终游戏状态 (注意：状态更新现在发生在 execute_round 中)

        Returns:
            GameState: 当前游戏状态
        """
        game_state = self.game_state_manager.get_state()
        round_duration = datetime.now() - self.round_start_time
        self.logger.info(f"回合 {self.current_round_id} 结束，持续时间: {round_duration}")
        return game_state

    async def execute_round(self, state: GameState) -> GameState:
        """
        执行单个回合的所有步骤

        Args:
            state: 回合开始时的游戏状态

        Returns:
            GameState: 回合结束时的游戏状态
        """
        try:
            # 1. 开始回合
            round_id = state.round_number + 1
            self.start_round(round_id) # This updates game_state.round_number internally

            # 2. 判断是否需要调用DM叙事
            DM_NARRATION_THRESHOLD = 3
            rounds_since_active = round_id - state.last_active_round
            should_call_dm = (rounds_since_active == 1) or (rounds_since_active >= DM_NARRATION_THRESHOLD)

            if should_call_dm:
                self.logger.info(f"回合 {round_id}: 距离上次活跃 {rounds_since_active} 回合，触发DM叙事。")
                start_round_hist = state.last_active_round + 1
                end_round_hist = round_id - 1
                historical_messages = [
                    msg for msg in state.chat_history
                    if start_round_hist <= msg.round_id <= end_round_hist
                ]
                await self.process_dm_turn(historical_messages=historical_messages)
            else:
                self.logger.info(f"回合 {round_id}: 距离上次活跃 {rounds_since_active} 回合，跳过DM叙事。")

            # 3. 处理玩家回合
            player_actions = await self.process_player_turns()

            # 4. 解析每个行动的直接结果
            action_results: List[ActionResult] = await self.resolve_actions(player_actions)

            # 5. 事件触发判定与结局选择 (调用 RefereeAgent 的合并方法)
            current_state_for_event_check = self.game_state_manager.get_state()
            scenario_for_event_check = self.scenario_manager.get_current_scenario()
            triggered_events_with_outcomes: List[Dict[str, str]] = []
            if scenario_for_event_check:
                triggered_events_with_outcomes = await self.referee_agent.determine_triggered_events_and_outcomes(
                    action_results, current_state_for_event_check, scenario_for_event_check
                )
            else:
                self.logger.warning("无法获取当前剧本，跳过事件触发与结局选择。")

            # 5b. 后果提取 (基于选定的结局)
            triggered_event_consequences: List[Consequence] = []
            if triggered_events_with_outcomes and scenario_for_event_check:
                # Use the updated helper method
                triggered_event_consequences = self._extract_consequences_for_chosen_outcomes(
                    triggered_events_with_outcomes, scenario_for_event_check
                )

            # 6. 整合所有后果
            all_round_consequences: List[Consequence] = []
            for result in action_results:
                all_round_consequences.extend(result.consequences) # 添加行动直接后果
            all_round_consequences.extend(triggered_event_consequences) # 添加事件触发后果

            # 7. 检查本回合是否有实质性行动，并更新last_active_round
            current_state_before_apply = self.game_state_manager.get_state() # Get state again before potential update
            has_substantive_action_this_round = any(
                action.action_type == ActionType.ACTION for action in player_actions
            )
            # Consider triggered events as substantive activity as well
            if has_substantive_action_this_round or triggered_events_with_outcomes:
                current_state_before_apply.last_active_round = round_id
                self.logger.info(f"回合 {round_id}: 有实质性活动，更新 last_active_round 为 {round_id}")
            else:
                 current_state_before_apply.last_active_round = state.last_active_round
                 self.logger.info(f"回合 {round_id}: 无实质性活动，last_active_round 保持为 {state.last_active_round}")


            # --- 阶段三: 应用所有后果 ---
            if all_round_consequences:
                self.logger.info(f"准备应用本回合所有后果 ({len(all_round_consequences)} 条)")
                await self.game_state_manager.apply_consequences(all_round_consequences) # 应用后果

                # --- 阶段三: 检查并推进阶段 ---
                self.logger.debug("应用后果后，检查阶段完成情况...")
                # advance_stage already includes check_stage_completion internally
                stage_advanced = self.game_state_manager.advance_stage()
                if stage_advanced:
                    self.logger.info("游戏阶段已在本回合推进。")
                else:
                    self.logger.debug("当前阶段未完成或已是最后阶段。")
                # --- 阶段三结束 ---

            else:
                self.logger.info("本回合没有需要应用的后果。")
            # --- 后果应用与阶段推进结束 ---


            # 8. 结束回合
            final_state = self.end_round() # Note: end_round just logs and returns state now
            return final_state

        except Exception as e:
            self.logger.exception(f"回合 {self.current_round_id} 执行过程中出现错误: {str(e)}")
            return state # Return original state on error

    def should_terminate(self, state: GameState) -> bool:
        """
        判断当前回合是否满足终止条件

        Args:
            state: 当前游戏状态

        Returns:
            bool: 是否应该终止游戏
        """
        if state.round_number >= state.max_rounds:
            self.logger.info(f"已达到最大回合数 {state.max_rounds}，游戏将结束")
            return True

        all_players_dead = True
        if not state.characters:
             self.logger.warning("游戏状态中没有角色信息，无法判断终止条件。")
             return False

        for char_id, character_ref in state.characters.items():
            try:
                 if hasattr(character_ref, 'status') and hasattr(character_ref.status, 'health'):
                     if character_ref.status.health > 0:
                         all_players_dead = False
                         break # No need to check further if one player is alive
                 else:
                      self.logger.warning(f"角色 {char_id} 状态或健康值信息不完整，无法判断是否存活。")
                      all_players_dead = False
                      break
            except AttributeError as e:
                 self.logger.warning(f"访问角色 {char_id} 状态时出错: {e}。假设角色存活。")
                 all_players_dead = False
                 break

        if all_players_dead:
            self.logger.info("所有玩家都已阵亡，游戏将结束")
            return True

        # TODO: Add check for goal completion if applicable

        return False
