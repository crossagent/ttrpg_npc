# src/engine/consequence_handlers/remove_item_handler.py
from typing import Optional

from src.engine.consequence_handlers.base_handler import BaseConsequenceHandler
from src.models.consequence_models import Consequence
from src.models.game_state_models import GameState, ItemInstance

class RemoveItemHandler(BaseConsequenceHandler):
    """处理 REMOVE_ITEM 后果。"""

    async def apply(self, consequence: Consequence, game_state: GameState) -> Optional[str]:
        """
        应用 REMOVE_ITEM 后果到游戏状态，并在成功或失败时记录。
        """
        if not consequence.target_entity_id or not consequence.item_id:
            self.logger.warning(f"无效的 REMOVE_ITEM 后果：缺少 target_entity_id 或 item_id。 {consequence}")
            self._create_record(consequence, game_state, success=False, description="缺少 target_entity_id 或 item_id")
            return None

        quantity_to_remove = consequence.value if isinstance(consequence.value, int) and consequence.value > 0 else 1
        description = None
        success = False

        # Remove from character inventory
        if consequence.target_entity_id in game_state.characters:
            character_instance = game_state.characters[consequence.target_entity_id]
            item_to_remove: Optional[ItemInstance] = next((item for item in character_instance.items if item.item_id == consequence.item_id), None)

            if item_to_remove:
                if item_to_remove.quantity >= quantity_to_remove:
                    original_quantity = item_to_remove.quantity
                    item_to_remove.quantity -= quantity_to_remove
                    description = f"物品移除：从角色 '{consequence.target_entity_id}' ({character_instance.name}) 移除 {quantity_to_remove} 个物品 '{consequence.item_id}'，剩余数量: {item_to_remove.quantity}。"
                    self.logger.info(description)
                    success = True

                    # Check if item should be completely removed
                    if item_to_remove.quantity <= 0:
                        character_instance.items.remove(item_to_remove)
                        description_removed = f"物品移除：角色 '{consequence.target_entity_id}' ({character_instance.name}) 的物品 '{consequence.item_id}' 已完全移除。"
                        self.logger.info(description_removed)
                        # Use the more specific description if fully removed
                        description = description_removed
                else:
                    description = f"REMOVE_ITEM 失败：角色 '{consequence.target_entity_id}' ({character_instance.name}) 物品 '{consequence.item_id}' 数量不足 ({item_to_remove.quantity} < {quantity_to_remove})。"
                    self.logger.warning(description)
                    success = False
            else:
                description = f"REMOVE_ITEM 失败：角色 '{consequence.target_entity_id}' ({character_instance.name}) 没有物品 '{consequence.item_id}'。"
                self.logger.warning(description)
                success = False

        # Remove from location
        elif consequence.target_entity_id in game_state.location_states:
            location_state = game_state.location_states[consequence.target_entity_id]
            item_to_remove: Optional[ItemInstance] = next((item for item in location_state.available_items if item.item_id == consequence.item_id), None)

            if item_to_remove:
                if item_to_remove.quantity >= quantity_to_remove:
                    original_quantity = item_to_remove.quantity
                    item_to_remove.quantity -= quantity_to_remove
                    description = f"物品移除：从地点 '{consequence.target_entity_id}' 移除 {quantity_to_remove} 个物品 '{consequence.item_id}'，剩余数量: {item_to_remove.quantity}。"
                    self.logger.info(description)
                    success = True

                    # Check if item should be completely removed
                    if item_to_remove.quantity <= 0:
                        location_state.available_items.remove(item_to_remove)
                        description_removed = f"物品移除：地点 '{consequence.target_entity_id}' 的物品 '{consequence.item_id}' 已完全移除。"
                        self.logger.info(description_removed)
                        description = description_removed # Use the more specific description
                else:
                    description = f"REMOVE_ITEM 失败：地点 '{consequence.target_entity_id}' 物品 '{consequence.item_id}' 数量不足 ({item_to_remove.quantity} < {quantity_to_remove})。"
                    self.logger.warning(description)
                    success = False
            else:
                description = f"REMOVE_ITEM 失败：地点 '{consequence.target_entity_id}' 没有物品 '{consequence.item_id}'。"
                self.logger.warning(description)
                success = False
        else:
            description = f"REMOVE_ITEM 失败：未找到目标实体 ID '{consequence.target_entity_id}' (既不是角色也不是地点)。"
            self.logger.warning(description)
            success = False

        # Create record
        self._create_record(consequence, game_state, success=success, description=description)
        # Return the description only if successful
        return description if success else None
