import pytest
import asyncio
import uuid
import os
import traceback # Import traceback module
from datetime import datetime, timedelta
from typing import List, Optional, Any # Added Any for model_client flexibility

# Import necessary models and classes from the src directory
from src.models.scenario_models import (
    Scenario, StoryInfo, ScenarioCharacterInfo, LocationInfo, ItemInfo,
    StoryStructure, StoryChapter, StorySection, StoryStage
)
from src.models.game_state_models import (
    GameState, ProgressStatus, EnvironmentStatus, CharacterInstance,
    CharacterStatus, LocationStatus, ItemStatus
)
from src.models.message_models import Message, MessageType
from src.agents.dm_agent import DMAgent
from src.config import config_loader

# --- Constants for Mock Data ---
MOCK_SCENARIO_ID_DM = "test_scenario_dm_001"
MOCK_CHAR_ID_DM = "char_hero_dm"
MOCK_LOC_ID_DM = "loc_tavern_dm"
MOCK_STAGE_ID_DM = "stage_intro_dm"
MOCK_SECTION_ID_DM = "section_start_dm"
MOCK_CHAPTER_ID_DM = "chapter_1_dm"

# --- Fixtures for Mock Data and Agent ---

@pytest.fixture(scope="module")
def llm_model_client() -> Optional[Any]:
    """Fixture to load LLM configuration and initialize a model client."""
    model_client = None
    try:
        # Assuming config file is at project_root/config/llm_settings.yaml
        # pytest runs from the project root usually
        config_path = os.path.join('config', 'llm_settings.yaml')
        print(f"\nLoading LLM config from: {config_path}")
        if not os.path.exists(config_path):
             print(f"Warning: Config file not found at {config_path}, LLM tests might be skipped.")
             return None # Return None if config not found

        llm_config = config_loader.load_llm_config(config_path)
        # Get the first configured model client for testing
        model_client_config = next(iter(llm_config.model_clients.values()), None)
        if not model_client_config:
            print("Warning: No model client configured in llm_settings.yaml, LLM tests might be skipped.")
            return None # Return None if no client configured

        model_client = config_loader.get_model_client(model_client_config)
        print(f"LLM Config loaded successfully for tests. Using client: {model_client_config.client_type}")
        return model_client
    except FileNotFoundError as e:
        print(f"Warning: LLM config file not found during test setup: {e}")
    except Exception as e:
        print(f"Warning: Error loading LLM config during test setup: {e}")
    return None # Return None in case of errors

@pytest.fixture(scope="module")
def mock_dm_scenario() -> Scenario:
    """Fixture to create a mock Scenario for DM tests."""
    scenario = Scenario(
        scenario_id=MOCK_SCENARIO_ID_DM,
        story_info=StoryInfo(
            id="test_story_dm",
            title="DM Test Adventure",
            background="A simple test adventure focusing on DM narrative generation in a tavern.",
            narrative_style="Descriptive fantasy",
            secrets={"main_secret": "The ale is magical."}
        ),
        characters={
            MOCK_CHAR_ID_DM: ScenarioCharacterInfo(
                character_id=MOCK_CHAR_ID_DM,
                name="DM Hero",
                public_identity="Tavern Patron",
                secret_goal="Observe the surroundings.",
                background="Just arrived.",
                special_ability=None,
                weakness=None
            )
        },
        events=[],
        locations={
            MOCK_LOC_ID_DM: LocationInfo(
                description="A dimly lit tavern. The air smells of stale ale and sawdust. A few patrons nurse their drinks."
            )
        },
        items={},
        story_structure=StoryStructure(
            chapters=[
                StoryChapter(
                    id=MOCK_CHAPTER_ID_DM, name="Chapter 1", description="Arrival",
                    sections=[
                        StorySection(
                            id=MOCK_SECTION_ID_DM, name="Section 1", description="Entering",
                            stages=[
                                StoryStage(
                                    id=MOCK_STAGE_ID_DM, name="Tavern Entrance", description="Stepping into the tavern",
                                    objective="Get a feel for the place.",
                                    locations=[MOCK_LOC_ID_DM],
                                    characters=[MOCK_CHAR_ID_DM],
                                    events=[]
                                )
                            ]
                        )
                    ]
                )
            ]
        )
    )
    print("Mock DM Scenario fixture created.")
    return scenario

