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
# Removed direct import of Consequence, AnyConsequence is used via other models
# from src.models.consequence_models import Consequence
from src.models.context_models import StateUpdateRequest # May need adjustment later if state_changes format changes
from src.engine.game_state_manager import GameStateManager
from src.communication.message_dispatcher import MessageDispatcher
from src.models.scenario_models import Scenario, ScenarioEvent, EventOutcome # Ensure Scenario models are imported
from src.engine.agent_manager import AgentManager, PlayerAgent, CompanionAgent # Import PlayerAgent and CompanionAgent
from src.engine.scenario_manager import ScenarioManager
# src/engine/round_manager.py
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
import asyncio
import logging

from src.models.game_state_models import GameState
from src.models.message_models import Message, MessageType, MessageVisibility # Keep Message imports if needed elsewhere
from src.models.action_models import PlayerAction, ActionResult, ActionType # Keep Action imports
# Removed direct import of Consequence
# from src.models.consequence_models import Consequence
# from src.models.context_models import StateUpdateRequest # Likely no longer needed here
from src.engine.game_state_manager import GameStateManager
from src.communication.message_dispatcher import MessageDispatcher
from src.models.scenario_models import Scenario, ScenarioEvent, EventOutcome # Keep Scenario imports if needed elsewhere
from src.engine.agent_manager import AgentManager # Keep AgentManager import
# PlayerAgent, CompanionAgent imports likely no longer needed directly here
from src.engine.scenario_manager import ScenarioManager
from src.engine.chat_history_manager import ChatHistoryManager # Import ChatHistoryManager
from src.agents import RefereeAgent # Keep RefereeAgent import
from src.io.input_handler import UserInputHandler # Import UserInputHandler

# Import phase handlers and context
from src.engine.round_phases.base_phase import PhaseContext
from src.engine.round_phases.narration_phase import NarrationPhase
from src.engine.round_phases.action_declaration_phase import ActionDeclarationPhase
from src.engine.round_phases.judgement_phase import JudgementPhase, JudgementOutput # Changed JudgementResult to JudgementOutput
# --- Removed UpdatePhase import ---
# from src.engine.round_phases.update_phase import UpdatePhase


