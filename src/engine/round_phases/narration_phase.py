# src/engine/round_phases/narration_phase.py
import uuid
from datetime import datetime
from typing import List, Optional

from src.engine.round_phases.base_phase import BaseRoundPhase, PhaseContext
from src.models.message_models import Message, MessageType, MessageVisibility, SenderRole # Import SenderRole

# 常量定义 (可以考虑移到配置中)
DM_NARRATION_THRESHOLD = 3

class NarrationPhase(BaseRoundPhase):
    """
    回合阶段：叙事阶段。
    负责处理可选的 DM 开场叙事。
    """
    def __init__(self, context: PhaseContext):
        super().__init__(context)

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
            await self._process_dm_turn(state, round_id)
        else:
            self.logger.info(f"回合 {round_id}: 距离上次活跃 {rounds_since_active} 回合，跳过DM叙事。")

        self.logger.info("--- 结束叙事阶段 ---")


    async def _process_dm_turn(self, game_state, round_id) -> Optional[Message]:
        """
        内部方法：处理DM回合，获取DM的叙述推进并广播消息。
        (逻辑从原 RoundManager.process_dm_turn 迁移并适配)
        """
        scenario = self.scenario_manager.get_current_scenario()
        dm_agent = self.agent_manager.get_dm_agent()

        if not dm_agent:
            self.logger.error("无法获取 DM Agent 实例，跳过 DM 叙事。")
            return None

        # 提取历史消息 (如果需要)
        start_round_hist = game_state.last_active_round + 1
        end_round_hist = round_id - 1
        historical_messages = [
            msg for msg in game_state.chat_history
            if start_round_hist <= msg.round_id <= end_round_hist
        ] if start_round_hist <= end_round_hist else []


        dm_narrative = await dm_agent.dm_generate_narrative(game_state, scenario, historical_messages=historical_messages)

        if not dm_narrative:
            self.logger.info("DM决定本回合不进行叙述。")
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