@pytest.fixture
def mock_dm_game_state(mock_dm_scenario: Scenario) -> GameState:
    """Fixture to create a mock GameState for DM tests, dependent on the scenario."""
    start_time = datetime.now()
    current_stage_obj = mock_dm_scenario.story_structure.chapters[0].sections[0].stages[0]
    char_instance = CharacterInstance(
        character_id=MOCK_CHAR_ID_DM,
        instance_id=f"inst_{MOCK_CHAR_ID_DM}",
        public_identity=mock_dm_scenario.characters[MOCK_CHAR_ID_DM].public_identity,
        name=mock_dm_scenario.characters[MOCK_CHAR_ID_DM].name,
        player_controlled=True,
        status=CharacterStatus(
            character_id=MOCK_CHAR_ID_DM,
            location=MOCK_LOC_ID_DM,
            health=95 # Slightly damaged
        )
    )
    char_status = CharacterStatus(
        character_id=MOCK_CHAR_ID_DM,
        location=MOCK_LOC_ID_DM,
        health=95
    )
    loc_status = LocationStatus(
        location_id=MOCK_LOC_ID_DM,
        present_characters=[MOCK_CHAR_ID_DM], # Only our hero is present
        description_state="A puddle of spilled ale darkens the floor near the bar."
    )

    game_state = GameState(
        game_id=f"test_game_dm_{uuid.uuid4()}",
        scenario_id=MOCK_SCENARIO_ID_DM,
        round_number=2, # Start at round 2 for context
        max_rounds=10,
        started_at=start_time,
        last_updated=start_time,
        progress=ProgressStatus(
            current_chapter_id=MOCK_CHAPTER_ID_DM,
            current_section_id=MOCK_SECTION_ID_DM,
            current_stage_id=MOCK_STAGE_ID_DM,
            current_stage=current_stage_obj # Cache current stage object
        ),
        environment=EnvironmentStatus(
            current_location_id=MOCK_LOC_ID_DM,
            time=start_time,
            weather="Overcast",
            atmosphere="Quiet Murmurs",
            lighting="Dim"
        ),
        scenario=mock_dm_scenario, # Embed scenario instance
        characters={MOCK_CHAR_ID_DM: char_instance},
        character_states={MOCK_CHAR_ID_DM: char_status},
        location_states={MOCK_LOC_ID_DM: loc_status},
        item_states={},
        event_instances={},
        chat_history=[
            Message(
                message_id=f"msg_{uuid.uuid4()}",
                type=MessageType.NARRATIVE,
                source="DM",
                target="all",
                content="The heavy oak door creaks open as you step into The Drunken Dragon tavern.",
                timestamp=(start_time - timedelta(minutes=5)).isoformat() # Previous message
            ),
             Message(
                message_id=f"msg_{uuid.uuid4()}",
                type=MessageType.ACTION,
                source=MOCK_CHAR_ID_DM, # Character ID as source
                target="environment", # Targetting the environment
                content="I look around the tavern, taking note of the patrons and the general atmosphere.",
                timestamp=(start_time - timedelta(minutes=1)).isoformat() # Most recent action
            )
        ]
    )
    print("Mock DM GameState fixture created.")
    return game_state

@pytest.fixture
def dm_agent_instance(llm_model_client: Optional[Any]) -> DMAgent:
    """Fixture to initialize the DMAgent for tests."""
    agent = DMAgent(agent_id="dm_agent_test_instance", agent_name="NarrativeDM", model_client=llm_model_client)
    print("DMAgent instance fixture created.")
    return agent

# --- Test Functions ---

@pytest.mark.asyncio # Mark test as async
async def test_dm_generate_narrative(
    dm_agent_instance: DMAgent,
    mock_dm_game_state: GameState,
    mock_dm_scenario: Scenario
):
    """
    测试 DMAgent 的叙述生成功能 (dm_generate_narrative)
    """
    print("\n--- Running test_dm_generate_narrative ---")
    if not dm_agent_instance.model_client:
        pytest.skip("LLM model client not initialized, skipping LLM-dependent test.")

    # Prepare relevant messages (Example: last action message)
    relevant_messages: List[Message] = [
        msg for msg in mock_dm_game_state.chat_history if msg.type == MessageType.ACTION
    ]
    # Get the last one if exists, otherwise try last narrative, else empty list
    if relevant_messages:
        historical_context = relevant_messages[-1:]
    else:
        narrative_messages = [
            msg for msg in mock_dm_game_state.chat_history if msg.type == MessageType.NARRATIVE
        ]
        historical_context = narrative_messages[-1:] if narrative_messages else []


    print(f"Providing {len(historical_context)} relevant message(s) as context.")

    try:
        narrative: str = await dm_agent_instance.dm_generate_narrative(
            game_state=mock_dm_game_state,
            scenario=mock_dm_scenario,
            historical_messages=historical_context
        )
        print("\n--- Generated Narrative (Test) ---")
        print(narrative)
        print("----------------------------------\n")

        # Add assertions
        assert isinstance(narrative, str), "Narrative should be a string"
        assert len(narrative) > 10, "Narrative seems too short" # Basic check
        # TODO: Add more specific assertions based on expected output patterns if possible
        # e.g., assert "tavern" in narrative.lower()

    except Exception as e:
        pytest.fail(f"Error during DM narrative generation test: {e}\n{traceback.format_exc()}")

# Add more test functions here if needed for other DMAgent methods or scenarios
