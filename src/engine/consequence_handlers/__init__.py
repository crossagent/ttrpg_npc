# src/engine/consequence_handlers/__init__.py
from typing import Optional # Import Optional
from src.models.consequence_models import ConsequenceType

# Import all specific handler classes
from .base_handler import BaseConsequenceHandler # Although not used directly in registry, good practice
from .update_attribute_handler import UpdateAttributeHandler
from .add_item_handler import AddItemHandler
from .remove_item_handler import RemoveItemHandler
from .change_relationship_handler import ChangeRelationshipHandler
from .update_character_attribute_handler import UpdateCharacterAttributeHandler
from .update_character_skill_handler import UpdateCharacterSkillHandler
from .change_location_handler import ChangeLocationHandler
# Import other handlers here as they are created

# Define the registry mapping ConsequenceType to Handler Class
HANDLER_REGISTRY = {
    ConsequenceType.UPDATE_ATTRIBUTE: UpdateAttributeHandler,
    ConsequenceType.ADD_ITEM: AddItemHandler,
    ConsequenceType.REMOVE_ITEM: RemoveItemHandler,
    ConsequenceType.CHANGE_RELATIONSHIP: ChangeRelationshipHandler,
    ConsequenceType.UPDATE_CHARACTER_ATTRIBUTE: UpdateCharacterAttributeHandler,
    ConsequenceType.UPDATE_CHARACTER_SKILL: UpdateCharacterSkillHandler,
    ConsequenceType.CHANGE_LOCATION: ChangeLocationHandler,
    # Add mappings for TRIGGER_EVENT, SEND_MESSAGE etc. when their handlers are implemented
    # ConsequenceType.TRIGGER_EVENT: TriggerEventHandler,
    # ConsequenceType.SEND_MESSAGE: SendMessageHandler,
}

# Optional: Define a function to get a handler instance
def get_handler(consequence_type: ConsequenceType) -> Optional[BaseConsequenceHandler]:
    """Gets an instance of the handler for the given consequence type."""
    handler_class = HANDLER_REGISTRY.get(consequence_type)
    if handler_class:
        return handler_class() # Instantiate the handler
    return None
