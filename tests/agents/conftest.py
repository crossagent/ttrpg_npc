import pytest
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Any, List
import copy # Import copy for deep copying game state

# Import necessary classes from src
from src.config import config_loader
from src.engine.scenario_manager import ScenarioManager
from src.engine.game_state_manager import GameStateManager
from src.models.scenario_models import Scenario
from src.models.game_state_models import GameState
from src.models.message_models import Message, MessageType
from src.models.action_models import ActionType # Needed for example message
from autogen_ext.models.openai import OpenAIChatCompletionClient
from src.config.config_loader import load_llm_settings, load_config
from autogen_core.models import ModelFamily

# Scope 'module' for fixtures that load data once per test module
# Scope 'function' for fixtures that need a fresh instance per test function

@pytest.fixture(scope="module")
def llm_model_client() -> Optional[Any]:
    """Fixture to load LLM configuration and initialize a model client."""
    model_client = None
    try:
        # Assuming config file is at project_root/config/llm_settings.yaml
        config_path = os.path.join('config', 'llm_settings.yaml')
        print(f"\nLoading LLM config from: {config_path}")
        if not os.path.exists(config_path):
             print(f"Warning: Config file not found at {config_path}, LLM tests might be skipped.")
             pytest.skip(f"LLM config file not found at {config_path}") # Skip instead of returning None
             return None # Should not be reached due to skip

        llm_settings = config_loader.load_llm_settings(config_path)

        # 使用配置初始化模型客户端
        model_client = OpenAIChatCompletionClient(
            model=llm_settings.model,
            api_key=llm_settings.openai_api_key,
            temperature=llm_settings.temperature,
            base_url=llm_settings.base_url,
            model_info={
                "name": llm_settings.model,
                "vision": False,
                "function_calling": False,
                "json_output": False,
                'family': ModelFamily.UNKNOWN
            }
        )
        print(f"LLM Config loaded successfully for tests. Using client: {llm_settings.model}")
        return model_client
    except FileNotFoundError as e:
        print(f"Warning: LLM config file not found during test setup: {e}")
        pytest.skip(f"LLM config file not found: {e}")
    except Exception as e:
        print(f"Warning: Error loading LLM config during test setup: {e}")
        pytest.skip(f"Error loading LLM config: {e}")
    return None # Should not be reached

@pytest.fixture(scope="module")
def scenario_manager() -> ScenarioManager:
    """Provides a ScenarioManager instance."""
    print("Creating ScenarioManager instance for tests.")
    return ScenarioManager()

@pytest.fixture(scope="module")
def game_state_manager() -> GameStateManager:
    """Provides a GameStateManager instance."""
    print("Creating GameStateManager instance for tests.")
    return GameStateManager()

@pytest.fixture(scope="module")
def loaded_scenario(scenario_manager: ScenarioManager) -> Scenario:
    """Loads the default scenario using ScenarioManager."""
    print("Loading default scenario ('default.json') for tests.")
    try:
        scenario = scenario_manager.load_scenario('default')
        print("Default scenario loaded successfully.")
        return scenario
    except ValueError as e:
        pytest.fail(f"Failed to load default scenario: {e}")

@pytest.fixture(scope="module") # Module scope as initial state is based on static scenario
def initial_game_state(game_state_manager: GameStateManager, loaded_scenario: Scenario) -> GameState:
    """Initializes the game state using GameStateManager based on the loaded scenario."""
    print("Initializing base game state from loaded scenario.")
    try:
        state = game_state_manager.initialize_game_state(loaded_scenario)
        print("Base game state initialized successfully.")
        # Ensure player character is marked as player_controlled if applicable
        # Find the player character ID (assuming it's 'player' based on default.json)
        player_char_id = "player" # Adjust if needed based on default.json
        if player_char_id in state.characters:
             state.characters[player_char_id].player_controlled = True
             print(f"Marked character '{player_char_id}' as player_controlled.")
        else:
             print(f"Warning: Character ID '{player_char_id}' not found in initialized state characters.")

        return state
    except ValueError as e:
        pytest.fail(f"Failed to initialize game state: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error initializing game state: {e}")


