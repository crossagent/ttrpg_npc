from autogen_agentchat.messages import TextMessage, ChatMessage
from autogen_core import CancellationToken
from typing import List, Dict, Any, Optional, Union
import json
import re # +++ Import re +++
import uuid # +++ Import uuid +++
import traceback # +++ Import traceback +++
import logging # +++ Import logging +++
from datetime import datetime
# +++ Update imports +++
from src.models.scenario_models import ScenarioCharacterInfo
from src.models.game_state_models import GameState, MessageReadMemory, CharacterInstance
from src.models.action_models import PlayerAction, RelationshipImpactAssessment # Add RelationshipImpactAssessment
# Import the new union type and specific types needed
from src.models.consequence_models import AnyConsequence, ConsequenceType, ChangeRelationshipConsequence
from src.agents.base_agent import BaseAgent
from src.models.action_models import ActionType
from src.models.llm_validation import create_validator_for, LLMOutputError
from src.models.context_models import PlayerActionLLMOutput
from src.models.message_models import Message, MessageStatus
from src.context.player_context_builder import (
    build_decision_system_prompt,
    build_decision_user_prompt,
    # +++ Import new prompt builder for relationship assessment (assuming it's here) +++
    build_relationship_assessment_system_prompt,
    build_relationship_assessment_user_prompt
)
from src.engine.scenario_manager import ScenarioManager # Import ScenarioManager
from src.engine.chat_history_manager import ChatHistoryManager # Import ChatHistoryManager
from autogen_agentchat.agents import AssistantAgent # +++ Import AssistantAgent +++

