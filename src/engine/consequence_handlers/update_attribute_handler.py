# src/engine/consequence_handlers/update_attribute_handler.py
from typing import Optional

from src.engine.consequence_handlers.base_handler import BaseConsequenceHandler
# Import the specific consequence type and the union type
from src.models.consequence_models import AnyConsequence, UpdateAttributeConsequence
from src.models.game_state_models import GameState

class UpdateAttributeHandler(BaseConsequenceHandler):
    """处理 UPDATE_ATTRIBUTE 后果 (通用，用于非角色实体的属性)。"""

    async def apply(self, consequence: AnyConsequence, game_state: GameState) -> Optional[str]:
        """
        应用 UPDATE_ATTRIBUTE 后果到游戏状态，并在成功时记录。
        """
        # Type check
        if not isinstance(consequence, UpdateAttributeConsequence):
            self.logger.error(f"UpdateAttributeHandler 接收到错误的后果类型: {type(consequence)}")
            return None

        # Access fields directly
        target_id = consequence.target_entity_id
        attribute_name = consequence.attribute_name
        new_value = consequence.value # The new value is directly provided

        # Placeholder for source description
        source_description = f"来源: {consequence.type}"

        target_obj = None
        entity_type = "未知实体"
        # Find the target object (currently only supports locations)
        if target_id in game_state.location_states:
            target_obj = game_state.location_states[target_id]
            entity_type = "地点"
        # TODO: Extend to support items or other non-character entities if needed
        # elif target_id in game_state.items: # Assuming items might have stateful attributes
        #     target_obj = game_state.items[target_id]
        #     entity_type = "物品"
        else:
            desc = f"UPDATE_ATTRIBUTE 失败：未找到目标实体 ID '{target_id}' (目前仅支持地点)。"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, source_description=source_description, description=desc)
            return None

        if not hasattr(target_obj, attribute_name):
            desc = f"UPDATE_ATTRIBUTE 失败：{entity_type} '{target_id}' 没有属性 '{attribute_name}'。"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, source_description=source_description, description=desc)
            return None

        try:
            current_value = getattr(target_obj, attribute_name)

            # Simple check to avoid unnecessary updates/logging if value is the same
            if current_value == new_value:
                description = f"属性未变：{entity_type} '{target_id}' 的属性 '{attribute_name}' 值已为 '{new_value}'。"
                self.logger.debug(description)
                # Record as success, as the state matches the desired outcome
                self._create_record(consequence, game_state, success=True, source_description=source_description, description=description)
                return description

            setattr(target_obj, attribute_name, new_value)
            description = f"属性更新：{entity_type} '{target_id}' 的属性 '{attribute_name}' 已从 '{current_value}' 更新为 '{new_value}'。"
            self.logger.info(description)
            # Create record on success
            self._create_record(consequence, game_state, success=True, source_description=source_description, description=description)
            return description
        except Exception as e:
            error_desc = f"更新 {entity_type} '{target_id}' 的属性 '{attribute_name}' 时出错：{e}"
            self.logger.exception(error_desc)
            # Create record on failure
            self._create_record(consequence, game_state, success=False, source_description=source_description, description=error_desc)
            return None
