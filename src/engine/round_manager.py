from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
import asyncio
import logging

from src.models.game_state_models import GameState
from src.models.message_models import Message, MessageType, MessageVisibility
from src.models.action_models import PlayerAction, ActionResult, ItemQuery, DiceResult
from src.models.context_models import StateUpdateRequest # May need adjustment later if state_changes format changes
from src.engine.game_state_manager import GameStateManager
from src.communication.message_dispatcher import MessageDispatcher
from src.models.scenario_models import ScenarioEvent # Ensure ScenarioEvent is imported
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
            # 如果 AgentManager 没有提供 RefereeAgent，则需要处理错误或创建默认实例
            # 这里暂时抛出错误，实际应用中可能需要更健壮的处理
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
        # 记录回合信息
        self.current_round_id = round_id
        self.round_start_time = datetime.now()
        
        # 初始化回合状态 - 使用管理器获取并修改状态
        game_state = self.game_state_manager.get_state()
        game_state.round_number = round_id
        
        # 记录日志
        self.logger.info(f"回合 {round_id} 开始于 {self.round_start_time}")
    
    async def process_dm_turn(self) -> Message:
        """
        处理DM回合，获取DM的叙述推进
        
        Returns:
            Message: DM的叙述消息
        """
        # 获取当前游戏状态和剧本
        game_state = self.game_state_manager.get_state()
        scenario = self.scenario_manager.get_current_scenario()
        
        # 通过DM代理生成叙述
        dm_agent = self.agent_manager.get_dm_agent()
        dm_narrative = await dm_agent.dm_generate_narrative(game_state, scenario)
        
        # 创建DM消息
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        dm_message = Message(
            message_id=message_id,
            type=MessageType.DM,
            source="DM", # Corrected to source
            content=dm_narrative,
            timestamp=timestamp,
            visibility=MessageVisibility.PUBLIC,
            recipients=self.agent_manager.get_all_player_ids(),
            round_id=self.current_round_id
        )
        
        # 广播DM消息
        self.message_dispatcher.broadcast_message(dm_message)
        
        # 更新游戏状态 (This might be redundant if broadcast_message updates state)
        # Consider if this specific update is still needed or handled differently
        update_request = StateUpdateRequest(
            dm_narrative=dm_narrative,
            action_context={
                "type": "dm_narration",
                "round": self.current_round_id
            }
        )
        # self.game_state_manager.update_state(update_request) # Commented out for review
        
        return dm_message

    async def process_dm_turn(self, historical_messages: Optional[List[Message]] = None) -> Message: # Add historical_messages parameter
        """
        处理DM回合，获取DM的叙述推进

        Args:
            historical_messages: 自上次活跃回合以来的历史消息 (可选)

        Returns:
            Message: DM的叙述消息
        """
        # 获取当前游戏状态和剧本
        game_state = self.game_state_manager.get_state()
        scenario = self.scenario_manager.get_current_scenario()

        # 通过DM代理生成叙述 - 将历史消息传递给Agent
        dm_agent = self.agent_manager.get_dm_agent()
        # 注意：需要确保 dm_generate_narrative 接口已更新以接收 historical_messages
        dm_narrative = await dm_agent.dm_generate_narrative(game_state, scenario, historical_messages=historical_messages)

        # 如果DM决定不叙述（例如返回空字符串），则不创建或广播消息
        if not dm_narrative:
            self.logger.info("DM决定本回合不进行叙述。")
            return None # 返回 None 表示没有生成消息

        # 创建DM消息
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        dm_message = Message(
            message_id=message_id,
            type=MessageType.DM,
            source="DM", # Corrected to source
            content=dm_narrative,
            timestamp=timestamp,
            visibility=MessageVisibility.PUBLIC,
            recipients=self.agent_manager.get_all_player_ids(),
            round_id=self.current_round_id
        )

        # 广播DM消息
        self.message_dispatcher.broadcast_message(dm_message)

        # 更新游戏状态 (This might be redundant if broadcast_message updates state)
        # Consider if this specific update is still needed or handled differently
        update_request = StateUpdateRequest(
            dm_narrative=dm_narrative,
            action_context={
                "type": "dm_narration",
                "round": self.current_round_id
            }
        )
        # self.game_state_manager.update_state(update_request) # Commented out for review

        return dm_message

    async def process_player_turns(self) -> List[PlayerAction]:
        """
        处理所有玩家回合，收集玩家行动
        使用gather模式并行处理所有玩家行动，统一处理结果
        
        Returns:
            List[PlayerAction]: 玩家行动列表
        """
        player_ids = self.agent_manager.get_all_player_ids()
        
        # 准备所有玩家的行动任务
        player_tasks = []
        player_id_to_index = {}
        
        for i, player_id in enumerate(player_ids):
            # 获取玩家代理
            player_agent = self.agent_manager.get_player_agent(player_id)
            if not player_agent:
                continue

            # 玩家决策行动（异步）
            task = player_agent.player_decide_action(self.game_state_manager.get_state(), 
                                                     self.scenario_manager.get_character_info(player_agent.character_id))
            player_tasks.append(task)
            player_id_to_index[player_id] = i
        
        # 并行等待所有玩家行动完成
        try:
            # 使用gather并行处理所有行动
            action_results_from_players = await asyncio.gather(*player_tasks)
            player_actions = []
            player_messages = []
            
            # 处理每个玩家的行动结果
            for i, player_id in enumerate(list(player_id_to_index.keys())):
                player_action = action_results_from_players[i]
                if player_action is None: # Handle potential None return from gather
                    self.logger.warning(f"玩家 {player_id} 未能决定行动。")
                    continue
                player_actions.append(player_action)
                
                # 创建玩家消息
                message_id = str(uuid.uuid4())
                timestamp = datetime.now().isoformat()
                
                player_message = Message(
                    message_id=message_id,
                    type=MessageType.PLAYER if player_action.action_type == ActionType.TALK else MessageType.ACTION,
                    source=player_id, # Corrected to source
                    content=player_action.content,
                    timestamp=timestamp,
                    visibility=MessageVisibility.PUBLIC,
                    recipients=self.agent_manager.get_all_agent_ids(),
                    round_id=self.current_round_id
                )
                player_messages.append(player_message)
            
            # 统一广播所有玩家消息
            for message in player_messages:
                self.message_dispatcher.broadcast_message(message)
            
            self.logger.info(f"所有玩家行动已完成并广播，共 {len(player_actions)} 个")
            
            return player_actions
            
        except Exception as e:
            self.logger.exception(f"处理玩家行动时出错: {str(e)}") # Use logger.exception for stack trace
            # 发生错误时返回空列表
            return []

    async def resolve_actions(self, actions: List[PlayerAction]) -> List[ActionResult]:
        """
        解析处理玩家行动的判定，并检查事件触发
        
        Args:
            actions: 玩家行动列表
            
        Returns:
            List[ActionResult]: 处理后的行动结果列表
        """
        processed_action_results: List[ActionResult] = []
        all_state_changes: Dict[str, Any] = {} # 累积所有状态变化

        # 过滤出需要解析的实质性行动（非对话类）
        substantive_actions = [action for action in actions if action.action_type == ActionType.ACTION]

        # --- Stage 1: Process each action individually ---
        for action in substantive_actions:
            try:
                # 检查前置条件（如物品检查）
                if "使用" in action.content.lower():
                    item_name = action.content.split("使用")[1].strip().split()[0]
                    item_result = self.game_state_manager.check_item(action.player_id, item_name)
                    
                    if not item_result.has_item:
                        action_result = ActionResult(
                            character_id=action.player_id,
                            action=action,
                            success=False,
                            narrative=f"{action.player_id}尝试使用{item_name}，但没有这个物品。",
                            state_changes={}
                        )
                        processed_action_results.append(action_result) 

                        # 创建并广播失败的系统消息 (客观效果)
                        message_id = str(uuid.uuid4())
                        timestamp = datetime.now().isoformat()
                        system_effect_message = Message(
                            message_id=message_id,
                            type=MessageType.SYSTEM_ACTION_RESULT,
                            source="system", # Corrected to source
                            content=f"{action.player_id} 尝试使用 {item_name} 失败：没有该物品。",
                            timestamp=timestamp,
                            visibility=MessageVisibility.PUBLIC,
                            recipients=self.agent_manager.get_all_agent_ids(), 
                            round_id=self.current_round_id
                        )
                        self.message_dispatcher.broadcast_message(system_effect_message)

                        # (Optional) Broadcast DM narrative for failure
                        message_id_narrative = str(uuid.uuid4())
                        timestamp_narrative = datetime.now().isoformat()
                        result_message = Message(
                            message_id=message_id_narrative,
                            type=MessageType.RESULT,
                            source="DM", # Corrected to source
                            content=action_result.narrative, 
                            timestamp=timestamp_narrative,
                            visibility=MessageVisibility.PUBLIC,
                            recipients=self.agent_manager.get_all_agent_ids(),
                            round_id=self.current_round_id
                        )
                        self.message_dispatcher.broadcast_message(result_message)
                        continue # 跳过后续处理

                # 检查是否需要掷骰子
                dice_result = None
                if any(keyword in action.content.lower() for keyword in ["检查", "尝试", "技能", "攻击"]):
                    raw_value = self.agent_manager.roll_dice("d20")
                    dice_result = DiceResult(
                        raw_value=raw_value,
                        modified_value=raw_value + 5,  # 简单示例
                        modifiers={"技能": 3, "属性": 2}
                    )
                    # 创建并广播骰子消息
                    message_id_dice = str(uuid.uuid4())
                    timestamp_dice = datetime.now().isoformat()
                    dice_message = Message(
                        message_id=message_id_dice,
                        type=MessageType.DICE,
                        source=action.player_id, # Corrected to source
                        content=f"掷骰结果: {dice_result.raw_value} + 修正值 {5} = {dice_result.modified_value}", 
                        timestamp=timestamp_dice,
                        visibility=MessageVisibility.PUBLIC,
                        recipients=self.agent_manager.get_all_agent_ids(),
                        round_id=self.current_round_id
                    )
                    self.message_dispatcher.broadcast_message(dice_message)

                # --- 调用 RefereeAgent 判断行动 ---
                # 不再需要查找 message_id，直接传递 PlayerAction 对象
                current_game_state = self.game_state_manager.get_state()
                temp_action_result = await self.referee_agent.judge_action(
                    action=action,
                    game_state=current_game_state,
                    scenario=self.scenario_manager.get_current_scenario()
                )

                if temp_action_result is None: # Handle potential None return from judge_action
                    self.logger.error(f"Referee未能解析行动: {action.content} 来自 {action.player_id}")
                    continue # Skip this action if resolution failed
                
                action_result = temp_action_result
                effect_description = f"[效果占位符] 玩家 {action.player_id} 执行了 '{action.content}'。 成功: {action_result.success}。" # 效果占位符
                narrative_result = action_result.narrative # 使用现有叙述作为占位符

                processed_action_results.append(action_result)

                # 创建并广播行动效果系统消息
                message_id_effect = str(uuid.uuid4())
                timestamp_effect = datetime.now().isoformat()
                system_effect_message = Message(
                    message_id=message_id_effect,
                    type=MessageType.SYSTEM_ACTION_RESULT,
                    source="system", # Corrected to source
                    content=effect_description,
                    timestamp=timestamp_effect,
                    visibility=MessageVisibility.PUBLIC,
                    recipients=self.agent_manager.get_all_agent_ids(),
                    round_id=self.current_round_id
                )
                self.message_dispatcher.broadcast_message(system_effect_message)

                # (Optional) 广播DM叙事结果
                if narrative_result:
                    message_id_narrative = str(uuid.uuid4())
                    timestamp_narrative = datetime.now().isoformat() 
                    result_message = Message(
                        message_id=message_id_narrative,
                        type=MessageType.RESULT,
                        source="DM", # Corrected to source
                        content=narrative_result,
                        timestamp=timestamp_narrative,
                        visibility=MessageVisibility.PUBLIC,
                        recipients=self.agent_manager.get_all_agent_ids(),
                        round_id=self.current_round_id
                    )
                    self.message_dispatcher.broadcast_message(result_message)

                # --- 累积行动的状态变化 ---
                if action_result.state_changes:
                     # 简单合并，后续可能需要处理冲突
                    all_state_changes.update(action_result.state_changes)
            
            except Exception as e:
                self.logger.exception(f"处理行动 '{action.content}' (来自 {action.player_id}) 时发生意外错误: {e}")
                # Optionally create a system error message or skip the action


        # --- Stage 2: 检查事件触发 (在所有行动处理后) ---
        # 注意：这里获取的状态可能尚未包含本轮行动的最终变化，取决于 update_state 的时机
        # 如果事件触发依赖本轮行动结果，可能需要调整状态更新时机或传递 action_results
        current_game_state = self.game_state_manager.get_state() 
        triggered_events = self._check_for_triggered_events(current_game_state, processed_action_results)

        for event in triggered_events:
            try:
                self.logger.info(f"事件触发: {event.name} ({event.id})")
                # --- Placeholder for resolving event outcome ---
                # event_outcome_description, event_state_changes = await dm_agent.dm_resolve_event(event, current_game_state) # 接口实现保留 PASS
                event_outcome_description = f"[事件效果占位符] 事件 '{event.name}' 被触发。"
                event_state_changes = {} # 状态变化占位符
                # --- Placeholder End ---

                # 创建并广播事件系统消息
                message_id_event = str(uuid.uuid4())
                timestamp_event = datetime.now().isoformat()
                system_event_message = Message(
                    message_id=message_id_event,
                    type=MessageType.SYSTEM_EVENT,
                    source="system", # Corrected to source
                    content=event_outcome_description,
                    timestamp=timestamp_event,
                    visibility=MessageVisibility.PUBLIC,
                    recipients=self.agent_manager.get_all_agent_ids(),
                    round_id=self.current_round_id
                )
                self.message_dispatcher.broadcast_message(system_event_message)

                # --- 累积事件的状态变化 ---
                if event_state_changes:
                    # 简单合并
                    all_state_changes.update(event_state_changes)
            except Exception as e:
                 self.logger.exception(f"处理触发事件 '{event.name}' 时发生意外错误: {e}")


        # --- Stage 3: 应用所有累积的状态变化 ---
        if all_state_changes:
            self.logger.info(f"应用累积的状态变化: {all_state_changes}")
            # 假设 update_state 接受包含 state_changes 的 StateUpdateRequest
            # 需要根据 StateUpdateRequest 的实际定义调整
            try:
                # TODO: Verify the structure expected by StateUpdateRequest and update_state
                # Assuming StateUpdateRequest can take state_changes directly for now
                update_request = StateUpdateRequest(state_changes=all_state_changes) 
                self.game_state_manager.update_state(update_request) # 调用 update_state 一次
                self.logger.info("状态变化应用成功。")
            except Exception as e:
                 # 捕获可能的 Pydantic 验证错误或其他问题
                 self.logger.exception(f"应用状态变化时出错: {e}. StateUpdateRequest 可能需要调整。变化内容: {all_state_changes}")
                 # 可以考虑如何处理错误，例如记录但不应用，或尝试部分应用
        else:
            self.logger.info("没有累积的状态变化需要应用。")


        return processed_action_results # 返回处理过的行动结果列表

    # --- 事件检查辅助方法 (占位符) ---
    def _check_for_triggered_events(self, game_state: GameState, action_results: List[ActionResult]) -> List[ScenarioEvent]:
        """检查是否有事件被触发 (占位符实现)"""
        triggered = []
        scenario = self.scenario_manager.get_current_scenario()
        if not scenario or not scenario.events:
            return triggered

        self.logger.debug("开始检查事件触发...")
        for event in scenario.events:
            # TODO: 实现真正的触发条件解析和评估逻辑
            # 例如：解析 event.trigger_condition 字符串
            #      检查 game_state 和 action_results 是否满足条件
            #      如果满足，则 triggered.append(event)
            
            # --- 简单占位符逻辑 (仅用于演示) ---
            # if "stage_02_01_01" in event.trigger_condition and game_state.round_number > 1: # 假设第二回合触发
            #     if event not in triggered: # 避免重复添加
            #        self.logger.debug(f"事件 '{event.name}' 条件满足 (占位符逻辑)")
            #        triggered.append(event)
            pass # 实际逻辑待实现

        if triggered:
            self.logger.info(f"发现 {len(triggered)} 个触发的事件 (占位符检查)")
        else:
            self.logger.debug("未发现触发的事件 (占位符检查)")
            
        return triggered
    
    def end_round(self) -> GameState:
        """
        结束回合，更新并返回最终游戏状态
        
        Returns:
            GameState: 更新后的游戏状态
        """
        # 获取当前状态
        game_state = self.game_state_manager.get_state()
        
        # 记录回合结束
        round_duration = datetime.now() - self.round_start_time
        self.logger.info(f"回合 {self.current_round_id} 结束，持续时间: {round_duration}")
        
        return game_state

    async def execute_round(self, state: GameState) -> GameState:
        """
        执行单个回合的所有步骤
        
        Args:
            state: 当前游戏状态
            
        Returns:
            GameState: 更新后的游戏状态
        """
        try:
            # 1. 开始回合
            round_id = state.round_number + 1
            self.start_round(round_id)
            
            # 2. 判断是否需要调用DM叙事
            DM_NARRATION_THRESHOLD = 3 # 安静回合阈值
            rounds_since_active = round_id - state.last_active_round
            should_call_dm = (rounds_since_active == 1) or (rounds_since_active >= DM_NARRATION_THRESHOLD)
            
            dm_message = None
            if should_call_dm:
                self.logger.info(f"回合 {round_id}: 距离上次活跃 {rounds_since_active} 回合，触发DM叙事。")
                # 筛选历史消息 (从上次活跃回合之后 到 本回合之前)
                start_round_hist = state.last_active_round + 1
                end_round_hist = round_id - 1 
                historical_messages = [
                    msg for msg in state.chat_history 
                    if start_round_hist <= msg.round_id <= end_round_hist
                ]
                # 处理DM开始叙事，传入历史消息
                dm_message = await self.process_dm_turn(historical_messages=historical_messages)
            else:
                self.logger.info(f"回合 {round_id}: 距离上次活跃 {rounds_since_active} 回合，跳过DM叙事。")

            # 3. 处理玩家回合
            player_actions = await self.process_player_turns()
            
            # 4. 确认行为影响的后果和是否触发了新的事件
            action_results = await self.resolve_actions(player_actions)

            # 5. 检查本回合是否有实质性行动，并更新last_active_round
            # 获取更新前的状态，以便更新 last_active_round
            current_state_before_end = self.game_state_manager.get_state() 
            has_substantive_action_this_round = any(
                action.action_type == ActionType.ACTION for action in player_actions
            )
            # 可以在这里加入更复杂的判断，例如检查 action_results 或事件触发
            
            if has_substantive_action_this_round:
                current_state_before_end.last_active_round = round_id
                self.logger.info(f"回合 {round_id}: 有实质性玩家行动，更新 last_active_round 为 {round_id}")
            else:
                 # 如果没有实质行动，last_active_round 保持不变 (继承自 state)
                 # 确保 current_state_before_end.last_active_round 继承了 state.last_active_round
                 current_state_before_end.last_active_round = state.last_active_round 
                 self.logger.info(f"回合 {round_id}: 无实质性玩家行动，last_active_round 保持为 {state.last_active_round}")

            # 6. 结束回合 (end_round 现在应该使用更新了 last_active_round 的状态)
            # 注意：end_round 内部可能需要调整以正确处理状态传递
            # 暂时假设 end_round 会返回最终状态，或者我们直接返回 current_state_before_end
            updated_state = self.end_round() # 确认 end_round 的实现
            # 如果 end_round 不修改状态，则需要确保 current_state_before_end 被正确返回或使用
            # 临时方案：直接使用更新了 last_active_round 的状态
            updated_state = current_state_before_end 
            
            return updated_state
        except Exception as e:
            self.logger.exception(f"回合执行过程中出现错误: {str(e)}") # Use logger.exception
            # 处理异常情况，记录错误并返回原始状态
            return state

    def should_terminate(self, state: GameState) -> bool:
        """
        判断当前回合是否满足终止条件
        
        Args:
            state: 当前游戏状态
            
        Returns:
            bool: 是否应该终止游戏
        """
        # 检查是否达到最大回合数
        if state.round_number >= state.max_rounds:
            self.logger.info(f"已达到最大回合数 {state.max_rounds}，游戏将结束")
            return True
        
        # 检查玩家状态，例如是否所有玩家都已达成目标或全部阵亡
        all_players_completed = False # Placeholder
        all_players_dead = True # Assume dead until proven otherwise

        if not state.characters: # Handle case with no characters
             self.logger.warning("游戏状态中没有角色信息，无法判断终止条件。")
             return False

        for char_id, character_ref in state.characters.items():
            # 直接访问嵌套的状态 - 需要确保 character_ref 结构正确
            try:
                 # Check if character_ref and status exist and health is accessible
                 if hasattr(character_ref, 'status') and hasattr(character_ref.status, 'health'):
                     if character_ref.status.health > 0:
                         all_players_dead = False
                 else:
                      self.logger.warning(f"角色 {char_id} 状态或健康值信息不完整，无法判断是否存活。")
                      all_players_dead = False # Assume alive if unsure
            except AttributeError as e:
                 self.logger.warning(f"访问角色 {char_id} 状态时出错: {e}。假设角色存活。")
                 all_players_dead = False


            # 检查是否完成目标 - 处理方式待定
            # if character_ref.status.goal_completed: # Example check
            #    pass # Need logic for all_players_completed
        
        # if all_players_completed: # Need actual logic
        #     self.logger.info("所有玩家都已完成目标，游戏将结束")
        #     return True
                
        if all_players_dead:
            self.logger.info("所有玩家都已阵亡，游戏将结束")
            return True
        
        return False
