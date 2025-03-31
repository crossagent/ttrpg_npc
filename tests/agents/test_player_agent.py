import pytest
import asyncio
import uuid
import os
import traceback # Import traceback
from datetime import datetime, timedelta
from typing import List, Optional, Any # Added Any for model_client flexibility

# Import necessary models and classes
from src.models.scenario_models import (
    Scenario, StoryInfo, ScenarioCharacterInfo, LocationInfo, ItemInfo,
    StoryStructure, StoryChapter, StorySection, StoryStage
)
from src.models.game_state_models import (
    GameState, ProgressStatus, EnvironmentStatus, CharacterInstance,
    CharacterStatus, LocationStatus, ItemStatus, MessageReadMemory, MessageStatus # Import MessageReadMemory, MessageStatus
)
from src.models.message_models import Message, MessageType
from src.models.action_models import PlayerAction, ActionType # Import ActionType
from src.agents.player_agent import PlayerAgent
from src.config import config_loader

# --- Constants for Mock Data ---
MOCK_SCENARIO_ID_PLAYER = "test_scenario_player_001"
MOCK_PLAYER_CHAR_ID = "char_hero_player"
MOCK_NPC_CHAR_ID = "char_npc_player"
MOCK_LOC_ID_PLAYER = "loc_forest_player"
MOCK_STAGE_ID_PLAYER = "stage_encounter_player"
MOCK_SECTION_ID_PLAYER = "section_travel_player"
MOCK_CHAPTER_ID_PLAYER = "chapter_1_player"

# --- Fixtures ---

# Re-use llm_model_client fixture if defined in conftest.py or import from another test file
# For simplicity here, we redefine it, but sharing via conftest.py is better practice.
@pytest.fixture(scope="module")
def llm_model_client() -> Optional[Any]:
    """Fixture to load LLM configuration and initialize a model client."""
    model_client = None
    try:
        config_path = os.path.join('config', 'llm_settings.yaml')
        print(f"\nLoading LLM config from: {config_path}")
        if not os.path.exists(config_path):
             print(f"Warning: Config file not found at {config_path}, LLM tests might be skipped.")
             return None
        llm_config = config_loader.load_llm_config(config_path)
        model_client_config = next(iter(llm_config.model_clients.values()), None)
        if not model_client_config:
            print("Warning: No model client configured, LLM tests might be skipped.")
            return None
        model_client = config_loader.get_model_client(model_client_config)
        print(f"LLM Config loaded successfully for tests. Using client: {model_client_config.client_type}")
        return model_client
    except Exception as e:
        print(f"Warning: Error loading LLM config during test setup: {e}")
    return None

@pytest.fixture(scope="module")
def mock_player_scenario() -> Scenario:
    """Fixture to create a mock Scenario for PlayerAgent tests."""
    scenario = Scenario(
        scenario_id=MOCK_SCENARIO_ID_PLAYER,
        story_info=StoryInfo(
            id="test_story_player",
            title="Player Test Adventure",
            background="A test adventure focusing on player decision making in a forest encounter.",
            narrative_style="Action-oriented fantasy",
            secrets={"main_secret": "The NPC is lost."}
        ),
        characters={
            MOCK_PLAYER_CHAR_ID: ScenarioCharacterInfo(
                character_id=MOCK_PLAYER_CHAR_ID, name="Player Hero", public_identity="Adventurer",
                secret_goal="Find the hidden shrine.", background="Seeking ancient artifacts.",
                special_ability="Detect Magic", weakness="Fear of spiders"
            ),
            MOCK_NPC_CHAR_ID: ScenarioCharacterInfo(
                character_id=MOCK_NPC_CHAR_ID, name="Lost Merchant", public_identity="Merchant",
                secret_goal="Find the way back to town.", background="Got separated from his caravan.",
                special_ability=None, weakness="Poor sense of direction"
            )
        },
        events=[],
        locations={ MOCK_LOC_ID_PLAYER: LocationInfo(description="A dense forest path...") },
        items={},
        story_structure=StoryStructure(chapters=[StoryChapter(id=MOCK_CHAPTER_ID_PLAYER, name="C1", description="D", sections=[StorySection(id=MOCK_SECTION_ID_PLAYER, name="S1", description="D", stages=[StoryStage(id=MOCK_STAGE_ID_PLAYER, name="Encounter", description="D", objective="Interact", locations=[MOCK_LOC_ID_PLAYER], characters=[MOCK_PLAYER_CHAR_ID, MOCK_NPC_CHAR_ID], events=[])])])])
    )
    print("Mock Player Scenario fixture created.")
    return scenario

