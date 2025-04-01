# src/models/consequence_models.py
from enum import Enum
from typing import Any, Optional, Dict

from pydantic import BaseModel, Field

class ConsequenceType(Enum):
    """Defines the types of consequences that can result from actions or events."""
    UPDATE_ATTRIBUTE = "update_attribute"  # Update an attribute of an entity (character, item, location)
    ADD_ITEM = "add_item"              # Add an item to a character's inventory or a location
    REMOVE_ITEM = "remove_item"          # Remove an item from a character's inventory or a location
    CHANGE_RELATIONSHIP = "change_relationship" # Change the relationship value between two characters
    TRIGGER_EVENT = "trigger_event"        # Trigger a new event (by ID)
    SEND_MESSAGE = "send_message"          # Send a specific message (e.g., GM narration, system message)
    # Add more types as needed, e.g., CHANGE_LOCATION, LEARN_INFO, APPLY_STATUS_EFFECT

class Consequence(BaseModel):
    """Represents a single structured consequence of an action or event."""
    type: ConsequenceType = Field(..., description="The type of consequence.")
    target_entity_id: Optional[str] = Field(None, description="The ID of the primary entity affected (e.g., character, item, location).")
    attribute_name: Optional[str] = Field(None, description="The name of the attribute being changed (used with UPDATE_ATTRIBUTE).")
    value: Any = Field(None, description="The new value or change amount (type depends on 'type' and 'attribute_name').")
    item_id: Optional[str] = Field(None, description="The ID of the item being added or removed (used with ADD_ITEM, REMOVE_ITEM).")
    secondary_entity_id: Optional[str] = Field(None, description="The ID of a secondary entity involved (e.g., the other character in CHANGE_RELATIONSHIP).")
    event_id: Optional[str] = Field(None, description="The ID of the event to be triggered (used with TRIGGER_EVENT).")
    message_content: Optional[str] = Field(None, description="The content of the message to be sent (used with SEND_MESSAGE).")
    message_recipient: Optional[str] = Field("PLAYER", description="The recipient of the message ('PLAYER', 'DM', or specific character ID). Default is 'PLAYER'.")
    # Optional metadata for context or debugging
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata for context or debugging.")

    class Config:
        pass # Default behavior: use Enum members, Pydantic handles conversion from string values on load
