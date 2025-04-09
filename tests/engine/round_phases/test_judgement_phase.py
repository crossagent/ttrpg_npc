import pytest
from unittest.mock import MagicMock, patch, ANY

# Assuming necessary models and classes exist in these locations
from src.engine.round_phases.judgement_phase import JudgementPhase
from src.agents.referee_agent import RefereeAgent
from src.engine.game_state_manager import GameStateManager
from src.engine.chat_history_manager import ChatHistoryManager
from src.engine.scenario_manager import ScenarioManager
from src.io.input_handler import UserInputHandler # Assuming CliInputHandler implements this
from src.config.config_loader import load_config, load_llm_settings
# Corrected model imports
from src.models.game_state_models import GameState, CharacterInstance, ItemInstance, LocationStatus, TriggeredEventRecord # Removed Attribute, Skill, Item, Location; Added ItemInstance, LocationStatus
from src.models.scenario_models import Scenario, ScenarioCharacterInfo, LocationInfo, ItemInfo, ScenarioEvent, AttributeSet, SkillSet, StoryInfo # Replaced Template models, removed EventCondition, ConditionType; Added AttributeSet, SkillSet, StoryInfo
from src.models.action_models import PlayerAction, ActionType
from src.models.consequence_models import AddItemConsequence, UpdateCharacterAttributeConsequence, UpdateFlagConsequence, AppliedConsequenceRecord, ConsequenceType # Replaced SetFlagConsequence with UpdateFlagConsequence, added ConsequenceType
from src.models.message_models import Message, SenderRole # Replaced Role with SenderRole
from src.agents.companion_agent import CompanionAgent # Needed for patching simulate_dice_roll if we decide to

# --- Fixtures ---

@pytest.fixture
def mock_input_handler():
    """Mocks the user input handler."""
    handler = MagicMock(spec=UserInputHandler)
    return handler

@pytest.fixture(scope="module") # Scope to module to load scenario only once
def scenario_manager():
    """Provides a ScenarioManager loaded with the default scenario."""
    manager = ScenarioManager()
    try:
        # Load the actual default scenario file
        # Ensure 'scenarios/default.json' exists and is correctly formatted
        scenario = manager.load_scenario("default")

        return manager
    except FileNotFoundError:
        pytest.skip("scenarios/default.json not found, skipping integration tests dependent on it.")
    except Exception as e:
        pytest.skip(f"Failed to load or validate default scenario: {e}")

@pytest.fixture
def game_state_manager(scenario_manager):
    """Provides a GameStateManager initialized with the test scenario."""
    manager = GameStateManager(scenario_manager)
    scenario = scenario_manager.get_current_scenario() # Get the scenario object

    # Initialize the game state using the manager's method.
    # This should populate characters, locations etc. based on the scenario.
    manager.initialize_game_state(scenario.id)

    # Get the state *after* initialization
    current_state = manager.get_cur_state()

    # --- Modifications for Testing ---
    # Add specific skills needed for tests if not already present from scenario base skills

    # Add 'lockpicking' skill for the player if missing
    player_id = "player_char_id"
    if player_id in current_state.characters:
        player = current_state.characters[player_id]
        # Check if skills is a dict-like object and if 'lockpicking' is missing
        if isinstance(player.skills, SkillSet) and not hasattr(player.skills, 'lockpicking'):
             player.skills.lockpicking = 5 # Add the skill with level 5

    # Add 'persuasion' skill for the companion if missing (though it should be in the fixture scenario)
    companion_id = "companion_char_id"
    if companion_id in current_state.characters:
        companion = current_state.characters[companion_id]
        if isinstance(companion.skills, SkillSet) and not hasattr(companion.skills, 'persuasion'):
            companion.skills.persuasion = 3 # Add skill with level 3

    # Add initial inventory item (box) for the player if missing
    # Assuming initialize_new_game doesn't handle initial inventory from a potential scenario field
    if player_id in current_state.characters:
        player = current_state.characters[player_id]
        if not any(item.item_id == "box_item" for item in player.items):
             box_item_info = scenario.items.get("box_item")
             if box_item_info:
                 player.items.append(ItemInstance(item_id="box_item", name=box_item_info.name, quantity=1))


    # Ensure the manager has the potentially modified state
    manager.set_current_state(current_state)
    return manager

@pytest.fixture
def chat_history_manager():
    """Provides a ChatHistoryManager."""
    return ChatHistoryManager()

