# src/engine/round_phases/action_declaration_phase.py
import asyncio
import uuid
from datetime import datetime
from typing import List, Optional, Tuple, Union

from src.engine.round_phases.base_phase import BaseRoundPhase, PhaseContext
# Import InternalThoughts
from src.models.action_models import PlayerAction, ActionType, ActionOption, InternalThoughts, PlayerAssessment
from src.models.message_models import Message, MessageType, MessageVisibility, SenderRole # Import SenderRole
from src.engine.agent_manager import PlayerAgent, CompanionAgent, BaseAgent # Import BaseAgent for type hint
from src.models.game_state_models import GameState
from src.models.scenario_models import ScenarioCharacterInfo


# Helper function to create default InternalThoughts
def create_default_thoughts(reason: str = "无可用思考内容", round_id: int = 0) -> InternalThoughts:
    """创建一个符合 InternalThoughts 结构的默认对象"""
    return InternalThoughts(
        short_term_goals=[],
        primary_emotion="中立",
        psychological_state="正常",
        narrative_analysis=reason,
        other_players_assessment={}, # Empty dict for default
        perceived_risks=[],
        perceived_opportunities=[],
        last_updated=datetime.now(), # Use datetime object directly
        last_updated_round=round_id # Pass round_id if available
    )

class ActionDeclarationPhase(BaseRoundPhase):
    """
    回合阶段：行动宣告阶段。
    负责收集所有玩家和陪玩角色的行动意图，并广播宣告消息。
    """
    def __init__(self, context: PhaseContext):
        super().__init__(context)

    # +++ 修改：合并广播和记录到同一个辅助函数 +++
    async def _broadcast_and_record_action(self, player_action: PlayerAction, game_state: GameState):
        """Helper method to broadcast the action and record it to game state."""
        # 1. Broadcast the message
        if not self.context.message_dispatcher:
            self.logger.warning(f"角色 {player_action.character_id} 无法发送行动宣告：未找到 message_dispatcher。")
            # Continue to record even if broadcast fails
        else:
            character_state = game_state.characters.get(player_action.character_id)
            character_name = character_state.name if character_state else player_action.character_id
            message_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat() # Use broadcast/record time
            sender_role = SenderRole.PLAYER_CHARACTER

            if player_action.action_type == ActionType.TALK:
                message_type = MessageType.DIALOGUE
            elif player_action.action_type == ActionType.ACTION:
                message_type = MessageType.ACTION_DECLARATION
            elif player_action.action_type == ActionType.WAIT:
                message_type = MessageType.WAIT_NOTIFICATION
            else:
                message_type = MessageType.SYSTEM_INFO
                self.logger.warning(f"未知的 ActionType '{player_action.action_type}' (角色: {player_action.character_id})，消息类型设为 SYSTEM_INFO。")

            action_message = Message(
                message_id=message_id,
                sender_role=sender_role,
                type=message_type,
                source=character_name,
                source_id=player_action.character_id,
                content=player_action.content,
                timestamp=timestamp,
                visibility=MessageVisibility.PUBLIC,
                recipients=self.agent_manager.get_all_agent_ids(),
                round_id=self.current_round_id
            )
            try:
                all_agent_ids = self.agent_manager.get_all_agent_ids()
                if hasattr(self.context.message_dispatcher, 'broadcast_message'):
                    self.context.message_dispatcher.broadcast_message(action_message)
                elif hasattr(self.context.message_dispatcher, 'send_message'):
                    self.context.message_dispatcher.send_message(action_message, recipients=all_agent_ids)
                else:
                    self.logger.error(f"Message dispatcher for {player_action.character_id} has no suitable send method.")

                self.logger.debug(f"角色 {player_action.character_id} 的行动宣告消息已发送。")
            except Exception as send_err:
                self.logger.error(f"为角色 {player_action.character_id} 发送行动宣告消息时出错: {send_err}")

        # 2. Record the action to game_state
        if game_state:
            # Ensure the list exists. This check is slightly redundant if execute() guarantees init, but safe.
            if not hasattr(game_state, 'current_round_actions') or game_state.current_round_actions is None:
                self.logger.warning("'_broadcast_and_record_action' 发现 'current_round_actions' 未初始化，正在创建。")
                game_state.current_round_actions = []
            game_state.current_round_actions.append(player_action)
            self.logger.debug(f"角色 {player_action.character_id} 的行动已记录到 GameState ({len(game_state.current_round_actions)} total)。")
        else:
            self.logger.error(f"无法记录角色 {player_action.character_id} 的行动：GameState 为 None。")
    # +++ 修改结束 +++

    async def _get_player_agent_action(
        self,
        agent: PlayerAgent,
        character_id: str,
        game_state: GameState,
        character_info: ScenarioCharacterInfo
    ) -> Optional[PlayerAction]:
        """获取单个 PlayerAgent 的行动，并广播/记录。"""
        self.logger.debug(f"玩家代理 {agent.agent_id} ({character_id}) 正在生成行动选项...")
        options: List[ActionOption] = []
        try:
            options = await agent.generate_action_options(game_state, character_info)
        except Exception as gen_err:
            self.logger.error(f"玩家代理 {character_id} 生成选项时出错: {gen_err}")
            options = []

        chosen_option: Optional[ActionOption] = None
        input_handler = self.context.input_handler

        if input_handler and options:
            self.logger.info(f"使用 Input Handler 获取角色 {character_id} 的选择...")
            try:
                chosen_option = await input_handler.get_player_choice(
                    options=options,
                    character_name=character_info.name,
                    character_id=character_id
                )
            except Exception as input_err:
                self.logger.error(f"从 Input Handler 获取角色 {character_id} 选择时出错: {input_err}")
                if options:
                    chosen_option = options[0]
                    self.logger.warning(f"Input Handler 出错，自动选择第一个选项: {chosen_option}")
        elif options:
            self.logger.warning(f"未配置 Input Handler 或选项为空，将自动为角色 {character_id} 选择第一个选项。")
            chosen_option = options[0]

        player_action: Optional[PlayerAction] = None
        if chosen_option:
            self.logger.info(f"角色 {character_id} 选择了行动: [{chosen_option.action_type.name}] {chosen_option.content}")
            player_action = PlayerAction(
                character_id=character_id,
                action_type=chosen_option.action_type,
                content=chosen_option.content,
                target=chosen_option.target,
                internal_thoughts=create_default_thoughts(reason="行动由玩家选择。", round_id=self.current_round_id),
                timestamp=datetime.now().isoformat()
            )
        else:
            self.logger.error(f"玩家代理 {character_id} 未能生成有效选项或接收选择。创建默认等待行动。")
            player_action = PlayerAction(
                character_id=character_id,
                action_type=ActionType.WAIT,
                content="...",
                target="environment",
                internal_thoughts=create_default_thoughts(reason="未能选择行动。", round_id=self.current_round_id),
                timestamp=datetime.now().isoformat()
            )

        # --- 修改：调用新的合并辅助函数 ---
        if player_action:
            await self._broadcast_and_record_action(player_action, game_state)
        # --- 修改结束 ---

        return player_action # 返回创建的行动对象 (用于 gather 的结果收集)

    async def _get_companion_agent_action(
        self,
        agent: CompanionAgent,
        character_id: str,
        game_state: GameState,
        character_info: ScenarioCharacterInfo
    ) -> Optional[PlayerAction]:
        """获取单个 CompanionAgent 的行动，并广播/记录。"""
        self.logger.debug(f"陪玩代理 {agent.agent_id} ({character_id}) 正在决定行动...")
        player_action: Optional[PlayerAction] = None
        try:
            player_action = await agent.player_decide_action(game_state, character_info)
            if player_action:
                 self.logger.info(f"陪玩代理 {character_id} 决定了行动: [{player_action.action_type.name}] {player_action.content[:50]}...")
            # else: player_action remains None

        except Exception as decide_err:
            self.logger.error(f"陪玩代理 {character_id} 决定行动时出错: {decide_err}")
            player_action = None # Ensure default action is created below

        if player_action is None:
             self.logger.warning(f"陪玩代理 {character_id} 未能决定行动或出错。创建默认等待行动。")
             player_action = PlayerAction(
                 character_id=character_id,
                 action_type=ActionType.WAIT,
                 content="...",
                 target="environment",
                 internal_thoughts=create_default_thoughts(reason="未能决定行动或出错。", round_id=self.current_round_id),
                 timestamp=datetime.now().isoformat()
             )

        # --- 修改：调用新的合并辅助函数 ---
        if player_action: # Should always be true here
            await self._broadcast_and_record_action(player_action, game_state)
        # --- 修改结束 ---

        return player_action # 返回创建的行动对象 (用于 gather 的结果收集)

    async def execute(self) -> List[PlayerAction]:
        """
        执行行动宣告阶段逻辑（并行，消息广播和状态记录在任务内部完成）。

        Returns:
            List[PlayerAction]: 本回合所有宣告的玩家/陪玩行动列表 (主要用于日志或返回值)。
        """
        self.logger.info("--- 开始行动宣告阶段 (并行, 广播与记录在任务内) ---")
        tasks = []
        game_state = self.get_current_state()

        # --- 新增：在任务开始前确保 GameState 和行动列表存在并初始化 ---\n
        if not game_state:
            self.logger.error("无法执行行动宣告阶段：GameState 未初始化。")
            return [] # Cannot proceed without game state
        # Ensure current_round_actions exists and is cleared for the new phase
        self.logger.info("初始化/清空 GameState.current_round_actions。")
        game_state.current_round_actions = []
        # --- 新增结束 ---

        # 1. 创建所有代理的行动决定、广播和记录任务
        for character_id, agent in self.agent_manager.player_agents.items():
            self.logger.debug(f"为角色 {character_id} ({type(agent).__name__}) 创建行动决定、广播与记录任务...")
            character_info = self.scenario_manager.get_character_info(character_id)
            if not character_info:
                self.logger.warning(f"无法获取角色 {character_id} 的信息，跳过其行动任务创建。")
                continue

            if isinstance(agent, PlayerAgent):
                task = asyncio.create_task(
                    self._get_player_agent_action(agent, character_id, game_state, character_info),
                    name=f"PlayerActionTask_{character_id}"
                )
                tasks.append(task)
            elif isinstance(agent, CompanionAgent):
                task = asyncio.create_task(
                    self._get_companion_agent_action(agent, character_id, game_state, character_info),
                    name=f"CompanionActionTask_{character_id}"
                )
                tasks.append(task)
            else:
                self.logger.warning(f"未知的 Agent 类型: {type(agent).__name__} for character {character_id}")

        # 2. 并发执行所有任务并收集结果 (主要用于日志和返回)
        self.logger.info(f"并发执行 {len(tasks)} 个行动决定、广播与记录任务...")
        results: List[Union[PlayerAction, Exception, None]] = await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.info("所有行动决定、广播与记录任务已完成。开始收集返回结果...")

        # 3. 处理 gather 的返回结果 (主要用于日志和构建返回值列表)
        returned_actions: List[PlayerAction] = []
        failed_tasks = 0
        for i, result in enumerate(results):
            task = tasks[i]
            task_name = task.get_name() if hasattr(task, 'get_name') else f"Task_{i}"
            character_id_from_task = task_name.split('_')[-1] if '_' in task_name else f"UnknownChar_{i}"

            if isinstance(result, Exception):
                self.logger.error(f"角色 {character_id_from_task} 的行动任务在 gather 后检测到失败: {result}")
                # Note: The default action should have been created and attempted broadcast/record within the task.
                # We log the failure here. We might not get a valid PlayerAction object in 'result' to return.
                failed_tasks += 1
            elif isinstance(result, PlayerAction):
                returned_actions.append(result) # Collect successful action returns
            elif result is None:
                 # This case should ideally not happen if _get_*_action always returns a PlayerAction (even default)
                 self.logger.warning(f"角色 {character_id_from_task} 的行动任务返回 None (意外情况)。")
                 failed_tasks += 1
            else:
                self.logger.error(f"角色 {character_id_from_task} 的行动任务返回未知类型: {type(result)}")
                failed_tasks += 1

        # --- 移除：不再需要在这里统一记录行动到 GameState ---
        # (Code block removed)

        final_recorded_count = len(game_state.current_round_actions) if game_state else 0
        self.logger.info(f"收集到 {len(returned_actions)} 个有效的行动任务返回值。{failed_tasks} 个任务遇到问题。GameState 中最终记录了 {final_recorded_count} 个行动。")
        self.logger.info(f"--- 行动宣告阶段结束 ---")
        # Decide what to return. Returning the successfully gathered actions might be useful.
        return returned_actions
