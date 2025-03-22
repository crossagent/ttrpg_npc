from autogen_agentchat.messages import TextMessage, ChatMessage
from autogen_core import CancellationToken
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from src.models.scenario_models import Scenario
from src.models.game_state_models import GameState
from src.models.action_models import PlayerAction
from src.agents.base_agent import BaseAgent
from src.models.action_models import ActionType
from src.context.player_context_builder import (
    build_decision_system_prompt,
    build_decision_user_prompt,
    build_reaction_system_prompt,
    build_reaction_user_prompt
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

    
    async def player_decide_action(self, game_state: GameState) -> PlayerAction:
        """
        玩家决策行动
        
        Args:
            game_state: 游戏状态，包含消息历史
            
        Returns:
            PlayerAction: 玩家行动
        """
        # 获取未读消息
        unread_messages = self.get_unread_messages(game_state)
        
        # 从game_state中获取角色信息
        character_profile = {"name": "未知角色", "personality": "无特定性格", "background": "无背景故事"}
        if self.character_id in game_state.characters:
            character_ref = game_state.characters[self.character_id]
            # 创建包含角色信息的字典
            character_profile = {
                "name": character_ref.name,
                "personality": "无特定性格",
                "background": "无背景故事"
            }
        
        # 生成系统消息
        system_message = build_decision_system_prompt(character_profile)
        
        # 直接创建新的AssistantAgent实例
        from autogen_agentchat.agents import AssistantAgent
        assistant = AssistantAgent(
            name=f"{self.agent_name}_action_helper",
            model_client=self.model_client,  # 假设model_client已作为属性存在
            system_message=system_message
        )
        
        # 构建用户消息
        user_message_content = build_decision_user_prompt(game_state, unread_messages)
        user_message = TextMessage(
            content=user_message_content,
            source="system"
        )
        
        try:
            # 使用新创建的assistant的on_messages方法
            response = await assistant.on_messages([user_message], CancellationToken())
            if response and response.chat_message:
                response_content = response.chat_message.content
                
                # 尝试解析JSON响应
                try:
                    # 查找JSON内容
                    import re
                    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_content)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        json_str = response_content
                    
                    # 修改JSON解析部分的代码
                    response_data = json.loads(json_str)
                    
                    # 从JSON中提取行动内容
                    action_content = response_data.get("action", "未能决定行动")
                    
                    # 获取action_type，如果返回中有明确指定则使用，否则使用默认值"对话"
                    action_type_str = response_data.get("action_type", "对话")

                    try:
                        action_type = ActionType(action_type_str)
                    except ValueError:
                        # 如果输入的值不在枚举中，使用默认值 DIALOGUE
                        action_type = ActionType.DIALOGUE

                    # 获取target，如果未指定则默认为"all"
                    target = response_data.get("target", "all")
                    
                    # 创建行动对象
                    return PlayerAction(
                        player_id=self.agent_id,
                        character_id=self.character_id,
                        action_type=action_type,
                        content=action_content,
                        target=target,
                        timestamp=datetime.now().isoformat()
                    )
                except json.JSONDecodeError as e:
                    raise ValueError(f"JSON解析错误: {str(e)}, 原始响应: {response_content}")
                    
        except Exception as e:
            raise Exception(f"Assistant生成行动失败: {str(e)}")