@pytest.fixture
def mock_player_game_state(mock_player_scenario: Scenario) -> GameState:
    """Fixture to create a mock GameState for PlayerAgent tests."""
    start_time = datetime.now()
    current_stage_obj = mock_player_scenario.story_structure.chapters[0].sections[0].stages[0]
    msg1_id = f"msg_{uuid.uuid4()}"
    msg2_id = f"msg_{uuid.uuid4()}" # This will be the unread message

    player_instance = CharacterInstance(
        character_id=MOCK_PLAYER_CHAR_ID, instance_id=f"inst_{MOCK_PLAYER_CHAR_ID}",
        public_identity=mock_player_scenario.characters[MOCK_PLAYER_CHAR_ID].public_identity,
        name=mock_player_scenario.characters[MOCK_PLAYER_CHAR_ID].name, player_controlled=True,
        status=CharacterStatus(character_id=MOCK_PLAYER_CHAR_ID, location=MOCK_LOC_ID_PLAYER, health=100)
    )
    npc_instance = CharacterInstance(
        character_id=MOCK_NPC_CHAR_ID, instance_id=f"inst_{MOCK_NPC_CHAR_ID}",
        public_identity=mock_player_scenario.characters[MOCK_NPC_CHAR_ID].public_identity,
        name=mock_player_scenario.characters[MOCK_NPC_CHAR_ID].name, player_controlled=False,
        status=CharacterStatus(character_id=MOCK_NPC_CHAR_ID, location=MOCK_LOC_ID_PLAYER, health=80)
    )
    player_status = CharacterStatus(character_id=MOCK_PLAYER_CHAR_ID, location=MOCK_LOC_ID_PLAYER, health=100)
    npc_status = CharacterStatus(character_id=MOCK_NPC_CHAR_ID, location=MOCK_LOC_ID_PLAYER, health=80)
    loc_status = LocationStatus(
        location_id=MOCK_LOC_ID_PLAYER,
        present_characters=[MOCK_PLAYER_CHAR_ID, MOCK_NPC_CHAR_ID],
        description_state="Broken branches litter the path."
    )

    game_state = GameState(
        game_id=f"test_game_player_{uuid.uuid4()}",
        scenario_id=MOCK_SCENARIO_ID_PLAYER,
        round_number=3, max_rounds=10, started_at=start_time, last_updated=start_time,
        progress=ProgressStatus(
            current_chapter_id=MOCK_CHAPTER_ID_PLAYER, current_section_id=MOCK_SECTION_ID_PLAYER,
            current_stage_id=MOCK_STAGE_ID_PLAYER, current_stage=current_stage_obj
        ),
        environment=EnvironmentStatus(
            current_location_id=MOCK_LOC_ID_PLAYER, time=start_time, weather="Sunny",
            atmosphere="Tense", lighting="Bright"
        ),
        scenario=mock_player_scenario,
        characters={ MOCK_PLAYER_CHAR_ID: player_instance, MOCK_NPC_CHAR_ID: npc_instance },
        character_states={ MOCK_PLAYER_CHAR_ID: player_status, MOCK_NPC_CHAR_ID: npc_status },
        location_states={ MOCK_LOC_ID_PLAYER: loc_status },
        item_states={}, event_instances={},
        chat_history=[
            Message(
                message_id=msg1_id, type=MessageType.NARRATIVE, source="DM", target="all",
                content="You hear rustling... a merchant looking lost.",
                timestamp=(start_time - timedelta(minutes=2)).isoformat()
            ),
             Message(
                message_id=msg2_id, type=MessageType.DIALOGUE, source=MOCK_NPC_CHAR_ID, target=MOCK_PLAYER_CHAR_ID,
                content="Oh, thank goodness! Can you help me?",
                timestamp=(start_time - timedelta(minutes=1)).isoformat()
            )
        ]
    )
    print("Mock Player GameState fixture created.")
    # Store message IDs for later use in agent memory setup
    game_state._test_msg1_id = msg1_id # Use a temporary attribute for test setup
    game_state._test_msg2_id = msg2_id
    return game_state