@pytest.fixture(scope="function") # Function scope to ensure each test gets a modified copy
def round_1_ended_game_state(initial_game_state: GameState) -> GameState:
    """
    Provides a GameState representing the state after round 1 has ended (start of round 2).
    Creates a deep copy of the initial state and modifies it.
    """
    print("Creating 'round 1 ended' game state (start of round 2).")
    # Create a deep copy to avoid modifying the module-scoped initial state
    game_state = copy.deepcopy(initial_game_state)

    # --- Apply 'End of Round 1' Modifications ---
    game_state.round_number = 2
    game_state.last_updated = datetime.now() # Update timestamp

    # Add example chat history for round 1
    player_char_id = "player" # Assuming 'player' is the main player character ID
    npc_char_id = "elara"    # Assuming 'elara' is an NPC in default.json

    # Example DM Narrative (Start of Game)
    msg1_id = f"msg_{uuid.uuid4()}"
    msg1_ts = (game_state.started_at + timedelta(seconds=10)).isoformat()
    game_state.chat_history.append(
        Message(
            message_id=msg1_id,
            type=MessageType.DM,
            source="DM",
            target="all",
            content="阳光透过酒馆的彩色玻璃窗，空气中弥漫着麦芽和旧木头的味道。吟游诗人艾拉拉坐在角落里，轻轻拨动着她的鲁特琴。你想做什么？",
            timestamp=msg1_ts,
            round_id = 1,
            recipients=["elara", "player"], # Assuming both player and NPC are recipients
        )
    )

    # Example Player Action (Round 1)
    msg2_id = f"msg_{uuid.uuid4()}"
    msg2_ts = (game_state.started_at + timedelta(seconds=30)).isoformat()
    game_state.chat_history.append(
        Message(
            message_id=msg2_id,
            type=MessageType.ACTION,
            source=player_char_id,
            target="environment", # Or target Elara if interacting directly
            content="我走向艾拉拉，想问问她最近有没有听到什么有趣的传闻。",
            timestamp=msg2_ts,
            round_id = 1,
            recipients=["elara", "player"], # Assuming both player and NPC are recipients
        )
    )

    # Example DM Response / NPC Dialogue (End of Round 1 / Start of Round 2 context)
    msg3_id = f"msg_{uuid.uuid4()}"
    msg3_ts = (game_state.started_at + timedelta(minutes=1)).isoformat() # Simulate time passing
    game_state.chat_history.append(
        Message(
            message_id=msg3_id,
            type=MessageType.DM, # Or NARRATIVE if DM describes Elara's reaction
            source=npc_char_id, # Or DM
            target=player_char_id,
            content="艾拉拉抬起头，微笑着说：“冒险者，你来得正好。确实有些奇怪的事情在发生……”",
            timestamp=msg3_ts,
            round_id = 1,
            recipients=["elara", "player"], # Assuming both player and NPC are recipients
        )
    )

    # Optional: Modify character/location state slightly
    if player_char_id in game_state.character_states:
        game_state.character_states[player_char_id].health = 98 # Minor change example
        print(f"Slightly modified state for character '{player_char_id}'.")

    if game_state.environment.current_location_id in game_state.location_states:
        game_state.location_states[game_state.environment.current_location_id].description_state = "角落里艾拉拉的鲁特琴声吸引了一些目光。"
        print(f"Slightly modified state for location '{game_state.environment.current_location_id}'.")

    print(f"'Round 1 ended' game state created with {len(game_state.chat_history)} messages.")
    # Store message IDs for potential use in player agent memory setup
    game_state._test_chat_ids = [msg.message_id for msg in game_state.chat_history]

    return game_state
