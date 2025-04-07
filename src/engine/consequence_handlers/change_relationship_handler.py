# src/engine/consequence_handlers/change_relationship_handler.py
from typing import Optional

from src.engine.consequence_handlers.base_handler import BaseConsequenceHandler
# Import the specific consequence type and the union type
from src.models.consequence_models import AnyConsequence, ChangeRelationshipConsequence
from src.models.game_state_models import GameState

class ChangeRelationshipHandler(BaseConsequenceHandler):
    """处理 CHANGE_RELATIONSHIP 后果。"""

    async def apply(self, consequence: AnyConsequence, game_state: GameState) -> Optional[str]:
        """
        应用 CHANGE_RELATIONSHIP 后果到游戏状态，并在成功或失败时记录。
        """
        # Type check
        if not isinstance(consequence, ChangeRelationshipConsequence):
            self.logger.error(f"ChangeRelationshipHandler 接收到错误的后果类型: {type(consequence)}")
            return None

        # Access fields directly
        target_id = consequence.target_entity_id
        secondary_id = consequence.secondary_entity_id
        change_value = consequence.value # Value is now float

        # Placeholder for source description
        source_description = f"来源: {consequence.type.value}"

        target_char = game_state.characters.get(target_id)
        secondary_char = game_state.characters.get(secondary_id)

        if not target_char:
            desc = f"CHANGE_RELATIONSHIP 失败：未找到目标角色 ID '{target_id}'。"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, source_description=source_description, description=desc)
            return None
        if not secondary_char:
            desc = f"CHANGE_RELATIONSHIP 失败：未找到次要角色 ID '{secondary_id}'。"
            self.logger.warning(desc)
            self._create_record(consequence, game_state, success=False, source_description=source_description, description=desc)
            return None

        # --- Relationship Storage Logic ---
        # TODO: Refine this logic based on how relationships are actually stored.
        # Current assumption: relationship_player stores target's feeling towards the player.
        # If secondary_id is the player, update target_char.relationship_player.
        # If target_id is the player, update secondary_char.relationship_player.
        # If neither is the player, this handler might need adjustment or a different storage mechanism.

        relationship_updated = False
        description = ""
        old_relationship = 0.0 # Default value

        # Case 1: Target -> Player relationship
        if secondary_id == game_state.player_character_id and hasattr(target_char, 'relationship_player'):
            try:
                old_relationship = target_char.relationship_player or 0.0 # Handle None case
                new_relationship = old_relationship + change_value
                # Clamp the value (assuming -1.0 to 1.0 or adjust as needed)
                new_relationship = max(-1.0, min(1.0, new_relationship))
                target_char.relationship_player = new_relationship
                description = f"关系变化：角色 '{target_char.name}' 对玩家的关系值从 {old_relationship:.2f} 变为 {new_relationship:.2f} (变化: {change_value:+.2f})。"
                relationship_updated = True
            except Exception as e:
                description = f"更新角色 '{target_id}' 对玩家的关系时出错：{e}"
                self.logger.exception(description)

        # Case 2: Player -> Target relationship (Update the target's perspective)
        elif target_id == game_state.player_character_id and hasattr(secondary_char, 'relationship_player'):
             try:
                old_relationship = secondary_char.relationship_player or 0.0 # Handle None case
                # Apply the change from the player's perspective to the NPC's feeling towards the player
                new_relationship = old_relationship + change_value
                new_relationship = max(-1.0, min(1.0, new_relationship))
                secondary_char.relationship_player = new_relationship
                description = f"关系变化：玩家影响了角色 '{secondary_char.name}' 对玩家的关系值，从 {old_relationship:.2f} 变为 {new_relationship:.2f} (变化: {change_value:+.2f})。"
                relationship_updated = True
             except Exception as e:
                description = f"更新角色 '{secondary_id}' 对玩家的关系时出错（由玩家 '{target_id}' 触发）：{e}"
                self.logger.exception(description)

        # Case 3: NPC <-> NPC relationship (Not currently handled by relationship_player)
        else:
            description = f"CHANGE_RELATIONSHIP 警告：当前仅支持角色与玩家之间的关系更新 (target={target_id}, secondary={secondary_id})。未做更改。"
            self.logger.warning(description)
            # Record as success=False because the intended NPC-NPC change didn't happen
            self._create_record(consequence, game_state, success=False, source_description=source_description, description=description)
            return None # Or return description? Let's return None as no state changed.

        # Record the outcome
        if relationship_updated:
            self.logger.info(description)
            self._create_record(consequence, game_state, success=True, source_description=source_description, description=description)
            return description
        else:
            # Log the error description if update failed due to exception
            self.logger.error(description)
            self._create_record(consequence, game_state, success=False, source_description=source_description, description=description)
            return None
