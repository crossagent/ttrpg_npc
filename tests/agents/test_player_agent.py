import pytest
import asyncio
import traceback # Import traceback
from datetime import datetime # Keep datetime if needed for memory setup
from typing import Optional, Any # Added Any for model_client flexibility

# Import necessary models and classes
# Scenario needed for ScenarioCharacterInfo type hint
from src.models.scenario_models import Scenario, ScenarioCharacterInfo

from src.models.game_state_models import GameState, MessageStatus # Import MessageStatus
from src.models.action_models import PlayerAction, ActionType # Import ActionType
from src.agents.player_agent import PlayerAgent

# --- Fixtures ---
# llm_model_client, loaded_scenario, initial_game_state, round_1_ended_game_state
# are now provided by tests/agents/conftest.py

# Define the player character ID used in the default scenario
PLAYER_CHAR_ID = "char_001"

@pytest.fixture
def player_agent_instance(llm_model_client: Optional[Any]) -> PlayerAgent:
    """Fixture to initialize the PlayerAgent for tests, using shared LLM client."""
    # llm_model_client is automatically injected from conftest.py
    agent = PlayerAgent(
        agent_id="player_agent_test_instance",
        agent_name="HeroAgent",
        character_id=PLAYER_CHAR_ID, # Use the ID from the loaded scenario
        model_client=llm_model_client
    )
    print(f"PlayerAgent instance created for character '{PLAYER_CHAR_ID}'.")
    return agent

# Removed player_agent_with_memory fixture, memory setup will be done in the test function


# --- Test Functions ---

# --- Test Functions ---

@pytest.mark.asyncio
async def test_player_decide_action(
    player_agent_instance: PlayerAgent, # Use the agent instance fixture
    round_1_ended_game_state: GameState # Use the game state from conftest
):
    """
    测试 PlayerAgent 的行动决策功能 (player_decide_action),
    使用从 conftest.py 加载并模拟到第一回合结束的游戏状态。
    """
    print("\n--- Running test_player_decide_action ---")
    agent = player_agent_instance
    game_state = round_1_ended_game_state
    scenario = game_state.scenario

    # The llm_model_client fixture in conftest handles skipping if client is None
    if not agent.model_client:
         pytest.skip("LLM model client not available for PlayerAgent.")

    # Get the character info for the player agent from the loaded scenario
    player_char_info = scenario.characters.get(PLAYER_CHAR_ID)
    assert player_char_info is not None, f"Character info not found for ID {PLAYER_CHAR_ID} in loaded scenario"

    # --- Setup Agent Memory based on round_1_ended_game_state ---
    agent.message_memory.history_messages.clear() # Clear any previous state
    unread_message_id = None
    if hasattr(game_state, '_test_chat_ids') and game_state._test_chat_ids:
        all_msg_ids = game_state._test_chat_ids
        # Simulate: Mark all but the last message as read
        for i, msg_id in enumerate(all_msg_ids):
            if i < len(all_msg_ids) - 1:
                agent.message_memory.history_messages[msg_id] = MessageStatus(message_id=msg_id, read_status=True, read_timestamp=datetime.now())
                print(f"  Marking message {msg_id} as READ for agent memory.")
            else:
                agent.message_memory.history_messages[msg_id] = MessageStatus(message_id=msg_id, read_status=False) # Last message is UNREAD
                unread_message_id = msg_id
                print(f"  Marking message {msg_id} as UNREAD for agent memory.")
    else:
        print("Warning: No message IDs found in game_state._test_chat_ids to set up memory.")


    # Check initial unread count (should be 1 based on setup above)
    initial_unread_count = agent.get_unread_messages_count()
    print(f"Initial unread messages for agent: {initial_unread_count}")
    assert initial_unread_count == 1, "Agent should have 1 unread message based on setup"

    print(f"Using game state at round {game_state.round_number}.")

    try:
        # The method internally gets unread messages based on agent's memory
        action: PlayerAction = await agent.player_decide_action(
            game_state=game_state,
            charaInfo=player_char_info
        )
        print("\n--- Generated Player Action (Test) ---")
        # Use model_dump_json for better readability of Pydantic object
        print(action.model_dump_json(indent=2))
        print("-------------------------------------")

        # Basic assertions
        assert isinstance(action, PlayerAction), "结果应该是一个 PlayerAction 对象"
        assert action.character_id == PLAYER_CHAR_ID, f"行动的角色 ID ({action.character_id}) 应该匹配 Agent 的 ID ({PLAYER_CHAR_ID})"
        assert isinstance(action.action_type, ActionType), "行动类型应该是 ActionType 枚举"
        assert isinstance(action.content, str) and len(action.content) > 0, "行动内容应该是一个非空字符串"
        # assert action.interal_thoughts is not None, "应该生成内部思考" # Check if thoughts are expected

        # Verify that the unread message was marked as read after the action
        final_unread_count = agent.get_unread_messages_count()
        print(f"Final unread messages for agent: {final_unread_count}")
        assert final_unread_count == 0, "Agent 决定行动后应该没有未读消息"
        if unread_message_id:
             assert agent.message_memory.history_messages[unread_message_id].read_status is True, f"消息 {unread_message_id} 应该被标记为已读"

    except Exception as e:
        print(f"Error during player action generation test: {e}")
        print(traceback.format_exc()) # Print traceback for debugging
        pytest.fail(f"Player action generation test failed: {e}")

# Add more tests, e.g., test_get_unread_messages, test_update_context, test_mark_message_as_read
# These tests might need simpler game states or specific memory setups.