@pytest.fixture
def player_agent_instance(llm_model_client: Optional[Any]) -> PlayerAgent:
    """Fixture to initialize the PlayerAgent for tests."""
    agent = PlayerAgent(
        agent_id="player_agent_test_instance",
        agent_name="HeroAgent",
        character_id=MOCK_PLAYER_CHAR_ID, # Associate with the player character
        model_client=llm_model_client
    )
    print("PlayerAgent instance fixture created.")
    return agent

@pytest.fixture
def player_agent_with_memory(player_agent_instance: PlayerAgent, mock_player_game_state: GameState) -> PlayerAgent:
    """Fixture to set up PlayerAgent's message memory for tests."""
    agent = player_agent_instance
    msg1_id = getattr(mock_player_game_state, '_test_msg1_id', None)
    msg2_id = getattr(mock_player_game_state, '_test_msg2_id', None)

    if msg1_id:
        agent.message_memory.history_messages[msg1_id] = MessageStatus(message_id=msg1_id, read_status=True, read_timestamp=datetime.now())
    if msg2_id:
        agent.message_memory.history_messages[msg2_id] = MessageStatus(message_id=msg2_id, read_status=False) # UNREAD

    print(f"Simulated message memory for PlayerAgent: Message '{msg1_id}' read, '{msg2_id}' unread.")
    return agent


# --- Test Functions ---

@pytest.mark.asyncio
async def test_player_decide_action(
    player_agent_with_memory: PlayerAgent, # Use the agent with pre-set memory
    mock_player_game_state: GameState,
    mock_player_scenario: Scenario
):
    """
    测试 PlayerAgent 的行动决策功能 (player_decide_action)
    """
    print("\n--- Running test_player_decide_action ---")
    agent = player_agent_with_memory
    if not agent.model_client:
        pytest.skip("LLM model client not initialized, skipping LLM-dependent test.")

    # Get the character info for the player agent
    player_char_info = mock_player_scenario.characters.get(MOCK_PLAYER_CHAR_ID)
    assert player_char_info is not None, f"Character info not found for ID {MOCK_PLAYER_CHAR_ID}"

    # Check initial unread count (should be 1 based on fixture setup)
    initial_unread_count = agent.get_unread_messages_count()
    print(f"Initial unread messages: {initial_unread_count}")
    assert initial_unread_count == 1, "Agent should have 1 unread message initially"

    try:
        # The method internally gets unread messages based on agent's memory
        action: PlayerAction = await agent.player_decide_action(
            game_state=mock_player_game_state,
            charaInfo=player_char_info
        )
        print("\n--- Generated Player Action (Test) ---")
        # Use model_dump_json for better readability of Pydantic object
        print(action.model_dump_json(indent=2))
        print("-------------------------------------\n")

        # Add assertions
        assert isinstance(action, PlayerAction), "Result should be a PlayerAction object"
        assert action.character_id == MOCK_PLAYER_CHAR_ID, "Action character ID should match agent's ID"
        assert isinstance(action.action_type, ActionType), "Action type should be an ActionType enum"
        assert isinstance(action.content, str) and len(action.content) > 0, "Action content should be a non-empty string"
        # assert action.interal_thoughts is not None, "Internal thoughts should be generated" # Check if thoughts are expected

        # Verify that the unread message was marked as read
        final_unread_count = agent.get_unread_messages_count()
        print(f"Final unread messages: {final_unread_count}")
        assert final_unread_count == 0, "Agent should have 0 unread messages after deciding action"
        msg2_id = getattr(mock_player_game_state, '_test_msg2_id', None)
        if msg2_id:
             assert agent.message_memory.history_messages[msg2_id].read_status is True, f"Message {msg2_id} should be marked as read"


    except Exception as e:
        pytest.fail(f"Error during player action generation test: {e}\n{traceback.format_exc()}")

# Add more tests, e.g., test_get_unread_messages, test_update_context, test_mark_message_as_read
