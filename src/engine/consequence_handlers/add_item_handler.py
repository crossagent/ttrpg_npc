# src/engine/consequence_handlers/add_item_handler.py
from typing import Optional

from src.engine.consequence_handlers.base_handler import BaseConsequenceHandler
from src.models.consequence_models import Consequence
from src.models.game_state_models import GameState, ItemInstance
# We need ScenarioManager to get item definitions, but handlers shouldn't depend on managers directly.
# Let's assume GameState might hold a reference or we pass needed info via consequence details later.
# For now, we'll skip fetching item names if not already present. A better solution might be needed.
# Alternative: Pass ScenarioManager to the handler constructor if needed, but increases coupling.
# Let's proceed without ScenarioManager for now and log warnings.

class AddItemHandler(BaseConsequenceHandler):
    """处理 ADD_ITEM 后果。"""

    async def apply(self, consequence: Consequence, game_state: GameState) -> Optional[str]:
        """
        应用 ADD_ITEM 后果到游戏状态，并在成功时记录。
        """
        if not consequence.target_entity_id or not consequence.item_id:
            self.logger.warning(f"无效的 ADD_ITEM 后果：缺少 target_entity_id 或 item_id。 {consequence}")
            self._create_record(consequence, game_state, success=False, description="缺少 target_entity_id 或 item_id")
            return None

        quantity = consequence.value if isinstance(consequence.value, int) and consequence.value > 0 else 1
        description = None
        success = False

        # Add to character inventory
        if consequence.target_entity_id in game_state.characters:
            character_instance = game_state.characters[consequence.target_entity_id]
            existing_item: Optional[ItemInstance] = next((item for item in character_instance.items if item.item_id == consequence.item_id), None)

            if existing_item:
                existing_item.quantity += quantity
                description = f"物品更新：角色 '{consequence.target_entity_id}' ({character_instance.name}) 的物品 '{consequence.item_id}' 数量增加 {quantity}，当前数量: {existing_item.quantity}。"
                self.logger.info(description)
                success = True
            else:
                # Ideally fetch item_def here using ScenarioManager, but skipping for now
                item_name = consequence.item_id # Use ID as name if definition not available
                self.logger.warning(f"ADD_ITEM 警告：无法获取物品 '{consequence.item_id}' 的定义，将使用 ID 作为名称。")
                new_item = ItemInstance(item_id=consequence.item_id, quantity=quantity, name=item_name)
                character_instance.items.append(new_item)
                description = f"物品添加：向角色 '{consequence.target_entity_id}' ({character_instance.name}) 添加了 {quantity} 个物品 '{consequence.item_id}'。"
                self.logger.info(description)
                success = True

        # Add to location
        elif consequence.target_entity_id in game_state.location_states:
            location_state = game_state.location_states[consequence.target_entity_id]
            existing_item: Optional[ItemInstance] = next((item for item in location_state.available_items if item.item_id == consequence.item_id), None)

            if existing_item:
                existing_item.quantity += quantity
                description = f"物品更新：地点 '{consequence.target_entity_id}' 的物品 '{consequence.item_id}' 数量增加 {quantity}，当前数量: {existing_item.quantity}。"
                self.logger.info(description)
                success = True
            else:
                # Ideally fetch item_def here using ScenarioManager
                item_name = consequence.item_id
                self.logger.warning(f"ADD_ITEM 警告：无法获取物品 '{consequence.item_id}' 的定义，将使用 ID 作为名称。")
                new_item = ItemInstance(item_id=consequence.item_id, quantity=quantity, name=item_name)
                location_state.available_items.append(new_item)
                description = f"物品添加：向地点 '{consequence.target_entity_id}' 添加了 {quantity} 个物品 '{consequence.item_id}'。"
                self.logger.info(description)
                success = True
        else:
            description = f"ADD_ITEM 失败：未找到目标实体 ID '{consequence.target_entity_id}' (既不是角色也不是地点)。"
            self.logger.warning(description)
            success = False

        # Create record regardless of success/failure inside the target block
        self._create_record(consequence, game_state, success=success, description=description)
        return description if success else None
