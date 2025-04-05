# src/engine/consequence_handlers/change_relationship_handler.py
from typing import Optional

from src.engine.consequence_handlers.base_handler import BaseConsequenceHandler
from src.models.consequence_models import Consequence
from src.models.game_state_models import GameState

class ChangeRelationshipHandler(BaseConsequenceHandler):
    """处理 CHANGE_RELATIONSHIP 后果。"""

    async def apply(self, consequence: Consequence, game_state: GameState) -> Optional[str]:
        """
        应用 CHANGE_RELATIONSHIP 后果到游戏状态，并在成功或失败时记录。
        """
        if not consequence.target_entity_id or consequence.secondary_entity_id is None or consequence.value is None:
            desc = f"无效的 CHANGE_RELATIONSHIP 后果：缺少 target_entity_id, secondary_entity_id 或 value。 {consequence}"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None

        target_char = game_state.characters.get(consequence.target_entity_id)
        # Assuming secondary_entity_id is always the player for relationship_player
        # If relationships can be between any two characters, this needs adjustment.
        secondary_char = game_state.characters.get(consequence.secondary_entity_id)

        if not target_char:
            desc = f"CHANGE_RELATIONSHIP 失败：未找到目标角色 ID '{consequence.target_entity_id}'。"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None
        if not secondary_char:
            # If secondary is not found, maybe log a warning but proceed if relationship is one-way?
            # For now, let's require both.
            desc = f"CHANGE_RELATIONSHIP 失败：未找到次要角色 ID '{consequence.secondary_entity_id}'。"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None

        # Currently assumes relationship is stored in target_char.relationship_player
        # This might need generalization if relationships are stored differently (e.g., a matrix)
        if not hasattr(target_char, 'relationship_player'):
             desc = f"CHANGE_RELATIONSHIP 失败：目标角色 '{target_char.name}' 没有 'relationship_player' 属性。"
             self.logger.error(desc) # This should ideally not happen if model is correct
             self._create_record(consequence, game_state, success=False, description=desc)
             return None

        try:
            change_value = int(consequence.value) # Ensure value is an integer
            old_relationship = target_char.relationship_player
            new_relationship = old_relationship + change_value

            # Clamp the value between -100 and 100 (or define min/max elsewhere)
            new_relationship = max(-100, min(100, new_relationship))

            target_char.relationship_player = new_relationship
            description = f"关系变化：角色 '{target_char.name}' 对 '{secondary_char.name}' 的关系值从 {old_relationship} 变为 {new_relationship} (变化: {change_value})。"
            self.logger.info(description)
            self._create_record(consequence, game_state, success=True, description=description)
            return description
        except ValueError:
            desc = f"CHANGE_RELATIONSHIP 失败：无法将 value '{consequence.value}' 转换为整数。"
            self.logger.error(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None
        except Exception as e:
            desc = f"更新角色 '{consequence.target_entity_id}' 对 '{consequence.secondary_entity_id}' 的关系时出错：{e}"
            self.logger.exception(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None
