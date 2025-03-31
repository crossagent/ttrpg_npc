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
import uuid # Import uuid for unique assistant names

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
        # Use a unique name for each call to avoid potential state issues if reused
        assistant_name = f"{self.agent_name}_action_resolver_helper_{uuid.uuid4()}"
        assistant = AssistantAgent(
            name=assistant_name,
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

        response_content: str = "" # Initialize response content
        try:
            # 调用LLM获取响应
            response = await assistant.on_messages([user_message], CancellationToken())
            if not response or not response.chat_message or not response.chat_message.content:
                # 考虑添加日志记录
                print(f"警告: RefereeAgent {self.agent_id} 未能从LLM获取有效的行动判断响应。Action: {action.content}")
                # 返回一个默认的失败结果或抛出异常，根据业务逻辑决定
                # 这里返回一个默认失败结果示例
                return ActionResult(
                    character_id=action.character_id, # 使用 character_id 作为 player_id
                    action=action,
                    success=False,
                    narrative="系统错误：无法判断行动结果 (LLM无响应)。",
                    state_changes={}
                )

            response_content = response.chat_message.content

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
                print(f"警告: RefereeAgent {self.agent_id} LLM响应未包含 ```json ``` 标记。尝试直接解析。响应: {response_content[:100]}...") # 打印部分响应以供调试

            try:
                response_data: Dict[str, Any] = json.loads(json_str)
            except json.JSONDecodeError as e:
                # 记录详细错误日志
                print(f"错误: RefereeAgent {self.agent_id} JSON解析失败。错误信息: {e}。原始JSON字符串: '{json_str}'。完整LLM响应: {response_content}")
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
                 print(f"警告: RefereeAgent {self.agent_id} LLM响应JSON缺少必要字段 ('success', 'narrative', 'state_changes')。响应数据: {response_data}")
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
        except Exception as e:
             # Log the full error and the response content if available
            import traceback
            print(f"Error during RefereeAgent {self.agent_id} action judging: {str(e)}")
            print(f"LLM Response Content (if any): {response_content[:200]}...")
            traceback.print_exc()
            # Raise a more specific exception or return a default action
            raise Exception(f"RefereeAgent {self.agent_id} 判断行动失败: {str(e)}")
