# src/engine/consequence_handlers/base_handler.py
import abc
import logging
from typing import Optional

# Import necessary models for type hinting
from src.models.consequence_models import Consequence, AppliedConsequenceRecord
from src.models.game_state_models import GameState
from datetime import datetime # For timestamp in record

class BaseConsequenceHandler(abc.ABC):
    """
    后果处理器的抽象基类。
    每个具体的处理器负责应用一种特定类型的后果，并在成功后记录结果。
    """
    def __init__(self):
        # Initialize logger for subclasses
        self.logger = logging.getLogger(self.__class__.__name__)

    @abc.abstractmethod
    async def apply(self, consequence: Consequence, game_state: GameState) -> Optional[str]:
        """
        应用后果到游戏状态，并在成功时记录 AppliedConsequenceRecord。

        Args:
            consequence: 要应用的后果对象。
            game_state: 当前的游戏状态对象 (将被直接修改)。

        Returns:
            Optional[str]: 描述状态变化的字符串，如果应用失败或无变化则返回 None。
                           此描述主要用于日志或调试，不保证一定生成。
        """
        pass

    def _create_record(self, consequence: Consequence, game_state: GameState, success: bool, description: Optional[str] = None) -> AppliedConsequenceRecord:
        """
        辅助方法：创建 AppliedConsequenceRecord。
        子类应在 apply 方法成功应用后果后调用此方法。

        Args:
            consequence: 应用的后果对象。
            game_state: 当前游戏状态 (用于获取 round_number)。
            success: 后果是否成功应用。
            description: 应用过程的描述 (可选)。

        Returns:
            AppliedConsequenceRecord: 创建的记录对象。
        """
        record = AppliedConsequenceRecord(
            record_id=f"acr_{datetime.now().strftime('%Y%m%d%H%M%S%f')}", # Unique ID
            round_number=game_state.round_number,
            timestamp=datetime.now().isoformat(),
            consequence_type=consequence.type,
            target_entity_id=consequence.target_entity_id,
            success=success,
            details=consequence.model_dump(), # Store the original consequence details
            description=description or f"Applied consequence: {consequence.type.value}"
        )
        # Add the record to the game state's list
        game_state.current_round_applied_consequences.append(record)
        self.logger.debug(f"已记录后果应用: {record.record_id} (类型: {record.consequence_type.value}, 成功: {record.success})")
        return record
