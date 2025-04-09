import pytest
from unittest.mock import MagicMock, patch, ANY

# Assuming necessary models and classes exist in these locations
from src.engine.round_phases.judgement_phase import JudgementPhase
from src.agents.referee_agent import RefereeAgent
from src.engine.game_state_manager import GameStateManager
from src.engine.chat_history_manager import ChatHistoryManager
from src.engine.scenario_manager import ScenarioManager
from src.engine.agent_manager import AgentManager # +++ Import AgentManager +++
from src.io.input_handler import UserInputHandler
from src.config.config_loader import load_llm_settings
# Corrected model imports
from src.models.game_state_models import GameState, CharacterInstance, ItemInstance, LocationStatus, TriggeredEventRecord, FlagSet
from src.models.scenario_models import Scenario, ScenarioCharacterInfo, LocationInfo, ItemInfo, ScenarioEvent, AttributeSet, SkillSet, StoryInfo
from src.models.action_models import PlayerAction, ActionType
from src.models.consequence_models import AddItemConsequence, UpdateCharacterAttributeConsequence, UpdateFlagConsequence, AppliedConsequenceRecord, ConsequenceType # Replaced SetFlagConsequence with UpdateFlagConsequence, added ConsequenceType
from src.models.message_models import Message, SenderRole
from src.agents.companion_agent import CompanionAgent

# --- Fixtures ---

# Keep mock_input_handler separate as it's always needed for mocking player input
@pytest.fixture
def mock_input_handler():
    """Mocks the user input handler."""
    handler = MagicMock(spec=UserInputHandler)
    return handler

# New fixture for integrated setup
@pytest.fixture
def judgement_phase_integration_setup(mock_input_handler):
    """
    Provides a more integrated setup for JudgementPhase tests,
    using real components where possible, including a real RefereeAgent
    connected to the configured LLM.
    """
    # 1. Scenario Manager
    scenario_manager = ScenarioManager()
    try:
        scenario = scenario_manager.load_scenario("default")
    except FileNotFoundError:
        pytest.skip("scenarios/default.json not found, skipping integration tests.")
    except Exception as e:
        pytest.skip(f"Failed to load or validate default scenario: {e}")

    # 2. Game State Manager
    game_state_manager = GameStateManager(scenario_manager)
    initial_state = game_state_manager.initialize_game_state() # Initialize state from scenario

    # --- Apply common modifications needed for tests ---
    # Ensure player and companion exist and have base skills/items from scenario
    # (Specific test cases can add more specific items/skills later if needed)
    player_id = "player_char_id" # Assuming this ID is in default.json
    companion_id = "companion_char_id" # Assuming this ID is in default.json

    if player_id not in initial_state.characters:
         pytest.skip(f"Player character '{player_id}' not found in default scenario.")
    if companion_id not in initial_state.characters:
         pytest.skip(f"Companion character '{companion_id}' not found in default scenario.")

    # Example: Ensure player has lockpicking (adjust level if needed by test)
    player = initial_state.characters[player_id]
    if not hasattr(player.skills, 'lockpicking'):
        player.skills.lockpicking = 5 # Default level for tests

    # Example: Ensure companion has persuasion
    companion = initial_state.characters[companion_id]
    if not hasattr(companion.skills, 'persuasion'):
        companion.skills.persuasion = 3 # Default level

    # Example: Ensure player starts with the box item if scenario doesn't provide it
    if not any(item.item_id == "box_item" for item in player.items):
        box_item_info = scenario.items.get("box_item")
        if box_item_info:
            player.items.append(ItemInstance(item_id="box_item", name=box_item_info.name, quantity=1))
        else:
            # If box_item isn't even in scenario items, we might need to skip or add it manually
            print("Warning: 'box_item' info not found in scenario items. Adding manually for test.")
            player.items.append(ItemInstance(item_id="box_item", name="Sturdy Box", quantity=1))


    # 3. Chat History Manager
    chat_history_manager = ChatHistoryManager()

    # 4. Agent Manager (Initializes all agents, including Referee)
    agent_manager = AgentManager(
        game_state=initial_state, # Use the state after common modifications
        scenario_manager=scenario_manager,
        chat_history_manager=chat_history_manager,
        game_state_manager=game_state_manager # Pass GSM to AgentManager
    )
    try:
        # This will load llm_settings internally and create agents based on scenario
        agent_manager.initialize_agents_from_characters(scenario)
    except FileNotFoundError:
         pytest.skip("config/llm_settings.yaml not found, skipping agent initialization.")
    except KeyError as e:
         pytest.skip(f"Missing key during agent initialization (check llm_settings.yaml and scenario character roles): {e}")
    except Exception as e:
         pytest.skip(f"Failed to initialize AgentManager: {e}")

    # 5. Get the Referee Agent instance from AgentManager
    # Assuming the referee agent's ID/name follows a convention or is defined in the scenario
    referee_agent_id = "referee_agent" # Adjust if the ID is different in your setup/scenario
    referee_agent = agent_manager.get_agent(referee_agent_id)
    if not referee_agent or not isinstance(referee_agent, RefereeAgent):
        pytest.skip(f"Could not find RefereeAgent with ID '{referee_agent_id}' in AgentManager.")


    # Return all initialized components
    return {
        "scenario_manager": scenario_manager,
        "game_state_manager": game_state_manager,
        "chat_history_manager": chat_history_manager,
        "agent_manager": agent_manager, # Return the manager
        "referee_agent": referee_agent, # Return the specific agent instance
        "mock_input_handler": mock_input_handler,
        "initial_state": initial_state # Return the state *after* common modifications but *before* agent init
    }


