# src/models/consequence_models.py
from enum import Enum
from typing import Any, Optional, Dict
from datetime import datetime # +++ Import datetime +++

from pydantic import BaseModel, Field

class ConsequenceType(Enum):
    """Defines the types of consequences that can result from actions or events."""
    UPDATE_ATTRIBUTE = "update_attribute"  # Update an attribute of an entity (character, item, location)
    ADD_ITEM = "add_item"              # Add an item to a character's inventory or a location
    REMOVE_ITEM = "remove_item"          # Remove an item from a character's inventory or a location
    CHANGE_RELATIONSHIP = "change_relationship" # Change the relationship value between two characters
    TRIGGER_EVENT = "trigger_event"        # Trigger a new event (by ID)
    SEND_MESSAGE = "send_message"          # Send a specific message (e.g., GM narration, system message)
    UPDATE_FLAG = "update_flag"            # Set or update a narrative flag in the game state
    # +++ Add new types for character attributes/skills +++
    UPDATE_CHARACTER_ATTRIBUTE = "update_character_attribute" # Update a specific attribute of a character instance
    UPDATE_CHARACTER_SKILL = "update_character_skill"      # Update a specific skill of a character instance
    CHANGE_LOCATION = "change_location"            # Change the location of a character instance
    # Add more types as needed, e.g., LEARN_INFO, APPLY_STATUS_EFFECT

class Consequence(BaseModel):
    """Represents a single structured consequence of an action or event."""
    type: ConsequenceType = Field(..., description="The type of consequence.")
    target_entity_id: Optional[str] = Field(None, description="The ID of the primary entity affected (e.g., character ID for attribute/skill changes).")
    attribute_name: Optional[str] = Field(None, description="The name of the attribute being changed (used with UPDATE_ATTRIBUTE, UPDATE_CHARACTER_ATTRIBUTE).")
    skill_name: Optional[str] = Field(None, description="The name of the skill being changed (used with UPDATE_CHARACTER_SKILL).") # +++ Add skill_name +++
    value: Any = Field(None, description="The change amount (e.g., +1, -2 for attributes/skills) or new value (depends on type).") # Clarified description
    item_id: Optional[str] = Field(None, description="The ID of the item being added or removed (used with ADD_ITEM, REMOVE_ITEM).")
    secondary_entity_id: Optional[str] = Field(None, description="The ID of a secondary entity involved (e.g., the other character in CHANGE_RELATIONSHIP).")
    event_id: Optional[str] = Field(None, description="The ID of the event to be triggered (used with TRIGGER_EVENT).")
    message_content: Optional[str] = Field(None, description="The content of the message to be sent (used with SEND_MESSAGE).")
    message_recipient: Optional[str] = Field("PLAYER", description="The recipient of the message ('PLAYER', 'DM', or specific character ID). Default is 'PLAYER'.")
    flag_name: Optional[str] = Field(None, description="The name of the flag being set or updated (used with UPDATE_FLAG).")
    flag_value: Optional[bool] = Field(None, description="The boolean value to set the flag to (used with UPDATE_FLAG).")
    # Optional metadata for context or debugging
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata for context or debugging.")

    class Config:
        pass # Default behavior: use Enum members, Pydantic handles conversion from string values on load


# +++ 新增：记录实际应用的后果和触发的事件 +++

class AppliedConsequenceRecord(BaseModel):
    """记录一个已成功应用到游戏状态的机制性后果"""
    timestamp: datetime = Field(default_factory=datetime.now, description="后果应用的时间戳")
    round_number: int = Field(..., description="后果应用的具体回合数")
    source_description: str = Field(..., description="触发此后果的来源描述 (例如: '玩家A的行动', '事件X的结局Y')")
    applied_consequence: Consequence = Field(..., description="实际应用的后果对象")
    # 可以添加更多元数据，例如应用前的状态值等用于调试

class TriggeredEventRecord(BaseModel):
    """记录一个已成功触发的事件及其结局"""
    timestamp: datetime = Field(default_factory=datetime.now, description="事件触发的时间戳")
    round_number: int = Field(..., description="事件触发的具体回合数")
    event_id: str = Field(..., description="触发的剧本事件ID (ScenarioEvent.event_id)")
    outcome_id: str = Field(..., description="实际发生的结局ID (EventOutcome.id)")
    trigger_source: str = Field(..., description="触发事件的来源描述 (例如: '玩家A的行动', '环境变化')")
