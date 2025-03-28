from autogen_agentchat.messages import TextMessage, ChatMessage
from autogen_core import CancellationToken
from typing import List, Dict, Any, Optional, Union
import json
from datetime import datetime
from src.models.scenario_models import ScenarioCharacterInfo
from src.models.game_state_models import GameState, MessageReadMemory
from src.models.action_models import PlayerAction
from src.agents.base_agent import BaseAgent
from src.models.action_models import ActionType
from src.models.llm_validation import create_validator_for, LLMOutputError
from src.models.context_models import PlayerActionLLMOutput
from src.models.message_models import Message, MessageStatus
from src.context.player_context_builder import (
    build_decision_system_prompt,
    build_decision_user_prompt
)
import uuid

class PlayerAgent(BaseAgent):
    """
    玩家Agent类，负责生成玩家的观察、状态、思考和行动
    """
    
    def __init__(self, agent_id: str, agent_name: str, character_id:str, model_client=None):
        """
        初始化玩家Agent
        
        Args:
            agent_id: Agent唯一标识符
            agent_name: Agent名称
            character_id: 角色ID
            model_client: 模型客户端
        """
        # 初始化BaseAgent
        super().__init__(agent_id=agent_id, agent_name=agent_name, model_client=model_client)

        self.character_id = character_id
        
        # 初始化消息记忆
        self.message_memory: MessageReadMemory = MessageReadMemory(
            player_id=agent_id,
            history_messages={}
        )
    
    def update_context(self, message: Message) -> None:
        """
        更新Agent的上下文，处理新接收的消息
        
        Args:
            message: 接收到的消息对象
        """
        # 创建消息状态
        message_status = MessageStatus(
            message_id=message.message_id,
            read_status=False
        )
        
        # 更新消息记录
        self.message_memory.history_messages[message.message_id] = message_status
    
    def get_unread_messages(self, game_state: GameState) -> List[Message]:
        """
        获取所有未读消息
        
        Args:
            game_state: 游戏状态，包含消息历史
            
        Returns:
            List[Message]: 未读消息列表
        """
        # 直接从game_state获取消息历史
        all_messages = game_state.chat_history
        
        # 过滤出自己可见且未读的消息
        unread_messages = []
        for message in all_messages:
            if (message.message_id in self.message_memory.history_messages and 
                not self.message_memory.history_messages[message.message_id].read_status and
                self.filter_message(message)):  # 确保消息对自己可见
                unread_messages.append(message)
                
        # 标记为已读
        for message in unread_messages:
            self.mark_message_as_read(message.message_id)
            
        return unread_messages
    
    def mark_message_as_read(self, message_id: str) -> bool:
        """
        将消息标记为已读
        
        Args:
            message_id: 消息ID
            
        Returns:
            bool: 是否成功标记
        """
        if message_id not in self.message_memory.history_messages:
            return False
            
        # 更新消息状态
        message_status = self.message_memory.history_messages[message_id]
        message_status.read_status = True
        message_status.read_timestamp = datetime.now()
        
        return True
    
    def get_unread_messages_count(self) -> int:
        """
        获取未读消息数量
        
        Returns:
            int: 未读消息数量
        """
        # 统计未读消息
        unread_count = 0
        for message_status in self.message_memory.history_messages.values():
            if not message_status.read_status:
                unread_count += 1
                
        return unread_count

    
    async def player_decide_action(self, game_state: GameState, charaInfo: ScenarioCharacterInfo) -> PlayerAction:
        """
        玩家决策行动
        
        Args:
            game_state: 游戏状态，包含消息历史
            
        Returns:
            PlayerAction: 玩家行动
        """
        # 获取未读消息
        unread_messages = self.get_unread_messages(game_state)
        
        # 生成系统消息
        system_message = build_decision_system_prompt(charaInfo)
        
        # 直接创建新的AssistantAgent实例
        from autogen_agentchat.agents import AssistantAgent
        assistant = AssistantAgent(
            name=f"{self.agent_name}_action_helper",
            model_client=self.model_client,  # 假设model_client已作为属性存在
            system_message=system_message
        )
        
        # 构建用户消息
        user_message_content = build_decision_user_prompt(game_state, unread_messages, self.character_id)
        user_message = TextMessage(
            content=user_message_content,
            source="DM"
        )
        
        try:
            # 使用新创建的assistant的on_messages方法
            response = await assistant.on_messages([user_message], CancellationToken())
            if response and response.chat_message:
                response_content = response.chat_message.content
                
                # 使用验证器验证LLM输出
                try:
                    # 创建验证器
                    validator = create_validator_for(PlayerActionLLMOutput)
                    
                    # 验证响应
                    validated_data = validator.validate_response(response_content)
                    
                    
                    # 创建行动对象
                    return PlayerAction(
                        character_id=self.character_id,
                        interal_thoughts=validated_data.internal_thoughts,
                        action_type=validated_data.action_type,
                        content=validated_data.action,
                        target=validated_data.target,
                        timestamp=datetime.now().isoformat()
                    )
                except LLMOutputError as e:
                    # 处理验证错误，使用默认值
                    print(f"LLM输出验证错误: {e.message}")
                    # 尝试从原始响应中提取有用信息
                    import re
                    # 尝试提取action
                    action_match = re.search(r'"action"\s*:\s*"([^"]+)"', e.raw_output)
                    action_content = action_match.group(1) if action_match else "未能决定行动"
                    
                    # 创建默认行动对象
                    return PlayerAction(
                        character_id=self.character_id,
                        internal_thoughts="未能生成内心活动",
                        action_type=ActionType.TALK,
                        content=action_content,
                        target="all",
                        timestamp=datetime.now().isoformat()
                    )
                    
        except Exception as e:
            raise Exception(f"Assistant生成行动失败: {str(e)}")