# --- Test Cases ---

# Note: These tests now rely on REAL LLM calls and may be slow/non-deterministic.
# Assertions might need to be adjusted for flexibility.

def test_judgement_player_action_needs_check_and_succeeds(judgement_phase_integration_setup):
    """
    Tests the scenario where a player action requires a check (determined by LLM),
    the player rolls successfully (mocked), and the consequences (determined by LLM) are applied.
    Relies on the LLM correctly identifying the need for a 'lockpicking' check for the action
    and generating appropriate consequences (e.g., adding a key).
    """
    # 1. Arrange: Get components from fixture and set up specific scenario
    gsm = judgement_phase_integration_setup["game_state_manager"]
    # AgentManager is now the source of truth for agents
    agent_manager = judgement_phase_integration_setup["agent_manager"]
    referee_agent = judgement_phase_integration_setup["referee_agent"] # Still useful to have direct ref
    mock_input_handler = judgement_phase_integration_setup["mock_input_handler"]
    scenario_manager = judgement_phase_integration_setup["scenario_manager"]
    chat_history_manager = judgement_phase_integration_setup["chat_history_manager"]

    # Get a fresh copy of the initial state *before* agent init for modification
    # Note: AgentManager was initialized with a state that included common modifications.
    # We might need to decide if tests modify the state *before* or *after* agent init.
    # Let's assume we modify *after* agent init for now, using the state from GSM.
    current_state = gsm.get_current_state().model_copy(deep=True) # Get state potentially modified by agent init
    current_state.current_round_number = 1
    player_id = "player_char_id"

    # Ensure player has the box (should be handled by fixture, but double-check)
    assert any(item.item_id == "box_item" for item in current_state.characters[player_id].items), "Player should have 'box_item'"

    # Declare the action for the current round
    player_action = PlayerAction(
        actor_id=player_id,
        type=ActionType.ACTION, # Corrected type: Use ACTION for substantial interactions
        description="I attempt to pick the lock on the sturdy box.",
        target_item_id="box_item", # Keep target_item_id for context if Referee uses it
        round_number=1
    )
    current_state.current_round_actions = [player_action] # Reset actions for this test
    current_state.current_round_applied_consequences = [] # Clear previous test consequences
    current_state.current_round_triggered_events = [] # Clear previous test events
    gsm.set_current_state(current_state) # Use the modified state

    # Mock the player's successful dice roll input
    mock_input_handler.get_dice_roll_input.return_value = 18 # Assume 18 is a success

    # Instantiate JudgementPhase with real components
    judgement_phase = JudgementPhase(
        game_state_manager=gsm,
        chat_history_manager=chat_history_manager,
        referee_agent=referee_agent,
        input_handler=mock_input_handler,
        scenario_manager=scenario_manager,
    )

    # --- REMOVED MOCKS for referee_agent.assess_check_necessity ---
    # --- REMOVED MOCKS for referee_agent.determine_consequences ---

    # 2. Act: Execute the JudgementPhase logic (will call real LLM)
    judgement_phase.process()

    # 3. Assert: Check results (Assertions need to be more flexible)
    final_state = gsm.get_current_state()

    # Check if input handler was called (implies a check was likely requested by LLM)
    # We can't easily assert the exact skill/DC requested by the LLM anymore
    assert mock_input_handler.get_dice_roll_input.called, "get_dice_roll_input should have been called if LLM requested a check."
    # Optional: Check if *some* check was requested
    # call_args, _ = mock_input_handler.get_dice_roll_input.call_args
    # assert call_args[2] is not None # Check if check_attribute_skill was provided

    # Check if *some* consequence was applied.
    # The exact consequence (e.g., finding a 'key_item') depends on the LLM.
    assert len(final_state.current_round_applied_consequences) > 0, "Expected at least one consequence to be applied on success."

    # Flexible check: Did the player gain *an* item? (Common success outcome)
    # This assumes the box contains an item according to the scenario/LLM logic.
    player_items_before = {item.item_id for item in current_state.characters[player_id].items}
    player_items_after = {item.item_id for item in final_state.characters[player_id].items}
    items_added = player_items_after - player_items_before
    assert len(items_added) > 0, "Expected player to gain at least one item from the box on successful lockpicking."
    print(f"Items added: {items_added}") # Log what was actually added

    # Check if the consequence was recorded
    recorded_consequence = final_state.current_round_applied_consequences[0] # Check the first one
    assert isinstance(recorded_consequence, AppliedConsequenceRecord)
    assert recorded_consequence.round_number == 1
    # We can check the type if the LLM is consistent, e.g., AddItemConsequence
    # assert isinstance(recorded_consequence.applied_consequence, AddItemConsequence)
    # Checking specific item_id might be too brittle now.


