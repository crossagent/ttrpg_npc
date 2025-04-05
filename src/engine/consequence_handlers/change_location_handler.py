# src/engine/consequence_handlers/change_location_handler.py
from typing import Optional

from src.engine.consequence_handlers.base_handler import BaseConsequenceHandler
from src.models.consequence_models import Consequence
from src.models.game_state_models import GameState

class ChangeLocationHandler(BaseConsequenceHandler):
    """处理 CHANGE_LOCATION 后果。"""

    async def apply(self, consequence: Consequence, game_state: GameState) -> Optional[str]:
        """
        应用 CHANGE_LOCATION 后果到游戏状态，并在成功或失败时记录。
        """
        if not consequence.target_entity_id or not consequence.value or not isinstance(consequence.value, str):
            desc = f"无效的 CHANGE_LOCATION 后果：缺少 target_entity_id 或 value 不是字符串。 {consequence}"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None

        character_instance = game_state.characters.get(consequence.target_entity_id)
        if not character_instance:
            desc = f"CHANGE_LOCATION 失败：未找到角色 ID '{consequence.target_entity_id}'。"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None

        new_location_id = consequence.value
        # Validate if new_location_id exists in game_state.location_states
        if new_location_id not in game_state.location_states:
            # Log a warning but proceed? Or fail? Let's fail for now for stricter state management.
            desc = f"CHANGE_LOCATION 失败：目标地点 ID '{new_location_id}' 不存在于 location_states 中。"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None # Fail if location doesn't exist

        try:
            old_location = character_instance.location
            # Only proceed if location actually changes
            if old_location == new_location_id:
                 desc = f"角色 '{consequence.target_entity_id}' ({character_instance.name}) 已在目标地点 '{new_location_id}'，无需移动。"
                 self.logger.info(desc)
                 # Record as success (no change needed is still a success in applying the intent)
                 self._create_record(consequence, game_state, success=True, description=desc)
                 return desc # Return description even if no change occurred

            character_instance.location = new_location_id
            description = f"角色位置更新：角色 '{consequence.target_entity_id}' ({character_instance.name}) 的位置从 '{old_location}' 更新为 '{new_location_id}'。"
            self.logger.info(description)

            # Update present_characters in old and new locations
            # Remove from old location
            if old_location and old_location in game_state.location_states:
                if consequence.target_entity_id in game_state.location_states[old_location].present_characters:
                    game_state.location_states[old_location].present_characters.remove(consequence.target_entity_id)
                    self.logger.debug(f"已将角色 '{consequence.target_entity_id}' 从地点 '{old_location}' 的 present_characters 移除。")
            # Add to new location
            if new_location_id in game_state.location_states: # Already checked existence above
                if consequence.target_entity_id not in game_state.location_states[new_location_id].present_characters:
                    game_state.location_states[new_location_id].present_characters.append(consequence.target_entity_id)
                    self.logger.debug(f"已将角色 '{consequence.target_entity_id}' 添加到地点 '{new_location_id}' 的 present_characters。")

            self._create_record(consequence, game_state, success=True, description=description)
            return description
        except Exception as e:
            desc = f"更新角色 '{consequence.target_entity_id}' 位置时出错：{e}"
            self.logger.exception(desc)
            self._create_record(consequence, game_state, success=False, description=desc)
            return None