@pytest.fixture
def referee_agent(scenario_manager):
    """Provides a RefereeAgent instance (requires LLM config)."""
    # Assumes llm_settings.yaml is configured correctly for tests
    # In a real CI/CD, API keys might be handled via environment variables
    try:
        llm_config = load_llm_settings('config/llm_settings.yaml')
        # Find a suitable model configuration, e.g., the default one
        model_config = llm_config['models']['default']
        api_key = model_config.get('api_key') # Or get from env var
        model_name = model_config.get('model')

        if not api_key or not model_name:
             pytest.skip("LLM API key or model name not configured, skipping integration test.")

        # Simplified config for AutoGen agent initialization
        config_list = [{'model': model_name, 'api_key': api_key}]

        agent = RefereeAgent(
            name="TestReferee",
            scenario_manager=scenario_manager,
            llm_config={"config_list": config_list}
        )
        return agent
    except FileNotFoundError:
         pytest.skip("config/llm_settings.yaml not found, skipping integration test.")
    except Exception as e:
         pytest.skip(f"Failed to initialize RefereeAgent: {e}, skipping integration test.")


@pytest.fixture
def judgement_phase(game_state_manager, chat_history_manager, referee_agent, mock_input_handler, scenario_manager):
    """Provides a JudgementPhase instance with dependencies."""
    # Need to ensure all dependencies required by JudgementPhase are provided
    # This might include AgentManager or MessageDispatcher if JudgementPhase uses them directly
    # For now, assuming direct dependencies are covered
    return JudgementPhase(
        game_state_manager=game_state_manager,
        chat_history_manager=chat_history_manager,
        referee_agent=referee_agent,
        input_handler=mock_input_handler,
        scenario_manager=scenario_manager,
        # agent_manager=MagicMock(), # Mock if needed
        # message_dispatcher=MagicMock(), # Mock if needed
    )

# --- Test Cases ---

def test_judgement_player_action_needs_check_and_succeeds(judgement_phase, game_state_manager, mock_input_handler, referee_agent):
    """
    Tests the scenario where a player action requires a check, the player rolls successfully (mocked),
    and the consequences are applied.
    """
    # 1. Arrange: Set up initial GameState and declare the action
    initial_state = game_state_manager.get_current_state()
    initial_state.current_round_number = 1 # Set current round

    # Ensure player exists and has the box
    player_id = "player_char_id"
    assert player_id in initial_state.characters
    assert any(item.id == "box_item" for item in initial_state.characters[player_id].inventory)

    # Declare the action for the current round
    player_action = PlayerAction(
        actor_id=player_id,
        type=ActionType.INTERACT_ITEM, # More specific type
        description="I attempt to pick the lock on the sturdy box.",
        target_item_id="box_item", # Target the item
        round_number=1
    )
    initial_state.current_round_actions.append(player_action)
    game_state_manager.set_current_state(initial_state) # Ensure state manager has the updated list

    # Mock the player's successful dice roll input
    mock_input_handler.get_dice_roll_input.return_value = 18 # Assume 18 is a success

    # Mock RefereeAgent's assess_check_necessity to force a check
    # We patch the specific instance used by the judgement_phase fixture
    with patch.object(referee_agent, 'assess_check_necessity', return_value=(True, "lockpicking", 12)) as mock_assess:
        # Mock the actual consequence generation for predictability in this specific test
        # We expect AddItemConsequence for the key inside the box
        mock_consequence = AddItemConsequence(
            type="ADD_ITEM",
            character_id=player_id,
            item_id="key_item",
            item_name="Shiny Key", # Get name from scenario if possible
            item_description="A small, shiny key." # Get desc from scenario
        )
        with patch.object(referee_agent, 'determine_consequences', return_value=([mock_consequence], [])) as mock_determine:

            # 2. Act: Execute the JudgementPhase logic
            judgement_phase.process()

            # 3. Assert: Check results
            final_state = game_state_manager.get_current_state()

            # Check if assess_check_necessity was called correctly
            mock_assess.assert_called_once_with(player_action, ANY) # Check it was called with the action

            # Check if input handler was called for the dice roll
            mock_input_handler.get_dice_roll_input.assert_called_once_with(
                character_name="Test Player", # Assuming name is accessible
                action_description=player_action.description,
                check_attribute_skill="lockpicking",
                difficulty_class=12
            )

            # Check if determine_consequences was called with roll result
            # The context passed to determine_consequences will be complex, check key parts
            mock_determine.assert_called_once()
            call_args, _ = mock_determine.call_args
            context_arg = call_args[1] # Assuming context is the second argument
            assert "Dice Roll Result: 18" in context_arg
            assert "Check: lockpicking" in context_arg
            assert "Difficulty: 12" in context_arg


            # Check if the consequence was applied (item added to inventory)
            player_inventory = final_state.characters[player_id].inventory
            assert any(item.id == "key_item" for item in player_inventory), "Key item not found in inventory"

            # Check if the applied consequence was recorded
            assert len(final_state.current_round_applied_consequences) == 1
            recorded_consequence = final_state.current_round_applied_consequences[0]
            assert isinstance(recorded_consequence, AppliedConsequenceRecord)
            assert recorded_consequence.round_number == 1
            assert isinstance(recorded_consequence.applied_consequence, AddItemConsequence)
            assert recorded_consequence.applied_consequence.item_id == "key_item"
            assert recorded_consequence.applied_consequence.character_id == player_id

