import pytest
import asyncio
import uuid
import os
import traceback # Import traceback
from datetime import datetime, timedelta
from typing import Optional, Any, Dict # Added Dict

# Import necessary models and classes
from src.models.scenario_models import (
    Scenario, StoryInfo, ScenarioCharacterInfo, LocationInfo, ItemInfo,
    StoryStructure, StoryChapter, StorySection, StoryStage
)
from src.models.game_state_models import (
    GameState, ProgressStatus, EnvironmentStatus, CharacterInstance,
    CharacterStatus, LocationStatus, ItemStatus
)
from src.models.message_models import Message, MessageType
from src.models.action_models import PlayerAction, ActionType, ActionResult, InternalThoughts # Import ActionType, ActionResult, InternalThoughts
from src.agents.referee_agent import RefereeAgent
from src.config import config_loader
# Note: The original __main__ used OpenAIChatCompletionClient and ModelFamily directly
# We might need to adjust based on how config_loader provides the client
# For now, assume config_loader.get_model_client returns a compatible client object
# from autogen_ext.models.openai import OpenAIChatCompletionClient # Keep if needed, but prefer config_loader
# from autogen_core.models import ModelFamily # Keep if needed

# --- Constants for Mock Data ---
MOCK_SCENARIO_ID_REFEREE = "test_scenario_referee_001"
MOCK_CHAR_ID_REFEREE = "char_hero_referee"
MOCK_LOC_ID_REFEREE = "loc_cave_referee"
MOCK_STAGE_ID_REFEREE = "stage_explore_referee"
MOCK_SECTION_ID_REFEREE = "section_delve_referee"
MOCK_CHAPTER_ID_REFEREE = "chapter_1_referee"

# --- Fixtures ---

# Re-use llm_model_client fixture if defined in conftest.py or import from another test file
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
        # Use the generic get_model_client function
        model_client = config_loader.get_model_client(model_client_config)
        print(f"LLM Config loaded successfully for tests. Using client: {model_client_config.client_type}")
        return model_client
    except Exception as e:
        print(f"Warning: Error loading LLM config during test setup: {e}")
    return None

@pytest.fixture(scope="module")
def mock_referee_scenario() -> Scenario:
    """Fixture to create a mock Scenario for RefereeAgent tests."""
    scenario = Scenario(
        scenario_id=MOCK_SCENARIO_ID_REFEREE,
        story_info=StoryInfo(
            id="test_story_referee", title="Referee Test Adventure",
            background="Testing action resolution in a dark cave.",
            narrative_style="Suspenseful fantasy",
            secrets={"main_secret": "There's treasure behind the waterfall."}
        ),
        characters={
            MOCK_CHAR_ID_REFEREE: ScenarioCharacterInfo(
                character_id=MOCK_CHAR_ID_REFEREE, name="Referee Hero", public_identity="Explorer",
                secret_goal="Map the cave system.", background="Brave adventurer.",
                special_ability="Night Vision", weakness="Claustrophobia"
            )
        },
        events=[],
        locations={ MOCK_LOC_ID_REFEREE: LocationInfo(description="A dark, damp cave.") },
        items={},
        story_structure=StoryStructure(chapters=[StoryChapter(id=MOCK_CHAPTER_ID_REFEREE, name="C1", description="D", sections=[StorySection(id=MOCK_SECTION_ID_REFEREE, name="S1", description="D", stages=[StoryStage(id=MOCK_STAGE_ID_REFEREE, name="Explore", description="D", objective="Find exit", locations=[MOCK_LOC_ID_REFEREE], characters=[MOCK_CHAR_ID_REFEREE], events=[])])])])
    )
    print("Mock Referee Scenario fixture created.")
    return scenario

