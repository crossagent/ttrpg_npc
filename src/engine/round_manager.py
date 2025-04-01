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

    # --- 新增: 结局选择与后果提取辅助方法 ---
    def _extract_consequences_for_triggered_events(self, triggered_event_ids: List[str], scenario: Scenario, game_state: GameState) -> List[Consequence]:
        """
        根据触发的事件ID列表，确定结局并提取后果。
        (当前为占位符实现，仅选择第一个结局)

        Args:
            triggered_event_ids: 被触发的事件ID列表。
            scenario: 当前剧本。
            game_state: 当前游戏状态 (可能用于结局选择)。

        Returns:
            List[Consequence]: 从触发事件的选定结局中提取的后果列表。
        """
        all_event_consequences: List[Consequence] = []
        if not scenario or not scenario.events:
            return all_event_consequences

        for event_id in triggered_event_ids:
            event = next((e for e in scenario.events if e.event_id == event_id), None)
            if event:
                self.logger.info(f"处理已触发事件 '{event.name}' ({event.id}) 的后果。")
                if event.possible_outcomes:
                    # TODO: 实现结局选择逻辑 (Outcome Selection Logic)
                    # - 可以基于规则、随机、或 LLM 判断 (需要额外调用)
                    # - 当前简单选择第一个结局作为占位符
                    chosen_outcome: EventOutcome = event.possible_outcomes[0]
                    self.logger.info(f"为事件 '{event.name}' 选择结局: '{chosen_outcome.id}' - {chosen_outcome.description}")

                    # 提取后果
                    if chosen_outcome.consequences:
                        all_event_consequences.extend(chosen_outcome.consequences)

                    # TODO: (可选) 广播事件结局消息
                    # outcome_message_content = f"事件 '{event.name}' 发生结局: {chosen_outcome.description}"
                    # ... create and broadcast message ...

                else:
                    self.logger.warning(f"触发的事件 '{event.name}' ({event.id}) 没有定义可能的结局。")
            else:
                self.logger.warning(f"无法在剧本中找到触发的事件ID: {event_id}")

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

            # 5. 事件触发判定 (调用 RefereeAgent 的新方法)
            current_state_for_event_check = self.game_state_manager.get_state()
            scenario_for_event_check = self.scenario_manager.get_current_scenario() # Get scenario
            triggered_event_ids: List[str] = []
            if scenario_for_event_check: # Ensure scenario exists
                triggered_event_ids = await self.referee_agent.determine_triggered_event_ids(
                    action_results, current_state_for_event_check, scenario_for_event_check
                )
            else:
                self.logger.warning("无法获取当前剧本，跳过事件触发判定。")

            # 5b. 结局选择与后果提取 (基于触发的事件ID)
            triggered_event_consequences: List[Consequence] = []
            if triggered_event_ids and scenario_for_event_check:
                # Use the helper method to get consequences
                triggered_event_consequences = self._extract_consequences_for_triggered_events(
                    triggered_event_ids, scenario_for_event_check, current_state_for_event_check
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
            if has_substantive_action_this_round or triggered_event_ids: # Consider triggered events as substantive?
                current_state_before_apply.last_active_round = round_id
                self.logger.info(f"回合 {round_id}: 有实质性活动，更新 last_active_round 为 {round_id}")
            else:
                 current_state_before_apply.last_active_round = state.last_active_round
                 self.logger.info(f"回合 {round_id}: 无实质性活动，last_active_round 保持为 {state.last_active_round}")


            # --- 阶段三 TODO: 应用所有后果 ---
            if all_round_consequences:
                self.logger.info(f"准备应用本回合所有后果 ({len(all_round_consequences)} 条)")
                # await self.game_state_manager.apply_consequences(all_round_consequences) # 待阶段三实现
                # Placeholder: Log consequences instead of applying
                for i, cons in enumerate(all_round_consequences):
                    # Use model_dump_json for Pydantic v2 if available, else fallback
                    log_str = f"  后果 {i+1}: "
                    if hasattr(cons, 'model_dump_json'):
                        log_str += cons.model_dump_json(indent=2)
                    else:
                        log_str += str(cons) # Fallback
                    self.logger.debug(log_str)
            else:
                self.logger.info("本回合没有需要应用的后果。")
            # --- 阶段三 TODO 结束 ---


            # 8. 结束回合
            final_state = self.end_round()
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