# Placeholder for other tests
# def test_judgement_companion_action_needs_check_and_fails(...):
#     pass

# def test_judgement_action_no_check_needed(...):
#     pass

def test_judgement_companion_action_needs_check_and_fails(judgement_phase, game_state_manager, mock_input_handler, referee_agent):
    """
    Tests the scenario where a companion action requires a check, the companion fails (simulated via consequence mock),
    and the failure consequences are applied.
    """
    # 1. Arrange: Set up initial GameState and declare the companion's action
    initial_state = game_state_manager.get_current_state()
    initial_state.current_round_number = 1

    companion_id = "companion_char_id"
    player_id = "player_char_id"
    assert companion_id in initial_state.characters
    assert player_id in initial_state.characters # Ensure player exists for relationship check
    initial_relationship = initial_state.characters[companion_id].attributes.get("relationship_player", 60) # Get initial relationship

    # Declare the companion's action for the current round
    companion_action = PlayerAction(
        actor_id=companion_id,
        type=ActionType.SOCIAL, # Social action
        description="Tries to persuade the player to give them the box.",
        target_character_id=player_id, # Target the player
        round_number=1
    )
    initial_state.current_round_actions.append(companion_action)
    game_state_manager.set_current_state(initial_state)

    # Mock RefereeAgent's assess_check_necessity to force a check
    with patch.object(referee_agent, 'assess_check_necessity', return_value=(True, "persuasion", 15)) as mock_assess:
        # Mock the consequence generation to return a *failure* consequence
        mock_failure_consequence = UpdateCharacterAttributeConsequence(
            type="UPDATE_CHARACTER_ATTRIBUTE",
            character_id=companion_id,
            attribute_name="relationship_player",
            new_value=initial_relationship - 10, # Decrease relationship
            reason="Failed persuasion attempt"
        )
        # We use ANY for the dice roll result in the context check
        def determine_consequences_side_effect(action, context, game_state):
            # Basic check that context contains dice roll info
            assert "Dice Roll Result:" in context
            assert "Check: persuasion" in context
            assert "Difficulty: 15" in context
            return ([mock_failure_consequence], []) # Return the failure consequence

        with patch.object(referee_agent, 'determine_consequences', side_effect=determine_consequences_side_effect) as mock_determine:
            # We also need to ensure simulate_dice_roll is called on the correct agent.
            # Since RefereeAgent likely gets the agent instance internally, we patch it globally for simplicity here.
            # This assumes RefereeAgent imports CompanionAgent or gets it via AgentManager.
            # A more robust approach might involve mocking AgentManager if RefereeAgent uses it.
            with patch('src.agents.referee_agent.RefereeAgent._get_agent_instance_for_roll', return_value=MagicMock(spec=CompanionAgent)) as mock_get_agent:
                 mock_companion_instance = mock_get_agent.return_value
                 mock_companion_instance.simulate_dice_roll.return_value = 5 # Simulate a low roll

                 # 2. Act: Execute the JudgementPhase logic
                 judgement_phase.process()


            # 3. Assert: Check results
            final_state = game_state_manager.get_current_state()

            # Check if assess_check_necessity was called correctly
            mock_assess.assert_called_once_with(companion_action, ANY)

            # Check if input handler was *NOT* called (it's a companion)
            mock_input_handler.get_dice_roll_input.assert_not_called()

            # Check if _get_agent_instance_for_roll was called (indirectly checks if it tried to get companion)
            mock_get_agent.assert_called_once_with(companion_id, ANY) # Check it tried to get the companion instance

            # Check if simulate_dice_roll was called on the mocked companion instance
            mock_companion_instance.simulate_dice_roll.assert_called_once_with(check_attribute_skill="persuasion", dc=15)


            # Check if determine_consequences was called
            mock_determine.assert_called_once()
            # Side effect already checked context contains roll info

            # Check if the failure consequence was applied (relationship decreased)
            final_relationship = final_state.characters[companion_id].attributes.get("relationship_player")
            assert final_relationship == initial_relationship - 10, f"Relationship should have decreased to {initial_relationship - 10}, but was {final_relationship}"

            # Check if the applied consequence was recorded
            assert len(final_state.current_round_applied_consequences) == 1
            recorded_consequence = final_state.current_round_applied_consequences[0]
            assert isinstance(recorded_consequence, AppliedConsequenceRecord)
            assert recorded_consequence.round_number == 1
            assert isinstance(recorded_consequence.applied_consequence, UpdateCharacterAttributeConsequence)
            assert recorded_consequence.applied_consequence.character_id == companion_id
            assert recorded_consequence.applied_consequence.attribute_name == "relationship_player"
            assert recorded_consequence.applied_consequence.new_value == initial_relationship - 10