@pytest.fixture
def mock_referee_game_state(mock_referee_scenario: Scenario) -> GameState:
    """Fixture to create a mock GameState for RefereeAgent tests."""
    start_time = datetime.now()
    current_stage_obj = mock_referee_scenario.story_structure.chapters[0].sections[0].stages[0]
    char_instance = CharacterInstance(
        character_id=MOCK_CHAR_ID_REFEREE, instance_id=f"inst_{MOCK_CHAR_ID_REFEREE}",
        public_identity=mock_referee_scenario.characters[MOCK_CHAR_ID_REFEREE].public_identity,
        name=mock_referee_scenario.characters[MOCK_CHAR_ID_REFEREE].name, player_controlled=True,
        status=CharacterStatus(character_id=MOCK_CHAR_ID_REFEREE, location=MOCK_LOC_ID_REFEREE, health=100)
    )
    char_status = CharacterStatus(character_id=MOCK_CHAR_ID_REFEREE, location=MOCK_LOC_ID_REFEREE, health=100)
    loc_status = LocationStatus(
        location_id=MOCK_LOC_ID_REFEREE, present_characters=[MOCK_CHAR_ID_REFEREE],
        description_state="Loose rocks are scattered on the floor."
    )

    game_state = GameState(
        game_id=f"test_game_referee_{uuid.uuid4()}",
        scenario_id=MOCK_SCENARIO_ID_REFEREE,
        round_number=5, max_rounds=10, started_at=start_time, last_updated=start_time,
        progress=ProgressStatus(
            current_chapter_id=MOCK_CHAPTER_ID_REFEREE, current_section_id=MOCK_SECTION_ID_REFEREE,
            current_stage_id=MOCK_STAGE_ID_REFEREE, current_stage=current_stage_obj
        ),
        environment=EnvironmentStatus(
            current_location_id=MOCK_LOC_ID_REFEREE, time=start_time,
            weather="Underground", atmosphere="Eerie", lighting="Dark"
        ),
        scenario=mock_referee_scenario,
        characters={ MOCK_CHAR_ID_REFEREE: char_instance },
        character_states={ MOCK_CHAR_ID_REFEREE: char_status },
        location_states={ MOCK_LOC_ID_REFEREE: loc_status },
        item_states={}, event_instances={},
        chat_history=[
             Message(
                message_id=f"msg_{uuid.uuid4()}", type=MessageType.NARRATIVE, source="DM", target="all",
                content="You stand at the entrance of a dark cave. What do you do?",
                timestamp=(start_time - timedelta(minutes=1)).isoformat()
            )
        ]
    )
    print("Mock Referee GameState fixture created.")
    return game_state

@pytest.fixture
def mock_player_action() -> PlayerAction:
    """Fixture to create a mock PlayerAction for the Referee to judge."""
    action = PlayerAction(
        character_id=MOCK_CHAR_ID_REFEREE,
        interal_thoughts=InternalThoughts( # Corrected attribute name
            short_term_goals=["Find a light source", "Check for traps"],
            primary_emotion="Cautious",
            psychological_state="Alert",
            narrative_analysis="Entered a dark cave, need to be careful.",
            perceived_risks=["Falling rocks", "Hidden creatures"],
            perceived_opportunities=["Potential treasure", "Secret passage"]
        ),
        action_type=ActionType.ACTION,
        content="I carefully examine the cave walls near the entrance for any loose rocks or hidden switches.",
        target="environment",
        timestamp=datetime.now().isoformat()
    )
    print("Mock PlayerAction fixture created.")
    return action

@pytest.fixture
def referee_agent_instance(llm_model_client: Optional[Any]) -> RefereeAgent:
    """Fixture to initialize the RefereeAgent for tests."""
    agent = RefereeAgent(
        agent_id="referee_agent_test_instance",
        agent_name="ActionJudge",
        model_client=llm_model_client
    )
    print("RefereeAgent instance fixture created.")
    return agent

# --- Test Functions ---

@pytest.mark.asyncio
async def test_judge_action(
    referee_agent_instance: RefereeAgent,
    mock_player_action: PlayerAction,
    mock_referee_game_state: GameState,
    mock_referee_scenario: Scenario
):
    """
    测试 RefereeAgent 的行动判断功能 (judge_action)
    """
    print("\n--- Running test_judge_action ---")
    agent = referee_agent_instance
    if not agent.model_client:
        pytest.skip("LLM model client not initialized, skipping LLM-dependent test.")

    try:
        action_result: ActionResult = await agent.judge_action(
            action=mock_player_action,
            game_state=mock_referee_game_state,
            scenario=mock_referee_scenario
        )
        print("\n--- Generated Action Result (Test) ---")
        # Use model_dump_json for better readability
        print(action_result.model_dump_json(indent=2))
        print("-------------------------------------\n")

        # Add assertions
        assert isinstance(action_result, ActionResult), "Result should be an ActionResult object"
        assert action_result.character_id == mock_player_action.character_id, "Result character ID should match action's character ID"
        assert action_result.action == mock_player_action, "Result should contain the original action"
        assert isinstance(action_result.success, bool), "Success flag should be a boolean"
        assert isinstance(action_result.narrative, str), "Narrative should be a string"
        assert len(action_result.narrative) > 0, "Narrative should not be empty"
        assert isinstance(action_result.state_changes, dict), "State changes should be a dictionary"
        # Add more specific assertions based on expected outcomes if possible
        # e.g., assert action_result.success is True
        # e.g., assert "You find nothing unusual" in action_result.narrative

    except Exception as e:
        pytest.fail(f"Error during action judging test: {e}\n{traceback.format_exc()}")

# Add more tests if needed for different action types or scenarios
