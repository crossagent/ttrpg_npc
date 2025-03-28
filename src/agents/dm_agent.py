from autogen_agentchat.messages import TextMessage, ChatMessage
from autogen_core import CancellationToken
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from src.models.scenario_models import Scenario
from src.models.game_state_models import GameState
from src.models.action_models import PlayerAction, ActionResult
from src.models.message_models import Message # Added import for Message
from src.agents.base_agent import BaseAgent
from src.context.dm_context_builder import (
    build_narrative_system_prompt,
    build_narrative_user_prompt,
    build_action_resolve_system_prompt,
    build_action_resolve_user_prompt
)

class DMAgent(BaseAgent):
    """
    DM Agent类，负责生成游戏叙述和处理玩家行动
    """
    
    def __init__(self, agent_id: str, agent_name: str, model_client=None):
        """
        初始化DMAgent
        
        Args:
            agent_id: Agent唯一标识符
            agent_name: Agent名称
            model_client: 模型客户端
        """
        # 初始化BaseAgent
        super().__init__(agent_id=agent_id, agent_name=agent_name, model_client=model_client) # Corrected indentation


    async def dm_generate_narrative(self, game_state: GameState, scenario: Scenario, historical_messages: Optional[List[Message]] = None) -> str: # Add historical_messages parameter
        """
        DM生成叙述

        Args:
            game_state: 当前游戏状态
            scenario: 当前剧本
            historical_messages: 自上次活跃回合以来的历史消息 (可选)
        """
        # 不再需要获取未读消息，使用传入的 historical_messages
        # unread_messages = self.get_unread_messages(game_state) 
        
        # 生成系统消息
        system_message = build_narrative_system_prompt(scenario)
        
        # 直接创建新的AssistantAgent实例，而不是调用create_assistant
        from autogen_agentchat.agents import AssistantAgent
        assistant = AssistantAgent(
            name=f"{self.agent_name}_narrative_helper",
            model_client=self.model_client,  # 假设model_client已作为属性存在
            system_message=system_message
        )
        
        # 构建用户消息 - 使用 historical_messages 替换 unread_messages
        # 注意：需要确保 build_narrative_user_prompt 接口已更新
        user_message_content = build_narrative_user_prompt(game_state, historical_messages or [], scenario) # Pass historical_messages, default to empty list if None
        user_message = TextMessage(
            content=user_message_content,
            source="system"
        )
        
        # 使用新创建的assistant的on_messages方法
        response = await assistant.on_messages([user_message], CancellationToken())
        if not response or not response.chat_message:
            raise Exception("未能获取有效的叙述响应")
        
        return response.chat_message.content

    # async def dm_resolve_action(self, character_id: str, message_id: str, game_state: GameState, scenario: Optional[Scenario] = None) -> ActionResult:
    #     """
    #     DM解析玩家行动并生成结果 (已由 RefereeAgent.judge_action 替代)
        
    #     Args:
    #         character_id: 角色ID
    #         message_id: 行动消息ID
    #         game_state: 游戏状态
    #         scenario: 游戏剧本（可选）
            
    #     Returns:
    #         ActionResult: 行动结果
    #     """
    #     # 从game_state.chat_history中查找对应的行动消息
    #     action_message = None
    #     for message in game_state.chat_history:
    #         if message.message_id == message_id:
    #             action_message = message
    #             break
        
    #     if not action_message:
    #         raise Exception(f"未找到ID为 {message_id} 的行动消息")
        
    #     # 从消息中提取行动信息
    #     from src.models.action_models import PlayerAction, ActionType
        
    #     # 创建PlayerAction对象
    #     action = PlayerAction(
    #         player_id=action_message.source,
    #         character_id=character_id,
    #         action_type=ActionType.ACTION if action_message.type == "action" else ActionType.TALK,
    #         content=action_message.content,
    #         target="all",  # 默认值，可能需要从消息中提取
    #         timestamp=action_message.timestamp
    #     )
        
    #     # 生成系统消息
    #     system_message = build_action_resolve_system_prompt(scenario)
        
    #     # 创建新的AssistantAgent实例
    #     from autogen_agentchat.agents import AssistantAgent
    #     assistant = AssistantAgent(
    #         name=f"{self.agent_name}_action_resolver",
    #         model_client=self.model_client,
    #         system_message=system_message
    #     )
        
    #     # 构建用户消息
    #     user_message_content = build_action_resolve_user_prompt(game_state, action)
    #     user_message = TextMessage(
    #         content=user_message_content,
    #         source="system"
    #     )
        
    #     # 使用assistant的on_messages方法
    #     response = await assistant.on_messages([user_message], CancellationToken())
    #     if not response or not response.chat_message:
    #         raise Exception("未能获取有效的行动解析响应")
            
    #     response_content = response.chat_message.content
        
    #     # 尝试解析JSON响应
    #     # 查找JSON内容
    #     import re
    #     json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_content)
    #     if json_match:
    #         json_str = json_match.group(1)
    #     else:
    #         json_str = response_content
        
    #     # 解析JSON
    #     try:
    #         response_data = json.loads(json_str)
    #     except json.JSONDecodeError as e:
    #         raise Exception(f"JSON解析错误: {str(e)}, 原始响应: {response_content}")
        
    #     # 创建行动结果
    #     return ActionResult(
    #         player_id=action.player_id,
    #         action=action,
    #         success=response_data.get("success", True),
    #         narrative=response_data.get("narrative", "行动结果未描述"),
    #         state_changes=response_data.get("state_changes", {})
    #     )

