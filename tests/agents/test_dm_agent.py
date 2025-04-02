import pytest
import asyncio
from typing import List, Optional, Any # Added Any for model_client flexibility
import traceback # Keep traceback for error reporting

# Import necessary models and classes from the src directory
# Scenario is needed if we access game_state.scenario
from src.models.scenario_models import Scenario

# Import necessary models and classes from the src directory
from src.models.scenario_models import (
    Scenario, StoryInfo, ScenarioCharacterInfo, LocationInfo, ItemInfo,
    StoryStructure, StoryChapter, StorySection, StoryStage
)
from src.models.game_state_models import (
    GameState, ProgressStatus, EnvironmentStatus, CharacterInstance,
    LocationStatus, ItemStatus
)
from src.models.message_models import Message, MessageType
from src.agents.dm_agent import DMAgent
from src.config import config_loader

# --- Fixtures ---
# llm_model_client, loaded_scenario, initial_game_state, round_1_ended_game_state
# are now provided by tests/agents/conftest.py

@pytest.fixture
def dm_agent_instance(llm_model_client: Optional[Any]) -> DMAgent:
    """Fixture to initialize the DMAgent for tests, using shared LLM client."""
    # llm_model_client is automatically injected from conftest.py
    agent = DMAgent(agent_id="dm_agent_test_instance", agent_name="NarrativeDM", model_client=llm_model_client)
    print("DMAgent instance fixture created.")
    return agent

# --- Test Functions ---

@pytest.mark.asyncio
async def test_dm_generate_narrative(
    dm_agent_instance: DMAgent,
    round_1_ended_game_state: GameState # Use the fixture from conftest.py
):
    """
    测试 DMAgent 的叙述生成功能 (dm_generate_narrative),
    使用从 conftest.py 加载并模拟到第一回合结束的游戏状态。
    """
    print("\n--- Running test_dm_generate_narrative ---")
    # The llm_model_client fixture in conftest handles skipping if client is None
    if not dm_agent_instance.model_client:
         pytest.skip("LLM model client not available for DMAgent.") # Should be skipped by fixture already

    game_state = round_1_ended_game_state
    scenario = game_state.scenario # Get scenario from the game state

    # Prepare relevant messages based on the game state's chat history
    # Example: Use the last message as context, regardless of type, or last action/dialogue
    if game_state.chat_history:
        historical_context = game_state.chat_history[-1:] # Use the very last message
    else:
        historical_context = []

    print(f"Using game state at round {game_state.round_number}.")
    print(f"Providing {len(historical_context)} historical message(s) as context:")
    for msg in historical_context:
        print(f"  - [{msg.type.name}] {msg.source}: {msg.content[:50]}...")

    try:
        narrative: str = await dm_agent_instance.dm_generate_narrative(
            game_state=game_state,
            scenario=scenario, # Pass the scenario from the game state
            historical_messages=historical_context
        )
        print("\n--- Generated Narrative (Test) ---")
        print(narrative) # Print the full narrative
        print("----------------------------------")

        # Basic assertions
        assert isinstance(narrative, str), "生成的叙述应该是一个字符串"
        assert len(narrative) > 10, "生成的叙述似乎太短了"
        # More specific assertions could check if the narrative logically follows
        # the last message in historical_context (e.g., responds to the player action/dialogue)
        # assert "艾拉拉" in narrative or "Elara" in narrative # Example check based on context

    except Exception as e:
        print(f"Error during DM narrative generation test: {e}")
        print(traceback.format_exc()) # Print traceback for debugging
        pytest.fail(f"DM narrative generation test failed: {e}")

# Add more test functions here if needed for other DMAgent methods or scenarios,
# using the round_1_ended_game_state fixture as the starting point.
