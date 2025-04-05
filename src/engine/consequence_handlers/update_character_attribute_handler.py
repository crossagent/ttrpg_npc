# src/engine/consequence_handlers/update_character_attribute_handler.py
from typing import Optional

from src.engine.consequence_handlers.base_handler import BaseConsequenceHandler
from src.models.consequence_models import Consequence
from src.models.game_state_models import GameState

class UpdateCharacterAttributeHandler(BaseConsequenceHandler):
    """处理 UPDATE_CHARACTER_ATTRIBUTE 后果。"""

    async def apply(self, consequence: Consequence, game_state: GameState) -> Optional[str]:
        """
        应用 UPDATE_CHARACTER_ATTRIBUTE 后果到游戏状态，并在成功或失败时记录。
        """
        if not consequence.target_entity_id or not consequence.attribute_name or consequence.value is None:
            desc = f"无效的 UPDATE_CHARACTER_ATTRIBUTE 后果：缺少 target_entity_id, attribute_name 或 value。 {consequence}"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None

        character_instance = game_state.characters.get(consequence.target_entity_id)
        if not character_instance:
            desc = f"UPDATE_CHARACTER_ATTRIBUTE 失败：未找到角色 ID '{consequence.target_entity_id}'。"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None

        if not hasattr(character_instance.attributes, consequence.attribute_name):
            desc = f"UPDATE_CHARACTER_ATTRIBUTE 失败：角色 '{consequence.target_entity_id}' 的属性集没有属性 '{consequence.attribute_name}'。"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None

        try:
            current_value = getattr(character_instance.attributes, consequence.attribute_name)
            change_value = consequence.value
            new_value = current_value

            # Assume value is the change amount (e.g., +1, -2) for numeric types
            if isinstance(change_value, (int, float)) and isinstance(current_value, (int, float)):
                new_value = current_value + change_value
            else:
                # Fallback: try direct assignment if types mismatch or value isn't numeric change
                self.logger.debug(f"UPDATE_CHARACTER_ATTRIBUTE: 尝试直接设置属性 '{consequence.attribute_name}' 为 '{change_value}' (类型: {type(change_value)})，原值: {current_value} (类型: {type(current_value)})。")
                new_value = change_value

            setattr(character_instance.attributes, consequence.attribute_name, new_value)
            description = f"角色属性更新：角色 '{consequence.target_entity_id}' ({character_instance.name}) 的属性 '{consequence.attribute_name}' 从 '{current_value}' 更新为 '{new_value}'。"
            # Log change value if it was numeric addition/subtraction
            if isinstance(change_value, (int, float)) and isinstance(current_value, (int, float)):
                 description += f" (变化: {change_value:+})" # Show sign for change

            self.logger.info(description)
            self._create_record(consequence, game_state, success=True, description=description)
            return description
        except Exception as e:
            desc = f"更新角色属性 '{consequence.attribute_name}' 时出错：{e}"
            self.logger.exception(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None