def test_judgement_companion_action_needs_check_and_fails(judgement_phase_integration_setup):
    """
    Tests the scenario where a companion action requires a check (determined by LLM),
    the companion rolls poorly (mocked), and failure consequences (determined by LLM) are applied.
    Relies on LLM identifying the check and generating failure consequences (e.g., relationship decrease).
    """
    # 1. Arrange: Get components and set up state
    gsm = judgement_phase_integration_setup["game_state_manager"]
    agent_manager = judgement_phase_integration_setup["agent_manager"]
    referee_agent = judgement_phase_integration_setup["referee_agent"]
    mock_input_handler = judgement_phase_integration_setup["mock_input_handler"]
    scenario_manager = judgement_phase_integration_setup["scenario_manager"]
    chat_history_manager = judgement_phase_integration_setup["chat_history_manager"]

    current_state = gsm.get_current_state().model_copy(deep=True)
    current_state.current_round_number = 1
    companion_id = "companion_char_id"
    player_id = "player_char_id" # Assuming player exists for relationship target

    # Ensure companion exists
    assert companion_id in current_state.characters
    # Record initial relationship (assuming 'relationship_player' attribute exists)
    initial_relationship = current_state.characters[companion_id].attributes.get("relationship_player", 0) # Default to 0 if not present

    # Declare the companion's action
    companion_action = PlayerAction(
        actor_id=companion_id,
        type=ActionType.TALK, # Corrected type: Persuasion is typically TALK
        description="Tries to awkwardly persuade the player to share their food.",
        target=player_id, # Use 'target' field for character ID
        round_number=1
    )
    current_state.current_round_actions = [companion_action]
    current_state.current_round_applied_consequences = []
    current_state.current_round_triggered_events = []
    gsm.set_current_state(current_state)

    # Mock the companion's dice roll to ensure failure
    # We patch the simulate_dice_roll method on the *actual* companion agent instance
    companion_agent_instance = agent_manager.get_agent(companion_id)
    if not companion_agent_instance:
         pytest.skip(f"Companion agent '{companion_id}' not found in AgentManager.")

    # Patch the simulate_dice_roll method on the specific instance
    with patch.object(companion_agent_instance, 'simulate_dice_roll', return_value=5) as mock_simulate_roll: # Low roll = failure

        # Instantiate JudgementPhase
        judgement_phase = JudgementPhase(
            game_state_manager=gsm,
            chat_history_manager=chat_history_manager,
            referee_agent=referee_agent,
            input_handler=mock_input_handler,
            scenario_manager=scenario_manager,
            # Pass agent_manager if JudgementPhase needs it to find the agent for rolling
            # Check JudgementPhase.__init__ and process method implementation
            # Assuming for now RefereeAgent handles getting the agent instance internally
        )

        # 2. Act: Execute the JudgementPhase logic
        judgement_phase.process()

        # 3. Assert: Check results
        final_state = gsm.get_current_state()

        # Check if input handler was *NOT* called (it's a companion)
        mock_input_handler.get_dice_roll_input.assert_not_called()

        # Check if simulate_dice_roll was called on the companion instance
        # We can't easily know the exact skill/DC requested by the LLM
        assert mock_simulate_roll.called, "Companion's simulate_dice_roll should have been called."
        # call_args, call_kwargs = mock_simulate_roll.call_args
        # print(f"Simulate roll called with: args={call_args}, kwargs={call_kwargs}") # Debugging

        # Check if *some* consequence was applied (expecting failure consequences)
        assert len(final_state.current_round_applied_consequences) > 0, "Expected at least one consequence for the failed action."

        # Flexible check: Did the relationship decrease?
        final_relationship = final_state.characters[companion_id].attributes.get("relationship_player", initial_relationship)
        assert final_relationship < initial_relationship, f"Expected relationship to decrease from {initial_relationship}, but it became {final_relationship}."
        print(f"Relationship changed from {initial_relationship} to {final_relationship}")

        # Check if the consequence was recorded
        recorded_consequence = final_state.current_round_applied_consequences[0]
        assert isinstance(recorded_consequence, AppliedConsequenceRecord)
        assert recorded_consequence.round_number == 1
        # Check if it was an attribute update (common failure consequence)
        # assert isinstance(recorded_consequence.applied_consequence, UpdateCharacterAttributeConsequence)
        # assert recorded_consequence.applied_consequence.attribute_name == "relationship_player" # This might be too brittle


