# src/engine/consequence_handlers/add_item_handler.py
from typing import Optional

from src.engine.consequence_handlers.base_handler import BaseConsequenceHandler
# Import the specific consequence type and the union type
from src.models.consequence_models import AnyConsequence, AddItemConsequence
from src.models.game_state_models import GameState, ItemInstance
# We need ScenarioManager to get item definitions, but handlers shouldn't depend on managers directly.
# Let's assume GameState might hold a reference or we pass needed info via consequence details later.
# For now, we'll skip fetching item names if not already present. A better solution might be needed.
# Alternative: Pass ScenarioManager to the handler constructor if needed, but increases coupling.
# Let's proceed without ScenarioManager for now and log warnings.

class AddItemHandler(BaseConsequenceHandler):
    """处理 ADD_ITEM 后果。"""

    async def apply(self, consequence: AnyConsequence, game_state: GameState) -> Optional[str]:
        """
        应用 ADD_ITEM 后果到游戏状态，并在成功时记录。
        """
        # Type check (optional but good practice if dispatcher isn't guaranteed)
        if not isinstance(consequence, AddItemConsequence):
            self.logger.error(f"AddItemHandler 接收到错误的后果类型: {type(consequence)}")
            # Cannot create a meaningful record here as the type is wrong
            return None

        # Access fields directly from the specific AddItemConsequence model
        target_id = consequence.target_entity_id
        item_id = consequence.item_id
        quantity = consequence.value # Already validated as int > 0 by Pydantic

        description = None
        success = False
        # Placeholder for source description - ideally this comes from where the consequence was generated
        source_description = f"来源: {consequence.type.value}"

        # Add to character inventory
        if target_id in game_state.characters:
            character_instance = game_state.characters[target_id]
            existing_item: Optional[ItemInstance] = next((item for item in character_instance.items if item.item_id == item_id), None)

            if existing_item:
                existing_item.quantity += quantity
                description = f"物品更新：角色 '{target_id}' ({character_instance.name}) 的物品 '{item_id}' 数量增加 {quantity}，当前数量: {existing_item.quantity}。"
                self.logger.info(description)
                success = True
            else:
                # Ideally fetch item_def here using ScenarioManager, but skipping for now
                item_name = item_id # Use ID as name if definition not available
                self.logger.warning(f"ADD_ITEM 警告：无法获取物品 '{item_id}' 的定义，将使用 ID 作为名称。")
                new_item = ItemInstance(item_id=item_id, quantity=quantity, name=item_name)
                character_instance.items.append(new_item)
                description = f"物品添加：向角色 '{target_id}' ({character_instance.name}) 添加了 {quantity} 个物品 '{item_id}'。"
                self.logger.info(description)
                success = True

        # Add to location
        elif target_id in game_state.location_states:
            location_state = game_state.location_states[target_id]
            existing_item: Optional[ItemInstance] = next((item for item in location_state.available_items if item.item_id == item_id), None)

            if existing_item:
                existing_item.quantity += quantity
                description = f"物品更新：地点 '{target_id}' 的物品 '{item_id}' 数量增加 {quantity}，当前数量: {existing_item.quantity}。"
                self.logger.info(description)
                success = True
            else:
                # Ideally fetch item_def here using ScenarioManager
                item_name = item_id
                self.logger.warning(f"ADD_ITEM 警告：无法获取物品 '{item_id}' 的定义，将使用 ID 作为名称。")
                new_item = ItemInstance(item_id=item_id, quantity=quantity, name=item_name)
                location_state.available_items.append(new_item)
                description = f"物品添加：向地点 '{target_id}' 添加了 {quantity} 个物品 '{item_id}'。"
                self.logger.info(description)
                success = True
        else:
            description = f"ADD_ITEM 失败：未找到目标实体 ID '{target_id}' (既不是角色也不是地点)。"
            self.logger.warning(description)
            success = False

        # Create record using the updated base class method signature
        self._create_record(
            consequence=consequence,
            game_state=game_state,
            success=success,
            source_description=source_description, # Pass the source description
            description=description
        )
        return description if success else None