def test_judgement_action_no_check_needed(judgement_phase, game_state_manager, mock_input_handler, referee_agent):
    """
    Tests the scenario where an action is simple enough that no check is required.
    """
    # 1. Arrange: Set up initial GameState and declare a simple action
    initial_state = game_state_manager.get_current_state()
    initial_state.current_round_number = 1

    player_id = "player_char_id"
    assert player_id in initial_state.characters
    scenario = scenario_manager.get_scenario() # Get scenario to access item info

    # Add a simple item to the location for the player to pick up
    apple_item_info = ItemInfo(id="apple_item", name="Red Apple", description="A juicy red apple.")
    # Add the ItemInfo to the scenario manager's internal scenario for consistency if needed, though not strictly necessary for this test setup
    if "apple_item" not in scenario.items:
        scenario.items["apple_item"] = apple_item_info
    # Add ItemInstance to the location status in game state
    if "start_loc" in initial_state.location_states:
        initial_state.location_states["start_loc"].available_items.append(
            ItemInstance(item_id="apple_item", name=apple_item_info.name, quantity=1)
        )
    game_state_manager.set_current_state(initial_state) # Update state

    # Declare the simple action
    simple_action = PlayerAction(
        actor_id=player_id,
        type=ActionType.INTERACT_ITEM,
        description="I pick up the red apple from the table.",
        target_item_id="apple_item", # Target the apple in the location
        round_number=1
    )
    initial_state.current_round_actions.append(simple_action)
    game_state_manager.set_current_state(initial_state)

    # Mock RefereeAgent's assess_check_necessity to return False (no check needed)
    with patch.object(referee_agent, 'assess_check_necessity', return_value=(False, None, None)) as mock_assess:
        # Mock the consequence generation to return the expected consequence
        mock_consequence = AddItemConsequence(
            type="ADD_ITEM",
            character_id=player_id,
            item_id="apple_item",
            item_name="Red Apple",
            item_description="A juicy red apple."
        )
        # Also need RemoveItem consequence for the location
        mock_remove_consequence = MagicMock() # Using MagicMock for simplicity if RemoveItemConsequence is complex
        mock_remove_consequence.type = "REMOVE_ITEM"
        # ... set other attributes if needed for validation ...

        # Determine consequences should be called without dice roll info
        def determine_consequences_side_effect(action, context, game_state):
            assert "Dice Roll Result:" not in context # Ensure no roll info
            assert "Check:" not in context
            assert "Difficulty:" not in context
            # Return picking up the apple and removing it from the location
            return ([mock_consequence, mock_remove_consequence], [])

        with patch.object(referee_agent, 'determine_consequences', side_effect=determine_consequences_side_effect) as mock_determine:
             # Patch the roll simulation part just to ensure it's NOT called
             with patch('src.agents.referee_agent.RefereeAgent._get_agent_instance_for_roll', return_value=MagicMock(spec=CompanionAgent)) as mock_get_agent:
                mock_companion_instance = mock_get_agent.return_value

                # 2. Act: Execute the JudgementPhase logic
                judgement_phase.process()

                # 3. Assert: Check results
                final_state = game_state_manager.get_current_state()

                # Check if assess_check_necessity was called correctly
                mock_assess.assert_called_once_with(simple_action, ANY)

                # Check if input handler was *NOT* called
                mock_input_handler.get_dice_roll_input.assert_not_called()

                # Check if simulate_dice_roll was *NOT* called
                mock_get_agent.assert_not_called()
                mock_companion_instance.simulate_dice_roll.assert_not_called()

                # Check if determine_consequences was called (side effect checks context)
                mock_determine.assert_called_once()

                # Check if the consequence was applied (item added to inventory)
                player_inventory = final_state.characters[player_id].inventory
                assert any(item.id == "apple_item" for item in player_inventory), "Apple item not found in inventory"

                # Check if the item was removed from the location
                location_items = final_state.locations["start_loc"].items
                assert not any(item.id == "apple_item" for item in location_items), "Apple item still found in location"


                # Check if the applied consequences were recorded (expecting 2: AddItem, RemoveItem)
                assert len(final_state.current_round_applied_consequences) == 2
                add_record = next((r for r in final_state.current_round_applied_consequences if isinstance(r.applied_consequence, AddItemConsequence)), None)
                remove_record = next((r for r in final_state.current_round_applied_consequences if r.applied_consequence.type == "REMOVE_ITEM"), None) # Check by type due to mock

                assert add_record is not None
                assert remove_record is not None

                assert add_record.round_number == 1
                assert add_record.applied_consequence.item_id == "apple_item"
                assert add_record.applied_consequence.character_id == player_id

                assert remove_record.round_number == 1
                # Add more specific checks for remove_record if needed


