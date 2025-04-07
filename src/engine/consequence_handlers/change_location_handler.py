# src/engine/consequence_handlers/change_location_handler.py
from typing import Optional

from src.engine.consequence_handlers.base_handler import BaseConsequenceHandler
# Import the specific consequence type and the union type
from src.models.consequence_models import AnyConsequence, ChangeLocationConsequence
from src.models.game_state_models import GameState

class ChangeLocationHandler(BaseConsequenceHandler):
    """处理 CHANGE_LOCATION 后果。"""

    async def apply(self, consequence: AnyConsequence, game_state: GameState) -> Optional[str]:
        """
        应用 CHANGE_LOCATION 后果到游戏状态，并在成功或失败时记录。
        """
        # Type check
        if not isinstance(consequence, ChangeLocationConsequence):
            self.logger.error(f"ChangeLocationHandler 接收到错误的后果类型: {type(consequence)}")
            return None

        # Access fields directly
        character_id = consequence.target_entity_id
        new_location_id = consequence.value # Value now represents the new location ID

        # Placeholder for source description
        source_description = f"来源: {consequence.type.value}"

        character_instance = game_state.characters.get(character_id)
        if not character_instance:
            desc = f"CHANGE_LOCATION 失败：未找到角色 ID '{character_id}'。"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, source_description=source_description, description=desc)
            return None

        # Validate if new_location_id exists in game_state.location_states
        if new_location_id not in game_state.location_states:
            desc = f"CHANGE_LOCATION 失败：目标地点 ID '{new_location_id}' 不存在于 location_states 中。"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, source_description=source_description, description=desc)
            return None # Fail if location doesn't exist

        try:
            old_location = character_instance.location
            # Only proceed if location actually changes
            if old_location == new_location_id:
                 desc = f"角色 '{character_id}' ({character_instance.name}) 已在目标地点 '{new_location_id}'，无需移动。"
                 self.logger.info(desc)
                 # Record as success (no change needed is still a success in applying the intent)
                 self._create_record(consequence, game_state, success=True, source_description=source_description, description=desc)
                 return desc # Return description even if no change occurred

            character_instance.location = new_location_id
            description = f"角色位置更新：角色 '{character_id}' ({character_instance.name}) 的位置从 '{old_location}' 更新为 '{new_location_id}'。"
            self.logger.info(description)

            # Update present_characters in old and new locations
            # Remove from old location
            if old_location and old_location in game_state.location_states:
                if character_id in game_state.location_states[old_location].present_characters:
                    game_state.location_states[old_location].present_characters.remove(character_id)
                    self.logger.debug(f"已将角色 '{character_id}' 从地点 '{old_location}' 的 present_characters 移除。")
            # Add to new location
            if new_location_id in game_state.location_states: # Already checked existence above
                if character_id not in game_state.location_states[new_location_id].present_characters:
                    game_state.location_states[new_location_id].present_characters.append(character_id)
                    self.logger.debug(f"已将角色 '{character_id}' 添加到地点 '{new_location_id}' 的 present_characters。")

            # +++ 更新 visited_locations +++
            if hasattr(character_instance, 'visited_locations'):
                # Treat the list like a set for checking existence
                if new_location_id not in character_instance.visited_locations:
                    character_instance.visited_locations.append(new_location_id)
                    self.logger.info(f"角色 '{character_id}' 首次访问地点 '{new_location_id}'，已添加到 visited_locations。")
            else:
                 self.logger.warning(f"角色 '{character_id}' 实例缺少 visited_locations 属性。")
            # +++ 结束更新 visited_locations +++

            self._create_record(consequence, game_state, success=True, source_description=source_description, description=description)
            return description
        except Exception as e:
            desc = f"更新角色 '{character_id}' 位置时出错：{e}"
            self.logger.exception(desc)
            self._create_record(consequence, game_state, success=False, source_description=source_description, description=desc)
            return None