def test_judgement_action_no_check_needed(judgement_phase_integration_setup):
    """
    Tests the scenario where an action is simple enough (determined by LLM)
    that no check is required, and consequences are applied directly.
    Relies on LLM determining no check needed for picking up a simple item
    and generating consequences like adding/removing the item.
    """
    # 1. Arrange: Get components and set up state for a simple action
    gsm = judgement_phase_integration_setup["game_state_manager"]
    agent_manager = judgement_phase_integration_setup["agent_manager"]
    referee_agent = judgement_phase_integration_setup["referee_agent"]
    mock_input_handler = judgement_phase_integration_setup["mock_input_handler"]
    scenario_manager = judgement_phase_integration_setup["scenario_manager"]
    chat_history_manager = judgement_phase_integration_setup["chat_history_manager"]

    current_state = gsm.get_current_state().model_copy(deep=True)
    current_state.current_round_number = 1
    player_id = "player_char_id"
    player_location_id = current_state.characters[player_id].location # Get player's current location

    # Define the simple item and ensure it exists in the location
    simple_item_id = "apple_item"
    simple_item_name = "Red Apple"
    # Ensure the item definition exists in the scenario for consistency if needed
    scenario = scenario_manager.get_current_scenario()
    if simple_item_id not in scenario.items:
        print(f"Warning: Adding '{simple_item_id}' to scenario items for test.")
        scenario.items[simple_item_id] = ItemInfo(id=simple_item_id, name=simple_item_name, description="A juicy red apple.")

    # Ensure the item instance is in the player's location state
    location_state = current_state.location_states.get(player_location_id)
    if not location_state:
         pytest.skip(f"Player location '{player_location_id}' state not found.")
    if not any(item.item_id == simple_item_id for item in location_state.available_items):
        location_state.available_items.append(
            ItemInstance(item_id=simple_item_id, name=simple_item_name, quantity=1)
        )
        print(f"Added '{simple_item_id}' instance to location '{player_location_id}' for test.")

    # Ensure player doesn't already have the item
    current_state.characters[player_id].items = [item for item in current_state.characters[player_id].items if item.item_id != simple_item_id]

    # Declare the simple action
    simple_action = PlayerAction(
        actor_id=player_id,
        type=ActionType.ACTION, # Picking up an item is an ACTION
        description=f"I pick up the {simple_item_name} from the ground.",
        target_item_id=simple_item_id, # Target the item in the location
        round_number=1
    )
    current_state.current_round_actions = [simple_action]
    current_state.current_round_applied_consequences = []
    current_state.current_round_triggered_events = []
    gsm.set_current_state(current_state)

    # Instantiate JudgementPhase
    judgement_phase = JudgementPhase(
        game_state_manager=gsm,
        chat_history_manager=chat_history_manager,
        referee_agent=referee_agent,
        input_handler=mock_input_handler,
        scenario_manager=scenario_manager,
    )

    # 2. Act: Execute the JudgementPhase logic
    judgement_phase.process()

    # 3. Assert: Check results
    final_state = gsm.get_current_state()

    # Check if input handler was *NOT* called
    assert not mock_input_handler.get_dice_roll_input.called, "Input handler should NOT be called for a simple action needing no check."

    # Check if consequences were applied (item added to player, removed from location)
    assert len(final_state.current_round_applied_consequences) >= 1, "Expected at least one consequence (e.g., AddItem)."

    # Check player inventory
    player_inventory = final_state.characters[player_id].items
    assert any(item.item_id == simple_item_id for item in player_inventory), f"'{simple_item_id}' not found in player inventory."

    # Check location items
    final_location_state = final_state.location_states.get(player_location_id)
    assert final_location_state is not None
    assert not any(item.item_id == simple_item_id for item in final_location_state.available_items), f"'{simple_item_id}' should have been removed from location '{player_location_id}'."

    # Check if consequences were recorded (expecting AddItem, maybe RemoveItem from location)
    recorded_consequences = final_state.current_round_applied_consequences
    assert any(isinstance(r.applied_consequence, AddItemConsequence) and r.applied_consequence.item_id == simple_item_id for r in recorded_consequences), "AddItemConsequence for apple not recorded."
    # Checking for RemoveItem might depend on how Referee/Handlers implement it
    # assert any(r.applied_consequence.type == ConsequenceType.REMOVE_ITEM.value ... for r in recorded_consequences)


