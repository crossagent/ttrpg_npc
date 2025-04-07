# src/engine/consequence_handlers/update_character_attribute_handler.py
from typing import Optional

from src.engine.consequence_handlers.base_handler import BaseConsequenceHandler
# Import the specific consequence type and the union type
from src.models.consequence_models import AnyConsequence, UpdateCharacterAttributeConsequence
from src.models.game_state_models import GameState

class UpdateCharacterAttributeHandler(BaseConsequenceHandler):
    """处理 UPDATE_CHARACTER_ATTRIBUTE 后果。"""

    async def apply(self, consequence: AnyConsequence, game_state: GameState) -> Optional[str]:
        """
        应用 UPDATE_CHARACTER_ATTRIBUTE 后果到游戏状态，并在成功或失败时记录。
        """
        # Type check
        if not isinstance(consequence, UpdateCharacterAttributeConsequence):
            self.logger.error(f"UpdateCharacterAttributeHandler 接收到错误的后果类型: {type(consequence)}")
            return None

        # Access fields directly
        character_id = consequence.target_entity_id
        attribute_name = consequence.attribute_name
        value_change = consequence.value # This can be a change amount or a new value

        # Placeholder for source description
        source_description = f"来源: {consequence.type.value}"

        character_instance = game_state.characters.get(character_id)
        if not character_instance:
            desc = f"UPDATE_CHARACTER_ATTRIBUTE 失败：未找到角色 ID '{character_id}'。"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, source_description=source_description, description=desc)
            return None

        # Check if the attribute exists on the CharacterAttributes model
        if not hasattr(character_instance.attributes, attribute_name):
            desc = f"UPDATE_CHARACTER_ATTRIBUTE 失败：角色 '{character_id}' 的属性集没有属性 '{attribute_name}'。"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, source_description=source_description, description=desc)
            return None

        try:
            current_value = getattr(character_instance.attributes, attribute_name)
            new_value = current_value # Initialize new_value with current_value

            # Determine how to apply the value:
            # 1. If value_change is numeric and current_value is numeric, assume additive change.
            # 2. Otherwise, assume direct assignment.
            is_numeric_change = isinstance(value_change, (int, float)) and isinstance(current_value, (int, float))

            if is_numeric_change:
                new_value = current_value + value_change
                # Optional: Add clamping logic here if needed (e.g., for HP, stats)
                # Example: if attribute_name == 'health': new_value = max(0, min(character_instance.attributes.max_health, new_value))
            else:
                # Direct assignment for non-numeric types or if value_change isn't a numeric delta
                new_value = value_change
                self.logger.debug(f"UPDATE_CHARACTER_ATTRIBUTE: 直接设置属性 '{attribute_name}' 为 '{new_value}' (类型: {type(new_value)})，原值: {current_value} (类型: {type(current_value)})。")

            # Avoid update if value hasn't changed
            if new_value == current_value:
                 description = f"角色属性未变：角色 '{character_id}' ({character_instance.name}) 的属性 '{attribute_name}' 值已为 '{new_value}'。"
                 self.logger.debug(description)
                 self._create_record(consequence, game_state, success=True, source_description=source_description, description=description)
                 return description

            setattr(character_instance.attributes, attribute_name, new_value)
            description = f"角色属性更新：角色 '{character_id}' ({character_instance.name}) 的属性 '{attribute_name}' 从 '{current_value}' 更新为 '{new_value}'。"
            if is_numeric_change:
                 description += f" (变化: {value_change:+})" # Show sign for numeric change

            self.logger.info(description)
            self._create_record(consequence, game_state, success=True, source_description=source_description, description=description)
            return description
        except Exception as e:
            desc = f"更新角色 '{character_id}' 的属性 '{attribute_name}' 时出错：{e}"
            self.logger.exception(desc)
            self._create_record(consequence, game_state, success=False, source_description=source_description, description=desc)
            return None
