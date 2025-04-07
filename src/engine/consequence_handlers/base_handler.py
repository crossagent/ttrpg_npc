# src/engine/consequence_handlers/base_handler.py
import abc
import logging
from typing import Optional, Dict, Any
import uuid # For generating unique record IDs

# Import necessary models for type hinting
from src.models.consequence_models import AnyConsequence, AppliedConsequenceRecord, ConsequenceType
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
    async def apply(self, consequence: AnyConsequence, game_state: GameState) -> Optional[str]:
        """
        应用后果到游戏状态，并在成功时记录 AppliedConsequenceRecord。

        Args:
            consequence: 要应用的后果对象 (具体类型由 discriminator 'type' 决定)。
            game_state: 当前的游戏状态对象 (将被直接修改)。

        Returns:
            Optional[str]: 描述状态变化的字符串，如果应用失败或无变化则返回 None。
                           此描述主要用于日志或调试，不保证一定生成。
        """
        pass

    def _create_record(
        self,
        consequence: AnyConsequence,
        game_state: GameState,
        success: bool,
        source_description: str, # Source description is now mandatory
        description: Optional[str] = None
    ) -> AppliedConsequenceRecord:
        """
        辅助方法：创建 AppliedConsequenceRecord 并添加到游戏状态。
        子类应在 apply 方法成功应用后果后调用此方法。

        Args:
            consequence: 应用的后果对象 (具体类型)。
            game_state: 当前游戏状态 (用于获取 round_number)。
            success: 后果是否成功应用。
            source_description: 触发此后果的来源描述。
            description: 应用过程的描述 (可选)。

        Returns:
            AppliedConsequenceRecord: 创建并添加到游戏状态的记录对象。
        """
        record_id = f"acr_{uuid.uuid4()}"
        consequence_type = consequence.type
        # Safely get target_entity_id if it exists on the specific consequence type
        target_entity_id = getattr(consequence, 'target_entity_id', None)

        record = AppliedConsequenceRecord(
            record_id=record_id,
            round_number=game_state.round_number,
            # timestamp is handled by default_factory in the model
            consequence_type=consequence_type,
            target_entity_id=target_entity_id,
            success=success,
            source_description=source_description, # Use the provided source description
            applied_consequence=consequence, # Store the specific consequence object
            description=description or f"Applied consequence: {consequence_type.value}",
            details=consequence.model_dump() # Store the specific consequence details
        )
        # Add the record to the game state's list
        game_state.current_round_applied_consequences.append(record)
        self.logger.debug(f"已记录后果应用: {record.record_id} (类型: {record.consequence_type.value}, 成功: {record.success})")
        return record