if __name__ == "__main__":
    import asyncio
    import uuid
    from datetime import datetime, timedelta # Import timedelta
    import sys
    import os

    # Add project root to sys.path
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
        CharacterStatus, LocationStatus, ItemStatus, MessageReadStatus # Import MessageReadStatus
    )
    from src.models.message_models import Message, MessageType
    from src.config import config_loader
    # PlayerAgent class is defined in this file

    print(f"Running {__file__} directly for testing...")

    # --- 1. Load LLM Config ---
    model_client = None
    try:
        config_path = os.path.join(project_root, 'config', 'llm_settings.yaml')
        print(f"Loading LLM config from: {config_path}")
        if not os.path.exists(config_path):
             raise FileNotFoundError(f"Config file not found at {config_path}")
        llm_config = config_loader.load_llm_config(config_path)
        model_client_config = next(iter(llm_config.model_clients.values()), None)
        if not model_client_config:
            raise ValueError("No model client configured in llm_settings.yaml")
        model_client = config_loader.get_model_client(model_client_config)
        print(f"LLM Config loaded successfully. Using client: {model_client_config.client_type}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error loading LLM config: {e}")

    # --- 2. Create Mock Scenario ---
    mock_scenario_id = "test_scenario_player_001"
    mock_player_char_id = "char_hero_player" # Specific ID for player agent test
    mock_npc_char_id = "char_npc_player"
    mock_loc_id = "loc_forest_player"
    mock_stage_id = "stage_encounter_player"
    mock_section_id = "section_travel_player"
    mock_chapter_id = "chapter_1_player"

    mock_scenario = Scenario(
        scenario_id=mock_scenario_id,
        story_info=StoryInfo(
            id="test_story_player",
            title="Player Test Adventure",
            background="A test adventure focusing on player decision making in a forest encounter.",
            narrative_style="Action-oriented fantasy",
            secrets={"main_secret": "The NPC is lost."}
        ),
        characters={
            mock_player_char_id: ScenarioCharacterInfo(
                character_id=mock_player_char_id,
                name="Player Hero",
                public_identity="Adventurer",
                secret_goal="Find the hidden shrine.",
                background="Seeking ancient artifacts.",
                special_ability="Detect Magic",
                weakness="Fear of spiders"
            ),
            mock_npc_char_id: ScenarioCharacterInfo(
                character_id=mock_npc_char_id,
                name="Lost Merchant",
                public_identity="Merchant",
                secret_goal="Find the way back to town.",
                background="Got separated from his caravan.",
                special_ability=None,
                weakness="Poor sense of direction"
            )
        },
        events=[],
        locations={
            mock_loc_id: LocationInfo(
                description="A dense forest path. Sunlight filters through the canopy. Strange noises echo nearby."
            )
        },
        items={},
        story_structure=StoryStructure(
            chapters=[
                StoryChapter(
                    id=mock_chapter_id, name="Chapter 1", description="The Journey",
                    sections=[
                        StorySection(
                            id=mock_section_id, name="Section 1", description="Through the Woods",
                            stages=[
                                StoryStage(
                                    id=mock_stage_id, name="Forest Encounter", description="Meeting someone on the path",
                                    objective="Decide how to interact with the stranger.",
                                    locations=[mock_loc_id],
                                    characters=[mock_player_char_id, mock_npc_char_id], # Both characters are relevant
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
    mock_game_id = f"test_game_player_{uuid.uuid4()}"
    start_time = datetime.now()
    current_stage_obj = mock_scenario.story_structure.chapters[0].sections[0].stages[0]

    # Define messages, including one the player hasn't "read" yet
    msg1_id = f"msg_{uuid.uuid4()}"
    msg2_id = f"msg_{uuid.uuid4()}" # This will be the unread message

    mock_game_state = GameState(
        game_id=mock_game_id,
        scenario_id=mock_scenario_id,
        round_number=3,
        max_rounds=10,
        started_at=start_time,
        last_updated=start_time,
        progress=ProgressStatus(
            current_chapter_id=mock_chapter_id,
            current_section_id=mock_section_id,
            current_stage_id=mock_stage_id,
            current_stage=current_stage_obj
        ),
        environment=EnvironmentStatus(
            current_location_id=mock_loc_id,
            time=start_time,
            weather="Sunny",
            atmosphere="Tense",
            lighting="Bright"
        ),
        scenario=mock_scenario,
        characters={
            mock_player_char_id: CharacterInstance(
                character_id=mock_player_char_id, instance_id=f"inst_{mock_player_char_id}",
                public_identity=mock_scenario.characters[mock_player_char_id].public_identity,
                name=mock_scenario.characters[mock_player_char_id].name, player_controlled=True,
                status=CharacterStatus(character_id=mock_player_char_id, location=mock_loc_id, health=100)
            ),
            mock_npc_char_id: CharacterInstance(
                character_id=mock_npc_char_id, instance_id=f"inst_{mock_npc_char_id}",
                public_identity=mock_scenario.characters[mock_npc_char_id].public_identity,
                name=mock_scenario.characters[mock_npc_char_id].name, player_controlled=False, # NPC
                status=CharacterStatus(character_id=mock_npc_char_id, location=mock_loc_id, health=80)
            )
        },
        character_states={
             mock_player_char_id: CharacterStatus(character_id=mock_player_char_id, location=mock_loc_id, health=100),
             mock_npc_char_id: CharacterStatus(character_id=mock_npc_char_id, location=mock_loc_id, health=80)
        },
        location_states={
            mock_loc_id: LocationStatus(
                location_id=mock_loc_id,
                present_characters=[mock_player_char_id, mock_npc_char_id], # Both characters present
                description_state="Broken branches litter the path."
            )
        },
        item_states={},
        event_instances={},
        chat_history=[
            Message(
                message_id=msg1_id, type=MessageType.NARRATIVE, source="DM", target="all",
                content="You hear rustling in the bushes ahead. A figure emerges - a merchant looking disheveled and lost.",
                timestamp=(start_time - timedelta(minutes=2)).isoformat()
            ),
             Message( # This is the message the player needs to react to
                message_id=msg2_id, type=MessageType.DIALOGUE, source=mock_npc_char_id, target=mock_player_char_id,
                content="Oh, thank goodness! Another traveler! Can you help me? I seem to have lost my way.",
                timestamp=(start_time - timedelta(minutes=1)).isoformat()
            )
        ]
    )
    print("Mock GameState created.")

    # --- 4. Initialize PlayerAgent ---
    player_agent = PlayerAgent(
        agent_id="player_agent_test_instance",
        agent_name="HeroAgent",
        character_id=mock_player_char_id, # Associate with the player character
        model_client=model_client
    )
    print("PlayerAgent initialized.")

    # --- 5. Simulate Message Memory (Crucial Step) ---
    # Mark the first message as read, but the second (dialogue) as unread for this agent
    player_agent.message_memory.history_messages[msg1_id] = MessageStatus(message_id=msg1_id, read_status=True, read_timestamp=datetime.now())
    player_agent.message_memory.history_messages[msg2_id] = MessageStatus(message_id=msg2_id, read_status=False) # UNREAD
    print(f"Simulated message memory: Message '{msg1_id}' read, '{msg2_id}' unread.")

    # --- 6. Run Test ---
    async def run_player_action_test():
        print("\n--- Calling player_decide_action ---")
        if not model_client:
            print("Cannot run test: LLM model client not initialized.")
            return
        try:
            # Get the character info for the player agent
            player_char_info = mock_scenario.characters.get(mock_player_char_id)
            if not player_char_info:
                 print(f"Error: Character info not found for ID {mock_player_char_id}")
                 return

            # The method internally gets unread messages based on agent's memory
            action = await player_agent.player_decide_action(
                game_state=mock_game_state,
                charaInfo=player_char_info
            )
            print("\n--- Generated Player Action ---")
            # Use model_dump_json for better readability of Pydantic object
            print(action.model_dump_json(indent=2))
            print("-----------------------------\n")
        except Exception as e:
            print(f"Error during player action generation: {e}")
            import traceback
            traceback.print_exc()

    # Run the async test function
    try:
        if sys.platform == "win32":
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_player_action_test())
    except RuntimeError as e:
         print(f"Asyncio runtime error: {e}.")

    print(f"Finished running {__file__}.")
