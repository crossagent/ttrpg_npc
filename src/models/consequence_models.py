# src/models/consequence_models.py
from enum import Enum
from typing import Any, Optional, Dict, Union, Literal, Annotated
from datetime import datetime

from pydantic import BaseModel, Field

class ConsequenceType(Enum):
    """Defines the types of consequences that can result from actions or events."""
    UPDATE_ATTRIBUTE = "update_attribute"  # Update an attribute of a non-character entity (item, location)
    ADD_ITEM = "add_item"              # Add an item to a character's inventory or a location
    REMOVE_ITEM = "remove_item"          # Remove an item from a character's inventory or a location
    CHANGE_RELATIONSHIP = "change_relationship" # Change the relationship value between two characters
    TRIGGER_EVENT = "trigger_event"        # Trigger a new event (by ID)
    SEND_MESSAGE = "send_message"          # Send a specific message (e.g., GM narration, system message)
    UPDATE_FLAG = "update_flag"            # Set or update a narrative flag in the game state
    UPDATE_CHARACTER_ATTRIBUTE = "update_character_attribute" # Update a specific attribute of a character instance
    UPDATE_CHARACTER_SKILL = "update_character_skill"      # Update a specific skill of a character instance
    CHANGE_LOCATION = "change_location"            # Change the location of a character instance
    # Add more types as needed, e.g., LEARN_INFO, APPLY_STATUS_EFFECT

# --- Discriminated Union Implementation ---

class BaseConsequence(BaseModel):
    """Base model for all consequence types, containing common optional fields."""
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata for context or debugging.")

class UpdateAttributeConsequence(BaseConsequence):
    """Updates an attribute of a non-character entity (item, location)."""
    type: str # Changed from Literal
    target_entity_id: str = Field(..., description="The ID of the entity (item, location) affected.")
    attribute_name: str = Field(..., description="The name of the attribute being changed.")
    value: Any = Field(..., description="The new value for the attribute.")

class AddItemConsequence(BaseConsequence):
    """Adds an item to a character's inventory or a location."""
    type: str # Changed from Literal
    target_entity_id: str = Field(..., description="The ID of the character or location receiving the item.")
    item_id: str = Field(..., description="The ID of the item being added.")
    value: int = Field(1, description="The quantity of the item to add.", gt=0) # Represents quantity

class RemoveItemConsequence(BaseConsequence):
    """Removes an item from a character's inventory or a location."""
    type: str # Changed from Literal
    target_entity_id: str = Field(..., description="The ID of the character or location losing the item.")
    item_id: str = Field(..., description="The ID of the item being removed.")
    value: int = Field(1, description="The quantity of the item to remove.", gt=0) # Represents quantity

class ChangeRelationshipConsequence(BaseConsequence):
    """Changes the relationship value between two characters."""
    type: str # Changed from Literal
    target_entity_id: str = Field(..., description="The ID of the first character.")
    secondary_entity_id: str = Field(..., description="The ID of the second character.")
    value: float = Field(..., description="The amount to change the relationship value by (e.g., +0.1, -0.5).")

class TriggerEventConsequence(BaseConsequence):
    """Triggers a new event."""
    type: str # Changed from Literal
    event_id: str = Field(..., description="The ID of the event to be triggered.")

class SendMessageConsequence(BaseConsequence):
    """Sends a specific message."""
    type: str # Changed from Literal
    message_content: str = Field(..., description="The content of the message to be sent.")
    message_recipient: str = Field("PLAYER", description="The recipient ('PLAYER', 'DM', or specific character ID).")

class UpdateFlagConsequence(BaseConsequence):
    """Sets or updates a narrative flag."""
    type: str # Changed from Literal
    flag_name: str = Field(..., description="The name of the flag being set or updated.")
    flag_value: bool = Field(..., description="The boolean value to set the flag to.")

class UpdateCharacterAttributeConsequence(BaseConsequence):
    """Updates a specific attribute of a character instance."""
    type: str # Changed from Literal
    target_entity_id: str = Field(..., description="The ID of the character affected.")
    attribute_name: str = Field(..., description="The name of the character attribute being changed.")
    value: Any = Field(..., description="The change amount (e.g., +1, -2) or new value for the attribute.")

class UpdateCharacterSkillConsequence(BaseConsequence):
    """Updates a specific skill of a character instance."""
    type: str # Changed from Literal
    target_entity_id: str = Field(..., description="The ID of the character affected.")
    skill_name: str = Field(..., description="The name of the character skill being changed.")
    value: Any = Field(..., description="The change amount (e.g., +1, -2) or new value for the skill.")

class ChangeLocationConsequence(BaseConsequence):
    """Changes the location of a character instance."""
    type: str # Changed from Literal
    target_entity_id: str = Field(..., description="The ID of the character whose location is changing.")
    value: str = Field(..., description="The ID of the new location.") # Represents new location_id

# --- Union Type Definition ---

# Removed Annotated and discriminator as we will handle validation manually
AnyConsequence = Union[
    UpdateAttributeConsequence,
    AddItemConsequence,
        RemoveItemConsequence,
        ChangeRelationshipConsequence,
        TriggerEventConsequence,
        SendMessageConsequence,
        UpdateFlagConsequence,
        UpdateCharacterAttributeConsequence,
        UpdateCharacterSkillConsequence,
        ChangeLocationConsequence,
    # Add future consequence types here
]

# --- Record Models (Updated) ---

class AppliedConsequenceRecord(BaseModel):
    """记录一个已成功应用到游戏状态的机制性后果"""
    record_id: str = Field(..., description="Unique identifier for this record.") # Added record_id
    timestamp: datetime = Field(default_factory=datetime.now, description="后果应用的时间戳")
    round_number: int = Field(..., description="后果应用的具体回合数")
    consequence_type: ConsequenceType = Field(..., description="The type of consequence applied.") # Added type for easier filtering
    target_entity_id: Optional[str] = Field(None, description="Primary entity affected, if applicable.") # Added target_id
    success: bool = Field(..., description="Whether the application was successful.") # Added success field
    source_description: str = Field(..., description="触发此后果的来源描述 (例如: '玩家A的行动', '事件X的结局Y')")
    applied_consequence: AnyConsequence = Field(..., description="实际应用的后果对象 (specific type)") # Changed type hint
    description: Optional[str] = Field(None, description="Optional description of the application process/result.") # Added description
    details: Dict[str, Any] = Field(..., description="Snapshot of the applied consequence details for logging/debugging.") # Added details

    # Removed redundant fields now present in applied_consequence or added above

class TriggeredEventRecord(BaseModel):
    """记录一个已成功触发的事件及其结局"""
    record_id: str = Field(..., description="Unique identifier for this record.") # Added record_id
    timestamp: datetime = Field(default_factory=datetime.now, description="事件触发的时间戳")
    round_number: int = Field(..., description="事件触发的具体回合数")
    event_id: str = Field(..., description="触发的剧本事件ID (ScenarioEvent.event_id)")
    outcome_id: str = Field(..., description="实际发生的结局ID (EventOutcome.id)")
    trigger_source: str = Field(..., description="触发事件的来源描述 (例如: '玩家A的行动', '环境变化')")
