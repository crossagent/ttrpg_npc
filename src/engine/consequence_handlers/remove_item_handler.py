# src/engine/consequence_handlers/remove_item_handler.py
from typing import Optional

from src.engine.consequence_handlers.base_handler import BaseConsequenceHandler
# Import the specific consequence type and the union type
from src.models.consequence_models import AnyConsequence, RemoveItemConsequence
from src.models.game_state_models import GameState, ItemInstance

class RemoveItemHandler(BaseConsequenceHandler):
    """处理 REMOVE_ITEM 后果。"""

    async def apply(self, consequence: AnyConsequence, game_state: GameState) -> Optional[str]:
        """
        应用 REMOVE_ITEM 后果到游戏状态，并在成功或失败时记录。
        """
        # Type check
        if not isinstance(consequence, RemoveItemConsequence):
            self.logger.error(f"RemoveItemHandler 接收到错误的后果类型: {type(consequence)}")
            return None

        # Access fields directly
        target_id = consequence.target_entity_id
        item_id = consequence.item_id
        quantity_to_remove = consequence.value # Already validated as int > 0

        description = None
        success = False
        # Placeholder for source description
        source_description = f"来源: {consequence.type}"

        # Remove from character inventory
        if target_id in game_state.characters:
            character_instance = game_state.characters[target_id]
            item_to_remove: Optional[ItemInstance] = next((item for item in character_instance.items if item.item_id == item_id), None)

            if item_to_remove:
                if item_to_remove.quantity >= quantity_to_remove:
                    original_quantity = item_to_remove.quantity
                    item_to_remove.quantity -= quantity_to_remove
                    description = f"物品移除：从角色 '{target_id}' ({character_instance.name}) 移除 {quantity_to_remove} 个物品 '{item_id}'，剩余数量: {item_to_remove.quantity}。"
                    self.logger.info(description)
                    success = True

                    # Check if item should be completely removed
                    if item_to_remove.quantity <= 0:
                        character_instance.items.remove(item_to_remove)
                        description_removed = f"物品移除：角色 '{target_id}' ({character_instance.name}) 的物品 '{item_id}' 已完全移除。"
                        self.logger.info(description_removed)
                        # Use the more specific description if fully removed
                        description = description_removed
                else:
                    description = f"REMOVE_ITEM 失败：角色 '{target_id}' ({character_instance.name}) 物品 '{item_id}' 数量不足 ({item_to_remove.quantity} < {quantity_to_remove})。"
                    self.logger.warning(description)
                    success = False
            else:
                description = f"REMOVE_ITEM 失败：角色 '{target_id}' ({character_instance.name}) 没有物品 '{item_id}'。"
                self.logger.warning(description)
                success = False

        # Remove from location
        elif target_id in game_state.location_states:
            location_state = game_state.location_states[target_id]
            item_to_remove: Optional[ItemInstance] = next((item for item in location_state.available_items if item.item_id == item_id), None)

            if item_to_remove:
                if item_to_remove.quantity >= quantity_to_remove:
                    original_quantity = item_to_remove.quantity
                    item_to_remove.quantity -= quantity_to_remove
                    description = f"物品移除：从地点 '{target_id}' 移除 {quantity_to_remove} 个物品 '{item_id}'，剩余数量: {item_to_remove.quantity}。"
                    self.logger.info(description)
                    success = True

                    # Check if item should be completely removed
                    if item_to_remove.quantity <= 0:
                        location_state.available_items.remove(item_to_remove)
                        description_removed = f"物品移除：地点 '{target_id}' 的物品 '{item_id}' 已完全移除。"
                        self.logger.info(description_removed)
                        description = description_removed # Use the more specific description
                else:
                    description = f"REMOVE_ITEM 失败：地点 '{target_id}' 物品 '{item_id}' 数量不足 ({item_to_remove.quantity} < {quantity_to_remove})。"
                    self.logger.warning(description)
                    success = False
            else:
                description = f"REMOVE_ITEM 失败：地点 '{target_id}' 没有物品 '{item_id}'。"
                self.logger.warning(description)
                success = False
        else:
            description = f"REMOVE_ITEM 失败：未找到目标实体 ID '{target_id}' (既不是角色也不是地点)。"
            self.logger.warning(description)
            success = False

        # Create record
        self._create_record(
            consequence=consequence,
            game_state=game_state,
            success=success,
            source_description=source_description,
            description=description
        )
        # Return the description only if successful
        return description if success else None
