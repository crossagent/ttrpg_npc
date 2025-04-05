# src/engine/consequence_handlers/update_character_skill_handler.py
from typing import Optional

from src.engine.consequence_handlers.base_handler import BaseConsequenceHandler
from src.models.consequence_models import Consequence
from src.models.game_state_models import GameState

class UpdateCharacterSkillHandler(BaseConsequenceHandler):
    """处理 UPDATE_CHARACTER_SKILL 后果。"""

    async def apply(self, consequence: Consequence, game_state: GameState) -> Optional[str]:
        """
        应用 UPDATE_CHARACTER_SKILL 后果到游戏状态，并在成功或失败时记录。
        """
        # Note: Consequence model uses 'skill_name' for this type
        if not consequence.target_entity_id or not consequence.skill_name or consequence.value is None:
            desc = f"无效的 UPDATE_CHARACTER_SKILL 后果：缺少 target_entity_id, skill_name 或 value。 {consequence}"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None

        character_instance = game_state.characters.get(consequence.target_entity_id)
        if not character_instance:
            desc = f"UPDATE_CHARACTER_SKILL 失败：未找到角色 ID '{consequence.target_entity_id}'。"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None

        if not hasattr(character_instance.skills, consequence.skill_name):
            desc = f"UPDATE_CHARACTER_SKILL 失败：角色 '{consequence.target_entity_id}' 的技能集没有技能 '{consequence.skill_name}'。"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None

        try:
            current_value = getattr(character_instance.skills, consequence.skill_name)
            change_value = consequence.value
            new_value = current_value

            # Assume value is the change amount (e.g., +1, -2) for numeric types
            if isinstance(change_value, (int, float)) and isinstance(current_value, (int, float)):
                new_value = current_value + change_value
            else:
                # Fallback: try direct assignment
                self.logger.debug(f"UPDATE_CHARACTER_SKILL: 尝试直接设置技能 '{consequence.skill_name}' 为 '{change_value}' (类型: {type(change_value)})，原值: {current_value} (类型: {type(current_value)})。")
                new_value = change_value

            setattr(character_instance.skills, consequence.skill_name, new_value)
            description = f"角色技能更新：角色 '{consequence.target_entity_id}' ({character_instance.name}) 的技能 '{consequence.skill_name}' 从 '{current_value}' 更新为 '{new_value}'。"
            if isinstance(change_value, (int, float)) and isinstance(current_value, (int, float)):
                 description += f" (变化: {change_value:+})" # Show sign for change

            self.logger.info(description)
            self._create_record(consequence, game_state, success=True, description=description)
            return description
        except Exception as e:
            desc = f"更新角色技能 '{consequence.skill_name}' 时出错：{e}"
            self.logger.exception(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None