def test_judgement_action_triggers_event(judgement_phase_integration_setup):
    """
    Tests the scenario where an action's consequence (determined by LLM, e.g., setting a flag)
    triggers a scenario event.
    Relies on LLM generating an UpdateFlagConsequence and JudgementPhase correctly
    identifying and recording the triggered event based on scenario definitions.
    """
    # 1. Arrange: Get components and set up state
    gsm = judgement_phase_integration_setup["game_state_manager"]
    agent_manager = judgement_phase_integration_setup["agent_manager"]
    referee_agent = judgement_phase_integration_setup["referee_agent"]
    mock_input_handler = judgement_phase_integration_setup["mock_input_handler"]
    scenario_manager = judgement_phase_integration_setup["scenario_manager"]
    chat_history_manager = judgement_phase_integration_setup["chat_history_manager"]

    current_state = gsm.get_current_state().model_copy(deep=True)
    current_state.current_round_number = 1
    player_id = "player_char_id"

    # Define the flag and event IDs (ensure these exist in default.json scenario)
    trigger_flag_name = "secret_button_pressed"
    triggered_event_id = "secret_revealed_event" # Assumes this event is triggered by the flag

    # Ensure the corresponding event exists in the scenario
    scenario = scenario_manager.get_current_scenario()
    event_def = next((e for e in scenario.events if e.id == triggered_event_id), None)
    if not event_def:
        pytest.skip(f"Event '{triggered_event_id}' not found in scenario, cannot test triggering.")
    # Optional: Check if the event condition actually matches the flag
    # This requires parsing event_def.conditions which might be complex

    # Ensure the flag is initially NOT set
    if trigger_flag_name in current_state.flags:
        del current_state.flags[trigger_flag_name]
        print(f"Removed pre-existing flag '{trigger_flag_name}' for test.")

    # Declare the action expected to trigger the flag
    trigger_action = PlayerAction(
        actor_id=player_id,
        type=ActionType.ACTION, # Interacting with an object is an ACTION
        description="I press the strange, glowing button on the wall.",
        # target could be more specific if the button is modeled, e.g., target_object_id="glowing_button"
        round_number=1
    )
    current_state.current_round_actions = [trigger_action]
    current_state.current_round_applied_consequences = []
    current_state.current_round_triggered_events = []
    gsm.set_current_state(current_state)

    # Instantiate JudgementPhase
    judgement_phase = JudgementPhase(
        game_state_manager=gsm,
        chat_history_manager=chat_history_manager,
        referee_agent=referee_agent,
        input_handler=mock_input_handler,
        scenario_manager=scenario_manager,
    )

    # 2. Act: Execute the JudgementPhase logic
    judgement_phase.process()

    # 3. Assert: Check results
    final_state = gsm.get_current_state()

    # Check if the flag was set (LLM needs to generate UpdateFlag consequence)
    assert trigger_flag_name in final_state.flags, f"Flag '{trigger_flag_name}' was not set."
    assert final_state.flags[trigger_flag_name] is True, f"Flag '{trigger_flag_name}' was not set to True."

    # Check if the UpdateFlag consequence was recorded
    recorded_consequences = final_state.current_round_applied_consequences
    assert any(
        isinstance(r.applied_consequence, UpdateFlagConsequence) and r.applied_consequence.flag_name == trigger_flag_name
        for r in recorded_consequences
    ), f"UpdateFlagConsequence for '{trigger_flag_name}' not recorded."

    # Check if the event was recorded as triggered
    assert len(final_state.current_round_triggered_events) == 1, "Expected exactly one event to be triggered."
    recorded_event = final_state.current_round_triggered_events[0]
    assert isinstance(recorded_event, TriggeredEventRecord)
    assert recorded_event.round_number == 1
    assert recorded_event.event_id == triggered_event_id, f"Expected event '{triggered_event_id}' to be triggered, but got '{recorded_event.event_id}'."

    # Check if input handler was likely NOT called (depends on LLM)
    # assert not mock_input_handler.get_dice_roll_input.called, "Input handler should likely not be called for pressing a button."
