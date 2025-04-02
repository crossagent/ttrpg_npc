# src/engine/round_manager.py
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
# import asyncio # Already imported below if needed, or ensure it's present
import asyncio # Ensure asyncio is imported
import logging

from src.models.game_state_models import GameState
from src.models.message_models import Message, MessageType, MessageVisibility
from src.models.action_models import PlayerAction, ActionResult, ItemQuery, DiceResult
from src.models.consequence_models import Consequence # Import Consequence
from src.models.context_models import StateUpdateRequest # May need adjustment later if state_changes format changes
from src.engine.game_state_manager import GameStateManager
from src.communication.message_dispatcher import MessageDispatcher
from src.models.scenario_models import Scenario, ScenarioEvent, EventOutcome # Ensure Scenario models are imported
from src.engine.agent_manager import AgentManager, PlayerAgent, CompanionAgent # Import PlayerAgent and CompanionAgent
from src.engine.scenario_manager import ScenarioManager
from src.models.action_models import ActionType, PlayerAction # Ensure PlayerAction is imported
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
        # 获取 DM 代理以获取名称和 ID
        dm_agent_instance = self.agent_manager.get_dm_agent()
        if dm_agent_instance:
            dm_source_name = dm_agent_instance.agent_name
            dm_source_id = dm_agent_instance.agent_id
        else:
            self.logger.warning("无法获取 DM 代理实例，将使用默认值 'DM' 作为来源。")
            dm_source_name = "DM"
            dm_source_id = "dm_agent" # Fallback ID

        dm_message = Message(
            message_id=message_id,
            type=MessageType.DM,
            source=dm_source_name, # 使用 DM 代理名称
            source_id=dm_source_id, # 使用 DM 代理 ID
            content=dm_narrative,
            timestamp=timestamp,
            visibility=MessageVisibility.PUBLIC,
            recipients=self.agent_manager.get_all_player_ids(), # Should probably be get_all_agent_ids() to include referee? Check logic.
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
        player_actions: List[PlayerAction] = []
        # player_messages list is removed as messages are broadcasted inside the loop
        game_state = self.game_state_manager.get_state() # Get state once

        # Iterate through agents managed by AgentManager
        # agent_manager.player_agents now holds both PlayerAgent and CompanionAgent instances
        for character_id, agent in self.agent_manager.player_agents.items():
            self.logger.info(f"Processing turn for character: {character_id} (Agent Type: {type(agent).__name__})")
            player_action: Optional[PlayerAction] = None
            character_info = self.scenario_manager.get_character_info(character_id) if self.scenario_manager else None
            if not character_info:
                 self.logger.warning(f"无法获取角色 {character_id} 的信息，跳过此回合。")
                 continue

            try:
                if isinstance(agent, PlayerAgent):
                    # --- Player Agent: Generate options and wait for choice (Placeholder) ---
                    self.logger.debug(f"Agent {agent.agent_id} is PlayerAgent. Generating options...")
                    options = await agent.generate_action_options(game_state, character_info)

                    # --- Placeholder for UI Interaction ---
                    self.logger.warning(f"--- Player Input Needed for {character_id} ({agent.agent_name}) ---")
                    print(f"--- Player Input Needed for {character_id} ({agent.agent_name}) ---")
                    for idx, option in enumerate(options):
                        print(f"  {idx + 1}. [{option.action_type.name}] {option.content} (Target: {option.target})")
                        self.logger.warning(f"  {idx + 1}. [{option.action_type.name}] {option.content} (Target: {option.target})")

                    # !!! CRITICAL: Replace this placeholder with actual UI interaction logic !!!
                    # For now, automatically select the first option.
                    chosen_option = options[0] if options else None
                    self.logger.warning(f"!!! Placeholder: Automatically selecting option 1: {chosen_option}")
                    print(f"!!! Placeholder: Automatically selecting option 1: {chosen_option}")
                    # --- End Placeholder ---

                    if chosen_option:
                        # Convert chosen option to PlayerAction
                        player_action = PlayerAction(
                            character_id=character_id,
                            action_type=chosen_option.action_type,
                            content=chosen_option.content,
                            target=chosen_option.target,
                            # PlayerAgent doesn't generate internal thoughts in this flow
                            internal_thoughts="行动由玩家选择。",
                            timestamp=datetime.now().isoformat()
                        )
                    else:
                         self.logger.error(f"PlayerAgent {character_id} 未能生成有效选项或接收选择。")
                         # Create a default WAIT action
                         player_action = PlayerAction(
                             character_id=character_id,
                             action_type=ActionType.WAIT,
                             content="...",
                             target="environment",
                             internal_thoughts="未能选择行动。",
                             timestamp=datetime.now().isoformat()
                         )

                elif isinstance(agent, CompanionAgent):
                    # --- Companion Agent: Decide action autonomously ---
                    self.logger.debug(f"Agent {agent.agent_id} is CompanionAgent. Deciding action...")
                    # Note: CompanionAgent still uses the method named 'player_decide_action'
                    player_action = await agent.player_decide_action(game_state, character_info)
                else:
                    self.logger.warning(f"未知的 Agent 类型: {type(agent).__name__} for character {character_id}")
                    continue # Skip this agent

                # --- Process the decided action (either from player choice or companion AI) ---
                if player_action:
                    player_actions.append(player_action)
                    # Create and broadcast message for the action immediately
                    character_state = game_state.characters.get(character_id)
                    character_name = character_state.name if character_state else character_id
                    message_id = str(uuid.uuid4())
                    timestamp = datetime.now().isoformat()
                    message_type = MessageType.PLAYER if player_action.action_type == ActionType.TALK else MessageType.ACTION
                    message_subtype = "dialogue" if player_action.action_type == ActionType.TALK else "action_description"

                    player_message = Message(
                        message_id=message_id,
                        type=message_type,
                        source=character_name,
                        source_id=character_id,
                        content=player_action.content,
                        timestamp=timestamp,
                        visibility=MessageVisibility.PUBLIC,
                        recipients=self.agent_manager.get_all_agent_ids(),
                        round_id=self.current_round_id,
                        message_subtype=message_subtype
                    )
                    # Broadcast the message immediately
                    try:
                        self.message_dispatcher.broadcast_message(player_message)
                        self.logger.debug(f"Broadcasted action message for {character_id}: {player_message.content[:50]}...")
                    except Exception as broadcast_error:
                        self.logger.error(f"广播玩家 {character_id} 行动消息时出错: {broadcast_error}")

            except Exception as e:
                 # Log error for this specific agent's turn
                 self.logger.exception(f"处理角色 {character_id} ({type(agent).__name__}) 行动时出错: {e}")
                 # Optionally create a default WAIT action if needed, or just skip

        # Return the collected actions after processing all agents
        self.logger.info(f"完成处理所有玩家/陪玩回合，共收集 {len(player_actions)} 个行动。")
        return player_actions


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
        tasks = []
        action_map = {} # 用于在 gather 后关联结果和原始 action
        messages_to_broadcast = [] # 收集需要广播的消息

        if not substantive_actions:
            self.logger.info("没有实质性行动需要裁判判断。")
            return []

        # 获取一次状态和剧本，减少重复调用
        current_game_state = self.game_state_manager.get_state()
        current_scenario = self.scenario_manager.get_current_scenario()
        all_agent_ids = self.agent_manager.get_all_agent_ids() # 获取一次接收者列表

        # 获取一次代理实例，避免在循环中重复获取
        referee_agent_instance = self.agent_manager.get_referee_agent()
        system_source_id = referee_agent_instance.agent_id if referee_agent_instance else "referee_agent"
        dm_agent_instance = self.agent_manager.get_dm_agent()
        dm_source_name = dm_agent_instance.agent_name if dm_agent_instance else "DM"
        dm_source_id = dm_agent_instance.agent_id if dm_agent_instance else "dm_agent"

        # 1. 收集所有判断任务
        for i, action in enumerate(substantive_actions):
            task = self.referee_agent.judge_action(
                action=action,
                game_state=current_game_state,
                scenario=current_scenario
            )
            tasks.append(task)
            action_map[i] = action # 记录索引对应的 action

        # 2. 并发执行所有判断任务
        try:
            # 使用 return_exceptions=True 捕获单个任务的错误，防止 gather 提前失败
            results_or_exceptions = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as gather_error:
            self.logger.exception(f"asyncio.gather 在 resolve_actions 中失败: {gather_error}")
            # 返回空列表或根据需要处理
            return []

        # 3. 处理结果 (在 gather 完成后)
        for i, result_or_exc in enumerate(results_or_exceptions):
            original_action = action_map[i]
            action_result: Optional[ActionResult] = None

            if isinstance(result_or_exc, Exception):
                # 处理单个任务的异常
                self.logger.exception(f"处理行动 '{original_action.content}' (来自 {original_action.character_id}) 时发生错误: {result_or_exc}")
                action_result = ActionResult(
                    character_id=original_action.character_id,
                    action=original_action,
                    success=False,
                    narrative=f"系统处理行动时发生内部错误。",
                    consequences=[]
                )
            elif result_or_exc is None: # 检查 judge_action 是否可能返回 None
                 self.logger.error(f"Referee未能解析行动: {original_action.content} 来自 {original_action.character_id}")
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

                # --- 准备要广播的消息 (但不立即发送) ---
                # 1. 准备系统效果消息
                effect_description = f"玩家 {action_result.action.character_id} 执行 '{action_result.action.content}'。结果: {'成功' if action_result.success else '失败'}。"
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

                # 2. 准备DM叙事结果消息
                if action_result.narrative:
                    message_id_narrative = str(uuid.uuid4())
                    timestamp_narrative = datetime.now().isoformat()
                    result_message = Message(
                        message_id=message_id_narrative,
                        type=MessageType.RESULT,
                        source=dm_source_name,
                        source_id=dm_source_id,
                        content=action_result.narrative,
                        timestamp=timestamp_narrative,
                        visibility=MessageVisibility.PUBLIC,
                        recipients=all_agent_ids,
                        round_id=self.current_round_id
                    )
                    messages_to_broadcast.append(result_message)

        # 4. 在所有结果处理完毕后，统一广播消息
        if messages_to_broadcast:
            self.logger.info(f"准备广播 {len(messages_to_broadcast)} 条行动结果相关消息...")
            for msg in messages_to_broadcast:
                try:
                    self.message_dispatcher.broadcast_message(msg)
                except Exception as broadcast_error:
                    self.logger.error(f"广播消息 (ID: {msg.message_id}) 时出错: {broadcast_error}")
        else:
            self.logger.info("没有需要广播的行动结果消息。")


        self.logger.info(f"完成对 {len(processed_action_results)} 个实质性行动的并行结果判定。")
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


            # --- 阶段三: 应用所有后果并获取描述 ---
            change_descriptions: List[str] = []
            if all_round_consequences:
                self.logger.info(f"准备应用本回合所有后果 ({len(all_round_consequences)} 条)")
                self.logger.debug("--- 检查 all_round_consequences 内容 ---")
                for idx, cons_item in enumerate(all_round_consequences):
                    item_type = type(cons_item)
                    type_attr_value = getattr(cons_item, 'type', 'N/A')
                    type_attr_type = type(type_attr_value)
                    self.logger.debug(f"  后果 {idx}: 对象类型={item_type}, type属性值='{type_attr_value}', type属性类型={type_attr_type}")
                    # 可以在这里添加更多字段的打印，例如 cons_item 本身
                    # self.logger.debug(f"    内容: {cons_item}")
                self.logger.debug("--- 检查结束 ---")

                # 应用后果并接收描述列表
                change_descriptions = await self.game_state_manager.apply_consequences(all_round_consequences)

                # --- 广播状态更新消息 ---
                if change_descriptions:
                    self.logger.info(f"广播 {len(change_descriptions)} 条状态更新消息...")
                    referee_agent_instance = self.agent_manager.get_referee_agent()
                    system_source_id = referee_agent_instance.agent_id if referee_agent_instance else "referee_agent" # Fallback ID
                    all_agent_ids = self.agent_manager.get_all_agent_ids() # 获取所有接收者

                    for description in change_descriptions:
                        state_update_message = Message(
                            message_id=str(uuid.uuid4()),
                            type=MessageType.SYSTEM_EVENT,
                            source="裁判", # 使用 "裁判" 作为来源名称
                            source_id=system_source_id, # 使用裁判代理ID
                            content=description,
                            timestamp=datetime.now().isoformat(),
                            visibility=MessageVisibility.PUBLIC,
                            recipients=all_agent_ids,
                            round_id=self.current_round_id # 使用当前回合ID
                        )
                        try:
                            self.message_dispatcher.broadcast_message(state_update_message)
                        except Exception as broadcast_error:
                            self.logger.error(f"广播状态更新消息时出错: {broadcast_error}")
                # --- 状态更新消息广播结束 ---


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