class RoundManager:
    """
    回合管理器类，负责协调整个回合的执行流程，通过调用不同的阶段处理器来完成。
    """

    def __init__(self, game_state_manager: GameStateManager = None,
                 message_dispatcher: MessageDispatcher = None,
                 agent_manager: AgentManager = None,
                 scenario_manager: ScenarioManager = None,
                 chat_history_manager: ChatHistoryManager = None, # Add chat_history_manager
                 input_handler: Optional[UserInputHandler] = None): # Add input_handler
        """
        初始化回合管理器

        Args:
            game_state_manager: 游戏状态管理器
            message_dispatcher: 消息分发器
            agent_manager: Agent系统
            scenario_manager: 剧本管理器
            input_handler: (可选) 用户输入处理器
        """
        self.game_state_manager = game_state_manager
        self.message_dispatcher = message_dispatcher
        self.agent_manager = agent_manager
        self.scenario_manager = scenario_manager
        self.chat_history_manager = chat_history_manager # Store chat_history_manager
        self._input_handler = input_handler # Store input_handler
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
        启动新回合，初始化状态。
        (保留此方法用于设置回合初始信息)

        Args:
            round_id: 回合ID
        """
        self.current_round_id = round_id
        self.round_start_time = datetime.now()
        game_state = self.game_state_manager.get_cur_state()
        # 确保 game_state 对象存在且有 round_number 属性
        if game_state:
            game_state.round_number = round_id
            # +++ Clear previous round's temporary records +++
            game_state.current_round_actions.clear()
            game_state.current_round_applied_consequences.clear()
            game_state.current_round_triggered_events.clear()
            self.logger.debug(f"已清空回合 {round_id} 的临时记录列表。")
        else:
            self.logger.error("无法获取游戏状态对象，无法更新回合号或清空记录！")
        self.logger.info(f"回合 {round_id} 开始于 {self.round_start_time}")

    # --- 旧的回合处理方法已被移除，逻辑迁移至 phase handlers ---

    def end_round(self) -> GameState:
        """
        结束回合，记录日志并返回最终游戏状态。
        (保留此方法用于记录回合结束信息)

        Returns:
            GameState: 回合结束时的游戏状态。
        """
        game_state = self.game_state_manager.get_cur_state()

        # +++ Create and store snapshot before logging end +++
        if game_state:
            snapshot = self.game_state_manager.create_snapshot()
            if snapshot:
                self.game_state_manager.store_snapshot(self.current_round_id, snapshot)
            else:
                self.logger.error(f"未能为回合 {self.current_round_id} 创建快照！")
        else:
            self.logger.error(f"无法获取游戏状态，无法创建回合 {self.current_round_id} 的快照！")

        # Log round end time
        if self.round_start_time: # 确保 round_start_time 已设置
            round_duration = datetime.now() - self.round_start_time
            self.logger.info(f"回合 {self.current_round_id} 结束，持续时间: {round_duration}")
        else:
            self.logger.warning(f"回合 {self.current_round_id} 结束，但未记录开始时间。")
        return game_state

    async def execute_round(self, initial_state: GameState) -> GameState:
        """
        执行单个回合的所有步骤，通过调用阶段处理器完成。

        Args:
            initial_state: 回合开始时的游戏状态。

        Returns:
            GameState: 回合结束时的游戏状态。
        """
        try:
            # 1. 开始回合
            round_id = initial_state.round_number + 1
            self.start_round(round_id) # 更新 self.current_round_id 和 game_state.round_number

            # 2. 创建阶段上下文
            context = PhaseContext(
                game_state_manager=self.game_state_manager,
                agent_manager=self.agent_manager,
                message_dispatcher=self.message_dispatcher,
                scenario_manager=self.scenario_manager,
                #referee_agent=self.referee_agent,
                chat_history_manager=self.chat_history_manager, # Pass chat_history_manager
                current_round_id=self.current_round_id,
                input_handler=self._input_handler # Pass input_handler to context
            )

            # 3. 执行叙事阶段
            narration_phase = NarrationPhase(context)
            await narration_phase.execute()

            # 4. 执行行动宣告阶段
            action_declaration_phase = ActionDeclarationPhase(context)
            declared_actions: List[PlayerAction] = await action_declaration_phase.execute()

            # 5. 执行判定阶段
            judgement_phase = JudgementPhase(context)
            judgement_output: JudgementOutput = await judgement_phase.execute(declared_actions) # Changed type hint and variable name

            # --- 移除检查回合活跃并更新 last_active_round 的逻辑 ---
            # current_game_state = self.game_state_manager.get_state()
            # if current_game_state:
            #     is_active_round = any(action.action_type != ActionType.WAIT for action in declared_actions)
            #     if is_active_round:
            #         # current_game_state.last_active_round = self.current_round_id # Removed
            #         self.logger.info(f"回合 {self.current_round_id} 被标记为活跃。") # Log adjusted
            #     else:
            #         self.logger.info(f"回合 {self.current_round_id} 无实质性行动。") # Log adjusted
            # else:
            #     self.logger.error("无法获取当前游戏状态，无法判断回合活跃度。") # Log adjusted

            # 6. 【移除】执行更新阶段
            # update_phase = UpdatePhase(context)
            # await update_phase.execute(judgement_output, declared_actions) # Pass the renamed variable
            self.logger.info("步骤 6: 更新阶段已被移除，状态更新和记录已在其他阶段完成。")

            # 7. 结束回合 (现在包含快照存储)
            final_state = self.end_round()
            return final_state

        except Exception as e:
            self.logger.exception(f"回合 {self.current_round_id} 执行过程中出现严重错误: {str(e)}")
            # 在严重错误时返回初始状态或当前状态，避免游戏崩溃
            return self.game_state_manager.get_cur_state() if self.game_state_manager else initial_state

    def should_terminate(self, state: GameState) -> bool:
        """
        判断当前回合是否满足终止条件。
        (保留此方法用于游戏循环的终止判断)

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