if __name__ == "__main__":
    import asyncio
    import uuid
    from datetime import datetime, timedelta # Import timedelta here
    import sys
    import os

    # Add project root to sys.path to allow absolute imports when run directly
    # Go up two levels from src/agents to reach the project root e:/ttrpg_npc
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"Added project root to sys.path: {project_root}")


    # Imports needed specifically for the __main__ block
    from src.models.scenario_models import (
        Scenario, StoryInfo, ScenarioCharacterInfo, LocationInfo, ItemInfo,
        StoryStructure, StoryChapter, StorySection, StoryStage
    )
    from src.models.game_state_models import (
        GameState, ProgressStatus, EnvironmentStatus, CharacterInstance,
        CharacterStatus, LocationStatus, ItemStatus
    )
    from src.models.message_models import Message, MessageType
    from src.config import config_loader

    print(f"Running {__file__} directly for testing...")

    # --- 1. Load LLM Config ---
    model_client = None
    try:
        # Construct the absolute path to the config file relative to the project root
        config_path = os.path.join(project_root, 'config', 'llm_settings.yaml')
        print(f"Loading LLM config from: {config_path}")
        if not os.path.exists(config_path):
             raise FileNotFoundError(f"Config file not found at {config_path}")
        llm_config = config_loader.load_llm_config(config_path)
        # Get the first configured model client for testing
        model_client_config = next(iter(llm_config.model_clients.values()), None)
        if not model_client_config:
            raise ValueError("No model client configured in llm_settings.yaml")
        model_client = config_loader.get_model_client(model_client_config)
        print(f"LLM Config loaded successfully. Using client: {model_client_config.client_type}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error loading LLM config: {e}")
        # Depending on the desired behavior, you might exit or continue without a client

    # --- 2. Create Mock Scenario ---
    mock_scenario_id = "test_scenario_dm_001"
    mock_char_id = "char_hero_dm"
    mock_loc_id = "loc_tavern_dm"
    mock_stage_id = "stage_intro_dm"
    mock_section_id = "section_start_dm"
    mock_chapter_id = "chapter_1_dm"

    mock_scenario = Scenario(
        scenario_id=mock_scenario_id,
        story_info=StoryInfo(
            id="test_story_dm",
            title="DM Test Adventure",
            background="A simple test adventure focusing on DM narrative generation in a tavern.",
            narrative_style="Descriptive fantasy",
            secrets={"main_secret": "The ale is magical."}
        ),
        characters={
            mock_char_id: ScenarioCharacterInfo(
                character_id=mock_char_id,
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
            mock_loc_id: LocationInfo(
                # name="The Drunken Dragon", # LocationInfo model doesn't have 'name'
                description="A dimly lit tavern. The air smells of stale ale and sawdust. A few patrons nurse their drinks."
            )
        },
        items={},
        story_structure=StoryStructure(
            chapters=[
                StoryChapter(
                    id=mock_chapter_id, name="Chapter 1", description="Arrival",
                    sections=[
                        StorySection(
                            id=mock_section_id, name="Section 1", description="Entering",
                            stages=[
                                StoryStage(
                                    id=mock_stage_id, name="Tavern Entrance", description="Stepping into the tavern",
                                    objective="Get a feel for the place.",
                                    locations=[mock_loc_id],
                                    characters=[mock_char_id],
                                    events=[]
                                )
                            ]
                        )
                    ]
                )
            ]
        )
    )
    print("Mock Scenario created.")

    # --- 3. Create Mock GameState ---
    mock_game_id = f"test_game_dm_{uuid.uuid4()}"
    start_time = datetime.now()
    current_stage_obj = mock_scenario.story_structure.chapters[0].sections[0].stages[0]

    mock_game_state = GameState(
        game_id=mock_game_id,
        scenario_id=mock_scenario_id,
        round_number=2, # Start at round 2 for context
        max_rounds=10,
        started_at=start_time,
        last_updated=start_time,
        progress=ProgressStatus(
            current_chapter_id=mock_chapter_id,
            current_section_id=mock_section_id,
            current_stage_id=mock_stage_id,
            current_stage=current_stage_obj # Cache current stage object
        ),
        environment=EnvironmentStatus(
            current_location_id=mock_loc_id,
            time=start_time,
            weather="Overcast",
            atmosphere="Quiet Murmurs",
            lighting="Dim"
        ),
        scenario=mock_scenario, # Embed scenario instance
        characters={
            mock_char_id: CharacterInstance(
                character_id=mock_char_id,
                instance_id=f"inst_{mock_char_id}",
                public_identity=mock_scenario.characters[mock_char_id].public_identity,
                name=mock_scenario.characters[mock_char_id].name,
                player_controlled=True,
                status=CharacterStatus(
                    character_id=mock_char_id,
                    location=mock_loc_id,
                    health=95 # Slightly damaged
                )
            )
        },
        character_states={ # Ensure this matches characters dictionary structure
             mock_char_id: CharacterStatus(
                    character_id=mock_char_id,
                    location=mock_loc_id,
                    health=95
                )
        },
        location_states={
            mock_loc_id: LocationStatus(
                location_id=mock_loc_id,
                present_characters=[mock_char_id], # Only our hero is present
                description_state="A puddle of spilled ale darkens the floor near the bar."
            )
        },
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
                source=mock_char_id, # Character ID as source
                target="environment", # Targetting the environment
                content="I look around the tavern, taking note of the patrons and the general atmosphere.",
                timestamp=(start_time - timedelta(minutes=1)).isoformat() # Most recent action
            )
        ]
    )
    print("Mock GameState created.")

    # --- 4. Initialize DMAgent ---
    # DMAgent class is defined in this file, no extra import needed inside __main__
    dm_agent = DMAgent(agent_id="dm_agent_test_instance", agent_name="NarrativeDM", model_client=model_client)
    print("DMAgent initialized.")

    # --- 5. Run Test ---
    async def run_dm_narrative_test():
        print("\n--- Calling dm_generate_narrative ---")
        if not model_client:
            print("Cannot run test: LLM model client not initialized.")
            return
        try:
            # Pass only the most recent relevant messages for narrative context
            # Example: last action message
            relevant_messages = [msg for msg in mock_game_state.chat_history if msg.type == MessageType.ACTION][-1:]
            if not relevant_messages:
                 print("No relevant action messages found in history for context.")
                 # Optionally, pass the last narrative message instead or an empty list
                 relevant_messages = [msg for msg in mock_game_state.chat_history if msg.type == MessageType.NARRATIVE][-1:]


            print(f"Providing {len(relevant_messages)} relevant message(s) as context.")

            narrative = await dm_agent.dm_generate_narrative(
                game_state=mock_game_state,
                scenario=mock_scenario,
                historical_messages=relevant_messages
            )
            print("\n--- Generated Narrative ---")
            print(narrative)
            print("---------------------------\n")
        except Exception as e:
            print(f"Error during DM narrative generation: {e}")
            import traceback
            traceback.print_exc() # Print full traceback for debugging

    # Run the async test function
    # Ensure the event loop is managed correctly, especially on Windows
    try:
        if sys.platform == "win32":
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_dm_narrative_test())
    except RuntimeError as e:
         print(f"Asyncio runtime error: {e}. This might occur in certain environments (e.g., Jupyter).")
         # Consider alternative loop handling if needed

    print(f"Finished running {__file__}.")