def test_judgement_action_triggers_event(judgement_phase, game_state_manager, mock_input_handler, referee_agent, scenario_manager):
    """
    Tests the scenario where an action's consequence sets a flag, which in turn triggers a scenario event.
    """
    # 1. Arrange: Set up initial GameState and declare the action
    initial_state = game_state_manager.get_current_state()
    initial_state.current_round_number = 1

    player_id = "player_char_id"
    assert player_id in initial_state.characters
    assert "secret_button_pressed" not in initial_state.flags # Ensure flag is not set initially

    # Declare the action that will lead to the flag being set
    trigger_action = PlayerAction(
        actor_id=player_id,
        type=ActionType.INTERACT_GENERAL,
        description="I press the strange button on the wall.",
        # target could be location or a specific object if modeled
        round_number=1
    )
    initial_state.current_round_actions.append(trigger_action)
    game_state_manager.set_current_state(initial_state)

    # Mock assess_check_necessity to return False (pressing a button likely doesn't need a check)
    with patch.object(referee_agent, 'assess_check_necessity', return_value=(False, None, None)) as mock_assess:
        # Mock determine_consequences to return the UpdateFlag consequence AND the triggered event
        mock_update_flag_consequence = UpdateFlagConsequence( # Changed variable name and class
            type=ConsequenceType.UPDATE_FLAG.value, # Use enum value for type safety
            flag_name="secret_button_pressed",
            flag_value=True
        )
        # Get the event definition from the scenario
        # Need to access events list and find by id
        triggered_event_def = next((e for e in scenario_manager.get_scenario().events if e.id == "secret_revealed_event"), None)
        assert triggered_event_def is not None

        # Mock determine_consequences to return both the consequence and the event
        with patch.object(referee_agent, 'determine_consequences', return_value=([mock_update_flag_consequence], [triggered_event_def])) as mock_determine: # Use updated variable
            # Patch roll simulation just to ensure it's not called
            with patch('src.agents.referee_agent.RefereeAgent._get_agent_instance_for_roll', return_value=MagicMock(spec=CompanionAgent)) as mock_get_agent:
                mock_companion_instance = mock_get_agent.return_value

                # 2. Act: Execute the JudgementPhase logic
                judgement_phase.process()

                # 3. Assert: Check results
                final_state = game_state_manager.get_current_state()

                # Check if assess_check_necessity was called
                mock_assess.assert_called_once_with(trigger_action, ANY)

                # Check if input handler/roll simulation were *NOT* called
                mock_input_handler.get_dice_roll_input.assert_not_called()
                mock_get_agent.assert_not_called()
                mock_companion_instance.simulate_dice_roll.assert_not_called()

                # Check if determine_consequences was called
                mock_determine.assert_called_once()

                # Check if the flag was set in the game state
                assert "secret_button_pressed" in final_state.flags
                assert final_state.flags["secret_button_pressed"] is True

                # Check if the UpdateFlag consequence was recorded
                assert any(
                    isinstance(r.applied_consequence, UpdateFlagConsequence) and r.applied_consequence.flag_name == "secret_button_pressed" # Changed class check
                    for r in final_state.current_round_applied_consequences
                ), "UpdateFlag consequence not recorded" # Changed message

                # Check if the event was recorded as triggered
                assert len(final_state.current_round_triggered_events) == 1
                recorded_event = final_state.current_round_triggered_events[0]
                assert isinstance(recorded_event, TriggeredEventRecord)
                assert recorded_event.round_number == 1
                assert recorded_event.event_id == "secret_revealed_event"
