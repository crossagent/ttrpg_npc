# src/engine/round_phases/narration_phase.py
import uuid
from datetime import datetime
from typing import List, Optional

from src.engine.round_phases.base_phase import BaseRoundPhase, PhaseContext
from src.models.message_models import Message, MessageType, MessageVisibility, SenderRole # Import SenderRole
from src.models.game_state_models import GameState # +++ Import GameState +++

# 常量定义 (可以考虑移到配置中)
DM_NARRATION_THRESHOLD = 3

class NarrationPhase(BaseRoundPhase):
    """
    回合阶段：叙事阶段。
    负责处理可选的 DM 开场叙事。
    """
    def __init__(self, context: PhaseContext):
        super().__init__(context)
        # Get chat history manager from context (keep for now, might be useful later)
        self.chat_history_manager = context.chat_history_manager
        # +++ Store game state manager +++
        self.game_state_manager = context.game_state_manager

    async def execute(self) -> None:
        """
        执行叙事阶段逻辑。
        """
        self.logger.info("--- 开始叙事阶段 ---")
        state = self.get_current_state()
        round_id = self.current_round_id

        # 1. 判断是否需要调用DM叙事
        rounds_since_active = round_id - state.last_active_round
        # 第一次进入游戏 (round_id=1, last_active_round=0) 或达到阈值时触发
        should_call_dm = (rounds_since_active == 1 and round_id > 0) or (rounds_since_active >= DM_NARRATION_THRESHOLD)

        if should_call_dm:
            self.logger.info(f"回合 {round_id}: 距离上次活跃 {rounds_since_active} 回合，触发DM叙事。")
            # +++ Pass previous round ID +++
            await self._process_dm_turn(round_id - 1)
        else:
            self.logger.info(f"回合 {round_id}: 距离上次活跃 {rounds_since_active} 回合，跳过DM叙事。")

        self.logger.info("--- 结束叙事阶段 ---")


    async def _process_dm_turn(self, previous_round_id: int) -> Optional[Message]:
        """
        内部方法：处理DM回合，获取DM的叙述推进并广播消息。
        使用上一回合的 GameState 快照作为上下文。
        """
        scenario = self.scenario_manager.get_current_scenario()
        dm_agent = self.agent_manager.get_dm_agent()
        current_round_id = self.current_round_id # Get current round ID from base class

        if not dm_agent:
            self.logger.error("无法获取 DM Agent 实例，跳过 DM 叙事。")
            return None

        # +++ 获取上一回合的快照 +++
        previous_snapshot: Optional[GameState] = None
        if previous_round_id >= 0: # Check if previous round exists
            previous_snapshot = self.game_state_manager.get_snapshot(previous_round_id)
            if not previous_snapshot:
                self.logger.warning(f"无法获取回合 {previous_round_id} 的快照，DM叙事可能缺少上下文。")
        else:
            self.logger.info("这是第一回合或无法确定上一回合，DM叙事将基于初始状态（如果需要）。")
            # Optionally, pass the initial state if needed, or handle None snapshot in DM agent

        # --- 调用 DM Agent 生成叙事，传递快照 ---
        # 注意：dm_generate_narrative 需要调整以接受 GameState 快照
        # 并且能够从快照的 current_round_... 字段提取信息
        try:
            dm_narrative = await dm_agent.dm_generate_narrative(
                previous_snapshot, # Pass the snapshot (or None)
                scenario
                # historical_messages=historical_messages # Removed historical messages, context comes from snapshot
            )
        except Exception as e:
            self.logger.exception(f"DM Agent 生成叙事时出错: {e}")
            dm_narrative = None # Ensure dm_narrative is None on error

        if not dm_narrative:
            self.logger.info("DM Agent 未生成叙事内容。")
            return None

        # 构建并广播消息
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        dm_source_name = dm_agent.agent_name
        dm_source_id = dm_agent.agent_id

        # 注意：接收者应该是所有 Agent，包括裁判等，以便它们了解叙事内容
        all_agent_ids = self.agent_manager.get_all_agent_ids()

        dm_message = Message(
            message_id=message_id,
            sender_role=SenderRole.NARRATOR, # 设置 sender_role
            type=MessageType.NARRATION,     # 设置新的 message_type
            source=dm_source_name,
            source_id=dm_source_id,
            content=dm_narrative,
            timestamp=timestamp,
            visibility=MessageVisibility.PUBLIC,
            recipients=all_agent_ids,
            round_id=self.current_round_id
        )
        try:
            self.message_dispatcher.broadcast_message(dm_message)
            self.logger.debug(f"广播 DM 叙事消息: {dm_narrative[:50]}...")
        except Exception as broadcast_error:
            self.logger.error(f"广播 DM 叙事消息时出错: {broadcast_error}")

        return dm_message
