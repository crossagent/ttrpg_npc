# src/agents/referee_agent.py

from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from typing import Optional, Dict, Any
import json
import re
from datetime import datetime

from src.models.scenario_models import Scenario
from src.models.game_state_models import GameState
from src.models.action_models import PlayerAction, ActionResult
from src.agents.base_agent import BaseAgent
from src.context.dm_context_builder import (
    build_action_resolve_system_prompt,
    build_action_resolve_user_prompt
)
from autogen_agentchat.agents import AssistantAgent # Import AssistantAgent

class RefereeAgent(BaseAgent):
    """
    裁判代理类，负责解析和判断玩家或NPC的行动，并生成结果。
    使用LLM进行判断。
    """

    def __init__(self, agent_id: str, agent_name: str, model_client=None):
        """
        初始化 RefereeAgent

        Args:
            agent_id (str): Agent唯一标识符
            agent_name (str): Agent名称
            model_client: 模型客户端
        """
        super().__init__(agent_id=agent_id, agent_name=agent_name, model_client=model_client)

    async def judge_action(self, action: PlayerAction, game_state: GameState, scenario: Optional[Scenario] = None) -> ActionResult:
        """
        使用LLM判断行动结果

        Args:
            action (PlayerAction): 需要判断的玩家行动
            game_state (GameState): 当前游戏状态
            scenario (Optional[Scenario]): 当前剧本 (可选)

        Returns:
            ActionResult: 行动结果
        """
        # 生成系统消息
        system_message_content: str = build_action_resolve_system_prompt(scenario)

        # 创建临时的AssistantAgent实例用于本次调用
        assistant = AssistantAgent(
            name=f"{self.agent_name}_action_resolver_helper", # 使用唯一的助手名称
            model_client=self.model_client,
            system_message=system_message_content
        )

        # 构建用户消息
        # 注意：build_action_resolve_user_prompt 需要 game_state 和 action
        user_message_content: str = build_action_resolve_user_prompt(game_state, action)
        user_message = TextMessage(
            content=user_message_content,
            source="system" # 源头标记为系统，表示这是内部调用
        )

        # 调用LLM获取响应
        response = await assistant.on_messages([user_message], CancellationToken())
        if not response or not response.chat_message or not response.chat_message.content:
            # 考虑添加日志记录
            print(f"警告: 未能从LLM获取有效的行动判断响应。Action: {action.content}")
            # 返回一个默认的失败结果或抛出异常，根据业务逻辑决定
            # 这里返回一个默认失败结果示例
            return ActionResult(
                character_id=action.character_id, # 使用 character_id 作为 player_id
                action=action,
                success=False,
                narrative="系统错误：无法判断行动结果。",
                state_changes={}
            )

        response_content: str = response.chat_message.content

        # 尝试解析JSON响应
        json_str: str = response_content
        # 查找被 ```json ... ``` 包裹的内容
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_content, re.IGNORECASE)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # 如果没有找到 ```json ```, 尝试直接解析整个响应内容
            # 但这可能包含非JSON文本，增加解析失败风险
            # 可以选择在这里记录警告或直接尝试解析
            print(f"警告: LLM响应未包含 ```json ``` 标记。尝试直接解析。响应: {response_content[:100]}...") # 打印部分响应以供调试

        try:
            response_data: Dict[str, Any] = json.loads(json_str)
        except json.JSONDecodeError as e:
            # 记录详细错误日志
            print(f"错误: JSON解析失败。错误信息: {e}。原始JSON字符串: '{json_str}'。完整LLM响应: {response_content}")
            # 返回默认失败结果
            return ActionResult(
                character_id=action.character_id,
                action=action,
                success=False,
                narrative=f"系统错误：无法解析行动结果格式。原始响应: {response_content}",
                state_changes={}
            )

        # 验证解析出的数据结构是否符合预期 (可选但推荐)
        # 例如，检查 'success', 'narrative', 'state_changes' 是否存在
        if not all(k in response_data for k in ['success', 'narrative', 'state_changes']):
             print(f"警告: LLM响应JSON缺少必要字段 ('success', 'narrative', 'state_changes')。响应数据: {response_data}")
             # 可以根据情况决定是补充默认值还是返回错误
             # 这里补充默认值
             response_data.setdefault('success', False)
             response_data.setdefault('narrative', '行动结果描述缺失。')
             response_data.setdefault('state_changes', {})


        # 创建并返回行动结果
        # 注意：ActionResult 需要 player_id，这里使用 action.character_id
        return ActionResult(
            character_id=action.character_id,
            action=action,
            success=bool(response_data.get("success", False)), # 确保是布尔值
            narrative=str(response_data.get("narrative", "行动结果未描述")), # 确保是字符串
            # dice_result 字段暂时不处理，保持为 None
            state_changes=response_data.get("state_changes", {})
        )

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
        CharacterStatus, LocationStatus, ItemStatus
    )
    from src.models.message_models import Message, MessageType
    from src.models.action_models import PlayerAction, ActionType, InternalThoughts # Import ActionType, InternalThoughts
    from src.config import config_loader
    # RefereeAgent class is defined in this file

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
    # Keep it simple, Referee mainly needs context from GameState and the Action itself
    mock_scenario_id = "test_scenario_referee_001"
    mock_char_id = "char_hero_referee"
    mock_loc_id = "loc_cave_referee"
    mock_stage_id = "stage_explore_referee"
    mock_section_id = "section_delve_referee"
    mock_chapter_id = "chapter_1_referee"

    mock_scenario = Scenario(
        scenario_id=mock_scenario_id,
        story_info=StoryInfo(
            id="test_story_referee",
            title="Referee Test Adventure",
            background="Testing action resolution in a dark cave.",
            narrative_style="Suspenseful fantasy",
            secrets={"main_secret": "There's treasure behind the waterfall."}
        ),
        characters={
            mock_char_id: ScenarioCharacterInfo(
                character_id=mock_char_id, name="Referee Hero", public_identity="Explorer",
                secret_goal="Map the cave system.", background="Brave adventurer.",
                special_ability="Night Vision", weakness="Claustrophobia"
            )
        },
        events=[],
        locations={
            mock_loc_id: LocationInfo(description="A dark, damp cave. Water drips steadily.")
        },
        items={},
        story_structure=StoryStructure(chapters=[StoryChapter(id=mock_chapter_id, name="C1", description="D", sections=[StorySection(id=mock_section_id, name="S1", description="D", stages=[StoryStage(id=mock_stage_id, name="Explore", description="D", objective="Find exit", locations=[mock_loc_id], characters=[mock_char_id], events=[])])])])
    )
    print("Mock Scenario created.")

    # --- 3. Create Mock GameState ---
    mock_game_id = f"test_game_referee_{uuid.uuid4()}"
    start_time = datetime.now()
    current_stage_obj = mock_scenario.story_structure.chapters[0].sections[0].stages[0]

    mock_game_state = GameState(
        game_id=mock_game_id,
        scenario_id=mock_scenario_id,
        round_number=5,
        max_rounds=10,
        started_at=start_time,
        last_updated=start_time,
        progress=ProgressStatus(
            current_chapter_id=mock_chapter_id, current_section_id=mock_section_id,
            current_stage_id=mock_stage_id, current_stage=current_stage_obj
        ),
        environment=EnvironmentStatus(
            current_location_id=mock_loc_id, time=start_time,
            weather="Underground", atmosphere="Eerie", lighting="Dark"
        ),
        scenario=mock_scenario,
        characters={
            mock_char_id: CharacterInstance(
                character_id=mock_char_id, instance_id=f"inst_{mock_char_id}",
                public_identity=mock_scenario.characters[mock_char_id].public_identity,
                name=mock_scenario.characters[mock_char_id].name, player_controlled=True,
                status=CharacterStatus(character_id=mock_char_id, location=mock_loc_id, health=100)
            )
        },
        character_states={
             mock_char_id: CharacterStatus(character_id=mock_char_id, location=mock_loc_id, health=100)
        },
        location_states={
            mock_loc_id: LocationStatus(
                location_id=mock_loc_id, present_characters=[mock_char_id],
                description_state="Loose rocks are scattered on the floor."
            )
        },
        item_states={},
        event_instances={},
        chat_history=[ # Minimal history for context
             Message(
                message_id=f"msg_{uuid.uuid4()}", type=MessageType.NARRATIVE, source="DM", target="all",
                content="You stand at the entrance of a dark cave. What do you do?",
                timestamp=(start_time - timedelta(minutes=1)).isoformat()
            )
        ]
    )
    print("Mock GameState created.")

    # --- 4. Create Mock PlayerAction ---
    mock_action = PlayerAction(
        character_id=mock_char_id,
        # Internal thoughts might not be strictly necessary for Referee, but good practice
        interal_thoughts=InternalThoughts(
            short_term_goals=["Find a light source", "Check for traps"],
            primary_emotion="Cautious",
            psychological_state="Alert",
            narrative_analysis="Entered a dark cave, need to be careful.",
            perceived_risks=["Falling rocks", "Hidden creatures"],
            perceived_opportunities=["Potential treasure", "Secret passage"]
        ),
        action_type=ActionType.ACTION, # A physical action
        content="I carefully examine the cave walls near the entrance for any loose rocks or hidden switches.",
        target="environment", # Targetting the surroundings
        timestamp=datetime.now().isoformat()
    )
    print("Mock PlayerAction created.")


    # --- 5. Initialize RefereeAgent ---
    referee_agent = RefereeAgent(
        agent_id="referee_agent_test_instance",
        agent_name="ActionJudge",
        model_client=model_client
    )
    print("RefereeAgent initialized.")

    # --- 6. Run Test ---
    async def run_referee_judge_test():
        print("\n--- Calling judge_action ---")
        if not model_client:
            print("Cannot run test: LLM model client not initialized.")
            return
        try:
            action_result = await referee_agent.judge_action(
                action=mock_action,
                game_state=mock_game_state,
                scenario=mock_scenario
            )
            print("\n--- Generated Action Result ---")
            # Use model_dump_json for better readability
            print(action_result.model_dump_json(indent=2))
            print("-----------------------------\n")
        except Exception as e:
            print(f"Error during action judging: {e}")
            import traceback
            traceback.print_exc()

    # Run the async test function
    try:
        if sys.platform == "win32":
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_referee_judge_test())
    except RuntimeError as e:
         print(f"Asyncio runtime error: {e}.")

    print(f"Finished running {__file__}.")
