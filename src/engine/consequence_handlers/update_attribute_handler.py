# src/engine/consequence_handlers/update_attribute_handler.py
from typing import Optional
from operator import add, sub, mul, truediv

from src.engine.consequence_handlers.base_handler import BaseConsequenceHandler
from src.models.consequence_models import Consequence
from src.models.game_state_models import GameState

class UpdateAttributeHandler(BaseConsequenceHandler):
    """处理 UPDATE_ATTRIBUTE 后果 (通用，目前主要用于地点属性)。"""

    async def apply(self, consequence: Consequence, game_state: GameState) -> Optional[str]:
        """
        应用 UPDATE_ATTRIBUTE 后果到游戏状态，并在成功时记录。
        """
        if not consequence.target_entity_id or not consequence.attribute_name:
            self.logger.warning(f"无效的 UPDATE_ATTRIBUTE 后果：缺少 target_entity_id 或 attribute_name。 {consequence}")
            self._create_record(consequence, game_state, success=False, description="缺少 target_entity_id 或 attribute_name")
            return None

        target_obj = None
        # 目前只查找地点状态
        if consequence.target_entity_id in game_state.location_states:
            target_obj = game_state.location_states[consequence.target_entity_id]
        # TODO: 未来可能需要扩展到其他实体类型 (e.g., items with states)
        else:
            self.logger.warning(f"UPDATE_ATTRIBUTE 失败：未找到目标实体 ID '{consequence.target_entity_id}' (目前仅支持地点)。")
            self._create_record(consequence, game_state, success=False, description=f"未找到目标实体 ID '{consequence.target_entity_id}'")
            return None

        if not hasattr(target_obj, consequence.attribute_name):
            self.logger.warning(f"UPDATE_ATTRIBUTE 失败：目标实体 '{consequence.target_entity_id}' 没有属性 '{consequence.attribute_name}'。")
            self._create_record(consequence, game_state, success=False, description=f"目标实体没有属性 '{consequence.attribute_name}'")
            return None

        try:
            current_value = getattr(target_obj, consequence.attribute_name)
            new_value = consequence.value # Default to direct assignment

            # Handle simple arithmetic operations if value is structured
            if isinstance(consequence.value, dict) and "op" in consequence.value and "amount" in consequence.value:
                op_str = consequence.value["op"]
                amount = consequence.value["amount"]
                ops = {"+=": add, "-=": sub, "*=": mul, "/=": truediv, "=": lambda x, y: y}
                if op_str in ops and isinstance(current_value, (int, float)) and isinstance(amount, (int, float)):
                    new_value = ops[op_str](current_value, amount)
                else:
                    self.logger.warning(f"UPDATE_ATTRIBUTE: 不支持的操作 '{op_str}' 或类型不匹配 ({type(current_value)}, {type(amount)}) for attribute '{consequence.attribute_name}' on '{consequence.target_entity_id}'. Performing direct set.")
                    # Fallback to setting the amount directly if op fails, or keep original value if amount is not suitable?
                    # Let's fallback to setting the 'amount' field directly if it exists, otherwise keep original value
                    new_value = amount # Fallback to setting the amount directly

            setattr(target_obj, consequence.attribute_name, new_value)
            description = f"属性更新：实体 '{consequence.target_entity_id}' 的属性 '{consequence.attribute_name}' 已从 '{current_value}' 更新为 '{new_value}'。"
            self.logger.info(description)
            # Create record on success
            self._create_record(consequence, game_state, success=True, description=description)
            return description
        except Exception as e:
            error_desc = f"更新属性 '{consequence.attribute_name}' 时出错：{e}"
            self.logger.exception(error_desc)
            # Create record on failure
            self._create_record(consequence, game_state, success=False, description=error_desc)
            return None
