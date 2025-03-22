from autogen_agentchat.messages import TextMessage, ChatMessage
from autogen_core import CancellationToken
from typing import List, Dict, Any, Optional, Union
import json
from datetime import datetime
from src.models.scenario_models import Scenario
from src.models.game_state_models import GameState
from src.models.action_models import PlayerAction
from src.agents.base_agent import BaseAgent
from src.models.action_models import ActionType
from src.models.llm_validation import create_validator_for, LLMOutputError
from src.models.context_models import PlayerActionLLMOutput
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
                
                # 使用验证器验证LLM输出
                try:
                    # 创建验证器
                    validator = create_validator_for(PlayerActionLLMOutput)
                    
                    # 验证响应
                    validated_data = validator.validate_response(response_content)
                    
                    
                    # 创建行动对象
                    return PlayerAction(
                        player_id=self.agent_id,
                        character_id=self.character_id,
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
                        player_id=self.agent_id,
                        character_id=self.character_id,
                        action_type=ActionType.DIALOGUE,
                        content=action_content,
                        target="all",
                        timestamp=datetime.now().isoformat()
                    )
                    
        except Exception as e:
            raise Exception(f"Assistant生成行动失败: {str(e)}")
