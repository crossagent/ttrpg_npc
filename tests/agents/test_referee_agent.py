import pytest
import asyncio
import traceback # Import traceback
from datetime import datetime # Keep datetime for action timestamp
from typing import Optional, Any, Dict # Added Dict

# Import necessary models and classes
from src.models.scenario_models import Scenario # Needed for type hints

from src.models.game_state_models import GameState
from src.models.action_models import PlayerAction, ActionType, ActionResult, InternalThoughts # Import ActionType, ActionResult, InternalThoughts
from src.agents.referee_agent import RefereeAgent

# --- Fixtures ---
# llm_model_client, loaded_scenario, initial_game_state, round_1_ended_game_state
# are now provided by tests/agents/conftest.py

# Define the player character ID used in the default scenario
PLAYER_CHAR_ID = "player" # Assuming 'player' is the one performing actions

@pytest.fixture
def referee_agent_instance(llm_model_client: Optional[Any]) -> RefereeAgent:
    """Fixture to initialize the RefereeAgent for tests, using shared LLM client."""
    # llm_model_client is automatically injected from conftest.py
    agent = RefereeAgent(
        agent_id="referee_agent_test_instance",
        agent_name="ActionJudge",
        model_client=llm_model_client
    )
    print("RefereeAgent instance fixture created.")
    return agent

# Removed mock_player_action fixture, action will be created in the test function

# --- Test Functions ---

# --- Test Functions ---

@pytest.mark.asyncio
async def test_judge_action(
    referee_agent_instance: RefereeAgent,
    round_1_ended_game_state: GameState # Use the game state from conftest
):
    """
    测试 RefereeAgent 的行动判断功能 (judge_action),
    使用从 conftest.py 加载并模拟到第一回合结束的游戏状态。
    """
    print("\n--- Running test_judge_action ---")
    agent = referee_agent_instance
    game_state = round_1_ended_game_state
    scenario = game_state.scenario

    # The llm_model_client fixture in conftest handles skipping if client is None
    if not agent.model_client:
         pytest.skip("LLM model client not available for RefereeAgent.")

    # --- Create a PlayerAction relevant to the round_1_ended_game_state context ---
    # The last message in round_1_ended_game_state is Elara saying "确实有些奇怪的事情在发生……"
    # Let's create an action where the player asks Elara for details.
    player_action = PlayerAction(
        character_id=PLAYER_CHAR_ID,
        interal_thoughts=InternalThoughts( # Example thoughts
            short_term_goals=["了解奇怪的事情是什么", "评估危险性"],
            primary_emotion="好奇",
            psychological_state="专注",
            narrative_analysis="艾拉拉提到了奇怪的事情，这是获取信息的关键机会。",
            perceived_risks=["可能卷入麻烦"],
            perceived_opportunities=["获得任务线索", "了解本地情况"]
        ),
        action_type=ActionType.TALK, # Dialogue action
        content="哦？什么样的奇怪事情？请详细说说。", # Player asks Elara
        target="elara", # Target the NPC Elara
        timestamp=datetime.now().isoformat()
    )
    print("\n--- Player Action to be Judged ---")
    print(player_action.model_dump_json(indent=2))
    print("----------------------------------")

    print(f"Using game state at round {game_state.round_number}.")

    try:
        action_result: ActionResult = await agent.judge_action(
            action=player_action,
            game_state=game_state,
            scenario=scenario
        )
        print("\n--- Generated Action Result (Test) ---")
        # Use model_dump_json for better readability
        print(action_result.model_dump_json(indent=2))
        print("------------------------------------")

        # Basic assertions
        assert isinstance(action_result, ActionResult), "结果应该是一个 ActionResult 对象"
        assert action_result.character_id == player_action.character_id, "结果的角色 ID 应该匹配行动的角色 ID"
        assert action_result.action == player_action, "结果应该包含原始的行动对象"
        assert isinstance(action_result.success, bool), "Success 标志应该是一个布尔值"
        assert isinstance(action_result.narrative, str), "叙述应该是一个字符串"
        # Narrative might be empty if only state changes occur, but usually not for dialogue
        # assert len(action_result.narrative) > 0, "叙述不应为空"
        assert isinstance(action_result.state_changes, Dict), "状态变化应该是一个字典"
        # More specific assertions based on expected outcomes
        # For a simple dialogue question, success should likely be True
        assert action_result.success is True, "询问详情的对话行动应该成功"
        # The narrative might describe Elara's reaction or start her explanation
        # assert "艾拉拉" in action_result.narrative or "Elara" in action_result.narrative

    except Exception as e:
        print(f"Error during action judging test: {e}")
        print(traceback.format_exc()) # Print traceback for debugging
        pytest.fail(f"Action judging test failed: {e}")

# Add more tests if needed for different action types or scenarios,
# using the round_1_ended_game_state fixture as the starting point.
