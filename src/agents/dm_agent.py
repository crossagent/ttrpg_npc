from autogen_agentchat.messages import TextMessage, ChatMessage
from autogen_core import CancellationToken
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from src.models.scenario_models import Scenario
from src.models.game_state_models import GameState
from src.models.action_models import PlayerAction, ActionResult
from src.agents.base_agent import BaseAgent
from src.context.dm_context_builder import (
    build_narrative_system_prompt,
    build_narrative_user_prompt,
    build_action_resolve_system_prompt,
    build_action_resolve_user_prompt,
    get_current_scene
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
        super().__init__(agent_id=agent_id, agent_name=agent_name, model_client=model_client)

    
    async def dm_generate_narrative(self, game_state: GameState, scenario: Scenario) -> str:
        """
        DM生成叙述
        """
        # 获取未读消息和当前场景
        unread_messages = self.get_unread_messages(game_state)
        current_scene = get_current_scene(scenario, game_state.round_number)
        
        # 生成系统消息
        system_message = build_narrative_system_prompt(scenario)
        
        # 直接创建新的AssistantAgent实例，而不是调用create_assistant
        from autogen_agentchat.agents import AssistantAgent
        assistant = AssistantAgent(
            name=f"{self.agent_name}_narrative_helper",
            model_client=self.model_client,  # 假设model_client已作为属性存在
            system_message=system_message
        )
        
        # 构建用户消息
        user_message_content = build_narrative_user_prompt(game_state, unread_messages, current_scene)
        user_message = TextMessage(
            content=user_message_content,
            source="system"
        )
        
        # 使用新创建的assistant的on_messages方法
        response = await assistant.on_messages([user_message], CancellationToken())
        if not response or not response.chat_message:
            raise Exception("未能获取有效的叙述响应")
        
        return response.chat_message.content

    async def dm_resolve_action(self, action: PlayerAction, game_state: GameState, scenario: Optional[Scenario] = None) -> ActionResult:
        """
        DM解析玩家行动并生成结果
        
        Args:
            action: 玩家行动
            game_state: 游戏状态
            scenario: 游戏剧本（可选）
            
        Returns:
            ActionResult: 行动结果
        """
        # 生成系统消息
        system_message = build_action_resolve_system_prompt(scenario)
        
        # 创建新的AssistantAgent实例
        from autogen_agentchat.agents import AssistantAgent
        assistant = AssistantAgent(
            name=f"{self.agent_name}_action_resolver",
            model_client=self.model_client,
            system_message=system_message
        )
        
        # 构建用户消息
        user_message_content = build_action_resolve_user_prompt(game_state, action)
        user_message = TextMessage(
            content=user_message_content,
            source="system"
        )
        
        # 使用assistant的on_messages方法
        response = await assistant.on_messages([user_message], CancellationToken())
        if not response or not response.chat_message:
            raise Exception("未能获取有效的行动解析响应")
            
        response_content = response.chat_message.content
        
        # 尝试解析JSON响应
        # 查找JSON内容
        import re
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_content)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response_content
        
        # 解析JSON
        try:
            response_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise Exception(f"JSON解析错误: {str(e)}, 原始响应: {response_content}")
        
        # 创建行动结果
        return ActionResult(
            player_id=action.player_id,
            action=action,
            success=response_data.get("success", True),
            narrative=response_data.get("narrative", "行动结果未描述"),
            state_changes=response_data.get("state_changes", {})
        )