class CompanionAgent(BaseAgent):
    """
    AI控制的陪玩角色Agent类，负责生成角色的观察、状态、思考和行动
    """
    
    def __init__(self, agent_id: str, agent_name: str, character_id:str, scenario_manager: ScenarioManager, chat_history_manager: ChatHistoryManager, model_client=None): # Add chat_history_manager
        """
        初始化陪玩Agent
        
        Args:
            agent_id: Agent唯一标识符
            agent_name: Agent名称
            character_id: 角色ID
            scenario_manager: ScenarioManager 实例
            chat_history_manager: ChatHistoryManager 实例 # Add doc
            model_client: 模型客户端
        """
        # 初始化BaseAgent
        super().__init__(agent_id=agent_id, agent_name=agent_name, chat_history_manager=chat_history_manager, model_client=model_client) # Pass chat_history_manager

        self.character_id = character_id
        self.scenario_manager = scenario_manager # Store scenario_manager
        self.chat_history_manager = chat_history_manager # Store chat_history_manager
        
        # 初始化消息记忆
        self.message_memory: MessageReadMemory = MessageReadMemory(
            player_id=agent_id,
            history_messages={}
        )
        # +++ Setup logger +++
        self.logger = logging.getLogger(f"CompanionAgent_{agent_name}")

    async def _assess_relationship_impact(
        self,
        interacting_actor_instance: CharacterInstance, # The one who performed the action (e.g., player)
        interaction_content: str, # The action/dialogue content
        game_state: GameState
    ) -> Optional[RelationshipImpactAssessment]:
        """
        (私有方法) 使用LLM评估特定互动对自身关系的影响。

        Args:
            interacting_actor_instance: 发起互动的角色实例。
            interaction_content: 具体的行动或对话内容。
            game_state: 当前游戏状态。

        Returns:
            Optional[RelationshipImpactAssessment]: LLM评估结果，如果评估失败则返回None。
        """
        # Get self's info
        self_char_instance = game_state.characters.get(self.character_id)
        self_char_info = self.scenario_manager.get_character_info(self.character_id)

        if not self_char_instance or not self_char_info:
            self.logger.error(f"无法获取角色 {self.character_id} 的实例或模板信息，无法评估关系影响。")
            return None

        self.logger.info(f"评估 {interacting_actor_instance.name} 对 {self_char_info.name} 的互动影响: '{interaction_content}'")

        # 构建 Prompt (需要从 player_context_builder.py 导入)
        # TODO: Implement build_relationship_assessment_system_prompt and build_relationship_assessment_user_prompt in the context builder
        system_message_content = build_relationship_assessment_system_prompt() # Placeholder
        user_message_content = build_relationship_assessment_user_prompt( # Placeholder
            interacting_actor_instance, # Pass the actor who interacted
            self_char_info,             # Pass self's static info
            self_char_instance,          # Pass self's current instance state
            interaction_content,        # Pass the interaction content
            game_state
        )

        # 创建临时 Agent
        assistant_name = f"{self.agent_name}_relationship_assessor_{uuid.uuid4().hex}"
        assistant = AssistantAgent(
            name=assistant_name,
            model_client=self.model_client,
            system_message=system_message_content
        )
        user_message = TextMessage(content=user_message_content, source="system")

        response_content: str = ""
        try:
            # 调用 LLM
            response = await assistant.on_messages([user_message], CancellationToken())
            if not response or not response.chat_message or not response.chat_message.content:
                self.logger.warning(f"未能从LLM获取有效的关系影响评估响应。")
                return None

            response_content = response.chat_message.content

            # 解析 JSON
            json_str = response_content
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_content, re.IGNORECASE)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                self.logger.warning(f"_assess_relationship_impact LLM响应未包含 ```json ``` 标记。尝试直接解析。响应: {response_content[:100]}...")

            try:
                response_data = json.loads(json_str)
                # 验证并创建 RelationshipImpactAssessment 对象
                assessment = RelationshipImpactAssessment(**response_data)
                self.logger.info(f"关系影响评估结果: 类型={assessment.interaction_type.value}, 强度={assessment.intensity.value}, 建议变化={assessment.suggested_change}, 原因={assessment.reason}")
                return assessment
            except json.JSONDecodeError as e:
                self.logger.error(f"_assess_relationship_impact JSON解析失败。错误: {e}。原始JSON: '{json_str}'.")
                return None
            except Exception as pydantic_err: # Catch Pydantic validation errors
                self.logger.error(f"_assess_relationship_impact Pydantic模型验证失败: {pydantic_err}. Data: {response_data}")
                return None

        except Exception as e:
            self.logger.exception(f"评估关系影响时发生意外错误: {str(e)}")
            return None

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
        # 从 ChatHistoryManager 获取所有消息历史
        all_messages = self.chat_history_manager.get_all_messages()
        
        # 过滤出自己可见且未读的消息
        unread_messages = []
        for message in all_messages:
            # Check if message exists in memory AND is marked as unread AND is visible
            if (message.message_id in self.message_memory.history_messages and
                not self.message_memory.history_messages[message.message_id].read_status and
                self.filter_message(message)): # filter_message is inherited from BaseAgent
                unread_messages.append(message)
                
        # 标记为已读 (Important: Mark as read *after* identifying all unread messages for this turn)
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
             # If the message isn't even in memory, we can't mark it.
             # This might happen if update_context wasn't called for this message.
             # Consider logging a warning here.
             print(f"Warning: Attempted to mark message '{message_id}' as read, but it was not found in memory for agent {self.agent_id}.")
             return False
            
        # 更新消息状态
        message_status = self.message_memory.history_messages[message_id]
        if not message_status.read_status: # Only update timestamp if it wasn't already read
            message_status.read_status = True
            message_status.read_timestamp = datetime.now()
            return True
        return False # Return False if it was already marked as read
    
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
        AI 陪玩角色决策行动，包括回顾互动并评估关系变化。

        Args:
            game_state: 游戏状态，包含消息历史
            charaInfo: 当前玩家角色的剧本信息 (注意：这里参数名可能应为 self_charaInfo)

        Returns:
            PlayerAction: AI 角色的行动，包含其内部产生的关系变化后果
        """
        # +++ 新增：关系评估逻辑 +++
        relationship_consequences: List[AnyConsequence] = [] # Update type hint
        player_id = game_state.player_character_id
        player_instance = game_state.characters.get(player_id) if player_id else None

        if player_instance and game_state.round_number > 0:
            try:
                # 获取上一回合的消息
                prev_round_messages = self.chat_history_manager.get_messages(start_round=game_state.round_number - 1)
                # 筛选出玩家与当前 NPC 的互动
                player_interactions = [
                    msg for msg in prev_round_messages
                    if msg.source_id == player_id and  # 使用 source_id
                       (self.character_id in msg.recipients or 'all' in msg.recipients) and # 使用 recipients
                       msg.content # Ensure there is content to assess
                ]

                if player_interactions:
                    self.logger.info(f"找到 {len(player_interactions)} 条上一回合来自玩家 {player_instance.name} 的互动，开始评估关系影响...")
                    for interaction_msg in player_interactions:
                        # 调用评估方法
                        assessment = await self._assess_relationship_impact(
                            interacting_actor_instance=player_instance,
                            interaction_content=interaction_msg.content,
                            game_state=game_state
                        )
                        # 如果评估成功且建议变化不为0，则创建后果
                        if assessment and assessment.suggested_change != 0:
                            # Create the specific ChangeRelationshipConsequence
                            relationship_consequence = ChangeRelationshipConsequence(
                                # type is set automatically by Literal
                                target_entity_id=self.character_id, # 目标是自己
                                secondary_entity_id=player_id,      # 另一方是玩家
                                value=assessment.suggested_change,
                                metadata={"reason": assessment.reason, "interaction_msg_id": interaction_msg.message_id} # 添加原因和来源消息ID
                            )
                            relationship_consequences.append(relationship_consequence)
                            self.logger.info(f"生成关系变化后果: 对 {player_instance.name} 关系变化 {assessment.suggested_change}")
                else:
                    self.logger.info(f"上一回合未找到来自玩家 {player_instance.name} 的直接互动。")

            except Exception as assess_err:
                self.logger.exception(f"回顾和评估关系影响时出错: {assess_err}")
        elif not player_instance:
             self.logger.warning("无法找到玩家实例，跳过关系评估。")
        # +++ 关系评估逻辑结束 +++


        # 获取未读消息 (This also marks them as read in memory)
        unread_messages = self.get_unread_messages(game_state)

        # 生成系统消息 (注意：参数 charaInfo 应该是 self 的信息)
        # TODO: 确认传入的 charaInfo 是否正确，或者应该从 scenario_manager 获取
        self_chara_info = self.scenario_manager.get_character_info(self.character_id)
        if not self_chara_info:
             self.logger.error(f"无法获取角色 {self.character_id} 的模板信息，无法生成行动！")
             # 返回一个表示错误的默认行动
             return PlayerAction(
                 character_id=self.character_id,
                 action_type=ActionType.WAIT,
                 content="内部错误：无法获取角色信息",
                 generated_consequences=relationship_consequences # 即使出错也附加已生成的关系后果
             )
        system_message = build_decision_system_prompt(self_chara_info) # 使用 self_chara_info

        # 直接创建新的AssistantAgent实例
        # from autogen_agentchat.agents import AssistantAgent # 已在文件顶部导入
        assistant = AssistantAgent(
            name=f"{self.agent_name}_action_decider_{uuid.uuid4().hex}", # 更明确的名称
            model_client=self.model_client,
            system_message=system_message
        )

        # 构建用户消息 (需要传递 scenario_manager)
        # TODO: 更新 build_decision_user_prompt 以便可能利用关系评估结果（如果需要影响当前行动决策）
        user_message_content = build_decision_user_prompt(game_state, self.scenario_manager, unread_messages, self.character_id)
        user_message = TextMessage(
            content=user_message_content,
            source="system" # 改为 system，因为这是内部驱动的决策
        )

        response_content = "" # Initialize response content
        try:
            # 使用新创建的assistant的on_messages方法
            response = await assistant.on_messages([user_message], CancellationToken())
            if response and response.chat_message and response.chat_message.content:
                response_content = response.chat_message.content

                # 使用验证器验证LLM输出
                try:
                    # 创建验证器
                    validator = create_validator_for(PlayerActionLLMOutput)

                    # 验证响应
                    validated_data: PlayerActionLLMOutput = validator.validate_response(response_content)

                    # 创建行动对象，并附加生成的关系后果
                    # +++ 注意：修复 validated_data.internal_thoughts 的拼写错误 +++
                    # +++ 注意：移除 timestamp，通常在更高层处理 +++
                    return PlayerAction(
                        character_id=self.character_id,
                        internal_thoughts=validated_data.internal_thoughts, # 使用 internal_thoughts
                        action_type=validated_data.action_type,
                        content=validated_data.action,
                        target=validated_data.target,
                        # timestamp=datetime.now().isoformat() # Timestamp 通常在更高层添加或不需要
                        generated_consequences=relationship_consequences # +++ 附加后果 +++
                    )
                except LLMOutputError as e:
                    # 处理验证错误，使用默认值
                    self.logger.error(f"LLM output validation error for CompanionAgent {self.agent_id}: {e.message}. Raw output: {e.raw_output[:200]}...") # Log raw output snippet
                    # 尝试从原始响应中提取有用信息
                    # import re # 已在文件顶部导入
                    # 尝试提取action
                    action_match = re.search(r'"action"\s*:\s*"([^"]+)"', e.raw_output, re.IGNORECASE)
                    action_content = action_match.group(1) if action_match else "未能决定行动 (解析错误)"

                    # 创建默认行动对象，附加关系后果
                    # +++ 注意：修复 internal_thoughts 拼写，设为 None +++
                    return PlayerAction(
                        character_id=self.character_id,
                        internal_thoughts=None, # 设置为 None 或默认 InternalThoughts
                        action_type=ActionType.WAIT, # Default to WAIT on error
                        content=action_content,
                        target=None, # Default target
                        # timestamp=datetime.now().isoformat()
                        generated_consequences=relationship_consequences # +++ 附加后果 +++
                    )
            else:
                 self.logger.warning(f"CompanionAgent {self.agent_id} received no valid response from LLM assistant.")
                 # Fallback action if LLM fails completely，附加关系后果
                 # +++ 注意：修复 internal_thoughts 拼写，设为 None +++
                 return PlayerAction(
                        character_id=self.character_id,
                        internal_thoughts=None,
                        action_type=ActionType.WAIT, # Default to WAIT
                        content="...", # Indicate waiting or observing
                        target=None,
                        # timestamp=datetime.now().isoformat()
                        generated_consequences=relationship_consequences # +++ 附加后果 +++
                    )


        except Exception as e:
            # Log the full error and the response content if available
            # import traceback # 已在文件顶部导入
            self.logger.exception(f"Error during CompanionAgent {self.agent_id} action decision: {str(e)}")
            self.logger.error(f"LLM Response Content (if any): {response_content[:200]}...")
            # traceback.print_exc() # logger.exception includes traceback
            # Raise a more specific exception or return a default action
            # 返回默认行动，附加关系后果
            # +++ 注意：修复 internal_thoughts 拼写，设为 None +++
            return PlayerAction(
                   character_id=self.character_id,
                   internal_thoughts=None,
                   action_type=ActionType.WAIT,
                   content="内部错误：决策时发生异常",
                   target=None,
                   generated_consequences=relationship_consequences # +++ 附加后果 +++
               )
