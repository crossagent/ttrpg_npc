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
from src.models.action_models import PlayerAction, RelationshipImpactAssessment, InternalThoughts # Add RelationshipImpactAssessment, InternalThoughts
# Import the new union type and specific types needed
# +++ Import UpdateCharacterAttributeConsequence +++
from src.models.consequence_models import AnyConsequence, ConsequenceType, ChangeRelationshipConsequence, UpdateCharacterAttributeConsequence
from src.agents.base_agent import BaseAgent
from src.models.action_models import ActionType
from src.models.llm_validation import create_validator_for, LLMOutputError
from src.models.context_models import PlayerActionLLMOutput
from src.models.message_models import Message, MessageStatus
from src.context.player_context_builder import (
    build_decision_system_prompt,
    build_decision_user_prompt,
    build_relationship_assessment_system_prompt,
    build_relationship_assessment_user_prompt,
    # +++ Import new prompt builder for goal generation +++
    build_goal_generation_system_prompt,
    build_goal_generation_user_prompt
)
from src.engine.scenario_manager import ScenarioManager
from src.engine.chat_history_manager import ChatHistoryManager
from src.engine.game_state_manager import GameStateManager # +++ Import GameStateManager +++
from autogen_agentchat.agents import AssistantAgent

class CompanionAgent(BaseAgent):
    """
    AI控制的陪玩角色Agent类，负责生成角色的观察、状态、思考和行动
    """

    def __init__(self, agent_id: str, agent_name: str, character_id:str, scenario_manager: ScenarioManager, chat_history_manager: ChatHistoryManager, game_state_manager: GameStateManager, model_client=None): # +++ Add game_state_manager +++
        """
        初始化陪玩Agent

        Args:
            agent_id: Agent唯一标识符
            agent_name: Agent名称
            character_id: 角色ID
            scenario_manager: ScenarioManager 实例
            chat_history_manager: ChatHistoryManager 实例
            game_state_manager: GameStateManager 实例 # +++ Add doc +++
            model_client: 模型客户端
        """
        # 初始化BaseAgent
        super().__init__(agent_id=agent_id, agent_name=agent_name, chat_history_manager=chat_history_manager, model_client=model_client)

        self.character_id = character_id
        self.scenario_manager = scenario_manager
        self.chat_history_manager = chat_history_manager
        self.game_state_manager = game_state_manager # +++ Store game_state_manager +++

        # 初始化消息记忆
        self.message_memory: MessageReadMemory = MessageReadMemory(
            player_id=agent_id,
            history_messages={}
        )
        # +++ Setup logger +++
        self.logger = logging.getLogger(f"CompanionAgent_{agent_name}")

    async def _trigger_deep_thinking(
        self,
        game_state: GameState,
        self_char_instance: CharacterInstance,
        self_chara_info: ScenarioCharacterInfo
    ) -> None:
        """
        (私有方法) 当快速判断失败时，触发深度思考以生成下一回合的短期目标。
        """
        self.logger.info(f"{self.agent_name}: 触发深度思考/目标生成...")

        # 1. 构建 Prompt (需要从 player_context_builder.py 导入)
        # TODO: Implement build_goal_generation_system_prompt and build_goal_generation_user_prompt
        system_prompt = build_goal_generation_system_prompt(self_chara_info)
        user_prompt = build_goal_generation_user_prompt(
            game_state,
            self.scenario_manager,
            self.chat_history_manager, # Pass chat history manager
            self.character_id
        )

        # 2. 创建临时 Agent
        assistant_name = f"{self.agent_name}_goal_generator_{uuid.uuid4().hex}"
        assistant = AssistantAgent(
            name=assistant_name,
            model_client=self.model_client,
            system_message=system_prompt
        )
        user_message = TextMessage(content=user_prompt, source="system")
        response_content = ""

        try:
            # 3. 调用 LLM
            response = await assistant.on_messages([user_message], CancellationToken())
            if response and response.chat_message and response.chat_message.content:
                response_content = response.chat_message.content.strip()
                self.logger.debug(f"深度思考 LLM 原始响应: '{response_content[:200]}...'") # Log snippet

                # 4. 解析目标列表 (简单解析，假设LLM按要求返回换行分隔的列表)
                # TODO: Add more robust parsing, maybe JSON output from LLM?
                new_goals = [goal.strip() for goal in response_content.split('\n') if goal.strip()]

                if new_goals:
                    self.logger.info(f"{self.agent_name}: 深度思考生成了新的短期目标: {new_goals}")

                    # 5. 直接更新内心思考中的短期目标
                    if self_char_instance.internal_thoughts is None:
                        # 如果 internal_thoughts 不存在，创建一个新的实例
                        self_char_instance.internal_thoughts = InternalThoughts(
                            short_term_goals=new_goals,
                            long_term_goal=self_chara_info.secret_goal, # Copy long term goal
                            last_updated_round=game_state.round_number # Set initial round
                        )
                        self.logger.info(f"为 {self.agent_name} 创建了新的 InternalThoughts 并设置了目标。")
                    else:
                        # 如果已存在，只更新短期目标和时间戳
                        self_char_instance.internal_thoughts.short_term_goals = new_goals
                        self_char_instance.internal_thoughts.last_updated = datetime.now()
                        self_char_instance.internal_thoughts.last_updated_round = game_state.round_number
                        # Optionally ensure long_term_goal is set if missing
                        if not self_char_instance.internal_thoughts.long_term_goal:
                            self_char_instance.internal_thoughts.long_term_goal = self_chara_info.secret_goal
                        self.logger.info(f"更新了 {self.agent_name} 的 InternalThoughts 中的短期目标。")

                    # 移除旧的后果应用逻辑
                    # goal_consequence = UpdateCharacterAttributeConsequence(...)
                    # apply_desc = await self.game_state_manager.apply_single_consequence_immediately(...)
                    # ...

                else:
                    self.logger.warning(f"{self.agent_name}: 深度思考未能从LLM响应中解析出有效的新目标。响应: '{response_content[:200]}...'")

            else:
                self.logger.warning(f"{self.agent_name}: 深度思考未能从LLM获取有效响应。")

        except Exception as e:
            self.logger.exception(f"{self.agent_name}: 深度思考/目标生成过程中发生意外错误: {str(e)}")


    async def _check_plan_feasibility(
        self,
        game_state: GameState,
        self_char_instance: CharacterInstance
    ) -> bool:
        """
        (私有方法) 使用轻量级LLM调用，基于有限信息（目标+聊天记录）快速判断当前计划是否可行。

        Args:
            game_state: 当前游戏状态 (主要用于访问 ChatHistoryManager)。
            self_char_instance: 当前角色的实例。

        Returns:
            bool: True 如果LLM判断计划可行，False 否则。
        """
        # Read goals from internal_thoughts, handle None case
        current_goals = []
        if self_char_instance.internal_thoughts and self_char_instance.internal_thoughts.short_term_goals:
            current_goals = self_char_instance.internal_thoughts.short_term_goals
        
        if not current_goals:
            self.logger.info("快速判断：无短期目标，无需判断可行性。")
            return True # No goals means nothing is infeasible yet

        self.logger.info(f"快速判断：检查目标 {current_goals} 的可行性...")

        # 1. 准备有限上下文
        goals_text = "\n".join([f"- {goal}" for goal in current_goals])
        # 获取最近几条相关聊天记录 (最近1-2回合的)
        # TODO: Refine history retrieval logic if needed
        try:
            # 修复：根据正确的get_messages接口参数获取消息，指定回合范围
            recent_rounds = max(0, game_state.round_number - 1)
            recent_history = self.chat_history_manager.get_messages(
                start_round=recent_rounds,
                end_round=game_state.round_number
            )
            # 手动筛选与当前角色相关的消息
            character_related_messages = [
                msg for msg in recent_history 
                if (msg.source_id == self.character_id or 
                    self.character_id in msg.recipients or 
                    'all' in msg.recipients)
            ]
            # 限制消息数量，只取最新的5条
            relevant_messages = character_related_messages[-5:] if character_related_messages else []
            history_text = "\n".join([f"{msg.source}: {msg.content}" for msg in relevant_messages])
        except Exception as hist_err:
            self.logger.warning(f"快速判断：获取聊天记录时出错: {hist_err}。继续，但可能影响判断准确性。")
            history_text = "无法获取最近的对话记录。"

        # 2. 构建 Prompt (简化版，未来可移至 context_builder)
        system_prompt = "你是一个角色的快速直觉判断模块。根据角色当前的短期目标和最近的对话，快速判断继续执行这些目标在当前情境下是否看起来可行。不要进行深入分析，只做快速评估。请只回答 '可行' 或 '不可行'。"
        user_prompt = f"""
角色当前的短期目标:
{goals_text}

最近的相关对话:
{history_text}

基于以上信息，快速判断现在继续执行这些目标是否看起来可行？请只回答 '可行' 或 '不可行'。
"""

        # 3. 调用 LLM
        assistant_name = f"{self.agent_name}_feasibility_checker_{uuid.uuid4().hex}"
        assistant = AssistantAgent(
            name=assistant_name,
            model_client=self.model_client,
            system_message=system_prompt
        )
        user_message = TextMessage(content=user_prompt, source="system")
        response_content = ""

        try:
            response = await assistant.on_messages([user_message], CancellationToken())
            if response and response.chat_message and response.chat_message.content:
                response_content = response.chat_message.content.strip().lower()
                self.logger.info(f"快速判断 LLM 响应: '{response_content}'")
                # 简单判断
                if "可行" in response_content and "不可行" not in response_content:
                    return True
                elif "不可行" in response_content:
                    return False
                else:
                    self.logger.warning(f"快速判断：LLM响应无法明确判断可行性 ('{response_content}')，默认为不可行。")
                    return False # Default to infeasible if unclear
            else:
                self.logger.warning("快速判断：未能从LLM获取有效响应，默认为不可行。")
                return False # Default to infeasible on LLM error

        except Exception as e:
            self.logger.exception(f"快速判断：调用LLM时发生意外错误: {str(e)}，默认为不可行。")
            return False # Default to infeasible on exception

    async def _assess_relationship_impact(
        self,
        interacting_actor_instance: CharacterInstance,
        interaction_content: str,
        game_state: GameState
    ) -> None: # +++ Changed return type to None +++
        """
        (私有方法) 使用LLM评估特定互动对自身关系的影响，并 **立即应用** 产生的后果。

        Args:
            interacting_actor_instance: 发起互动的角色实例。
            interaction_content: 具体的行动或对话内容。
            game_state: 当前游戏状态。
        """
        # Get self's info
        self_char_instance = game_state.characters.get(self.character_id)
        self_char_info = self.scenario_manager.get_character_info(self.character_id)
        player_id = interacting_actor_instance.character_id # Get player ID for consequence

        if not self_char_instance or not self_char_info:
            self.logger.error(f"无法获取角色 {self.character_id} 的实例或模板信息，无法评估关系影响。")
            return # Return None implicitly

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
                return # Return None implicitly

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

                # +++ 如果评估成功且建议变化不为0，则立即应用后果 +++
                if assessment and assessment.suggested_change != 0:
                    relationship_consequence = ChangeRelationshipConsequence(
                        type=ConsequenceType.CHANGE_RELATIONSHIP.value,
                        target_entity_id=self.character_id,
                        secondary_entity_id=player_id,
                        value=float(assessment.suggested_change),
                        metadata={"reason": assessment.reason, "interaction_msg_id": "N/A"} # TODO: Pass interaction message ID if available
                    )
                    # 调用 GameStateManager 的新方法来立即应用
                    apply_desc = await self.game_state_manager.apply_single_consequence_immediately(
                        relationship_consequence, game_state
                    )
                    if apply_desc:
                        self.logger.info(f"立即应用关系变化后果成功: {apply_desc}")
                    else:
                        self.logger.warning(f"立即应用关系变化后果时未收到描述 (可能失败或无描述)。")
                # +++ 立即应用结束 +++

            except json.JSONDecodeError as e:
                self.logger.error(f"_assess_relationship_impact JSON解析失败。错误: {e}。原始JSON: '{json_str}'.")
            except Exception as pydantic_err: # Catch Pydantic validation errors
                self.logger.error(f"_assess_relationship_impact Pydantic模型验证失败: {pydantic_err}. Data: {response_data}")

        except Exception as e:
            self.logger.exception(f"评估关系影响时发生意外错误: {str(e)}")

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
            PlayerAction: AI 角色的行动
        """
        # +++ 移除 relationship_consequences 列表初始化 +++
        player_id = game_state.player_character_id
        player_instance = game_state.characters.get(player_id) if player_id else None

        # +++ 关系评估逻辑现在只调用评估和应用，不收集后果 +++
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
                        # 调用评估方法，该方法内部会尝试立即应用后果
                        await self._assess_relationship_impact(
                            interacting_actor_instance=player_instance,
                            interaction_content=interaction_msg.content,
                            game_state=game_state
                        )
                        # 不再需要在这里收集后果
                else:
                    self.logger.info(f"上一回合未找到来自玩家 {player_instance.name} 的直接互动。")

            except Exception as assess_err:
                self.logger.exception(f"回顾和评估关系影响时出错: {assess_err}")
        elif not player_instance:
             self.logger.warning("无法找到玩家实例，跳过关系评估。")
        # +++ 关系评估逻辑结束 +++

        # --- 两阶段思考逻辑开始 ---

        # 1. 获取自身实例和信息
        self_char_instance = game_state.characters.get(self.character_id)
        self_chara_info = self.scenario_manager.get_character_info(self.character_id) # charaInfo 参数未使用，直接获取

        if not self_char_instance or not self_chara_info:
            self.logger.error(f"无法获取角色 {self.character_id} 的实例或模板信息，无法生成行动！")
            return PlayerAction(
                character_id=self.character_id,
                action_type=ActionType.WAIT,
                content="内部错误：无法获取角色信息",
                generated_consequences=[] # 移除旧的后果列表
            )

        # 2. 快速判断阶段
        # 检查是否有短期目标 (从 internal_thoughts 读取)
        if not self_char_instance.internal_thoughts or not self_char_instance.internal_thoughts.short_term_goals:
            self.logger.info(f"{self.agent_name}: 无短期目标，选择等待并进行深度思考。")
            # +++ 触发深度思考 +++
            try:
                await self._trigger_deep_thinking(game_state, self_char_instance, self_chara_info)
            except Exception as dt_err:
                self.logger.exception(f"调用深度思考时出错 (无目标): {dt_err}")
            # --- 深度思考结束 ---
            return PlayerAction(
                character_id=self.character_id,
                action_type=ActionType.WAIT,
                content="思考下一步计划...", # 或者更符合角色的内心独白
                internal_thoughts=None, # 稍后由主LLM生成
                generated_consequences=[] # 移除旧的后果列表
            )

        # 如果有目标，进行快速可行性判断
        try:
            is_feasible = await self._check_plan_feasibility(game_state, self_char_instance)
        except Exception as feas_err:
            self.logger.exception(f"快速可行性判断出错: {feas_err}")
            is_feasible = False # Assume infeasible on error

        if not is_feasible:
            self.logger.info(f"{self.agent_name}: 快速判断认为目标不可行，选择等待并进行深度思考。")
            # +++ 触发深度思考 +++
            try:
                await self._trigger_deep_thinking(game_state, self_char_instance, self_chara_info)
            except Exception as dt_err:
                 self.logger.exception(f"调用深度思考时出错 (目标不可行): {dt_err}")
            # --- 深度思考结束 ---
            return PlayerAction(
                character_id=self.character_id,
                action_type=ActionType.WAIT,
                content="重新评估当前情况...", # 或者更符合角色的内心独白
                internal_thoughts=None, # 稍后由主LLM生成
                generated_consequences=[] # 移除旧的后果列表
            )

        # 3. 深度思考 / 行动选择阶段 (快速判断通过)
        self.logger.info(f"{self.agent_name}: 快速判断通过，进入深度思考/行动选择。")

        # 获取未读消息 (This also marks them as read in memory)
        unread_messages = self.get_unread_messages(game_state) # 移到这里，只有在需要深度思考时才获取

        # 生成系统消息
        system_message = build_decision_system_prompt(self_chara_info)

        # 创建主决策 AssistantAgent 实例
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

                    # +++ 更新内心思考状态 (简化) +++
                    if validated_data.internal_thoughts:
                        if self_char_instance.internal_thoughts is None:
                            # 如果不存在，直接使用 LLM 返回的，并补充 long_term_goal
                            self_char_instance.internal_thoughts = validated_data.internal_thoughts
                            self_char_instance.internal_thoughts.long_term_goal = self_chara_info.secret_goal # Ensure long term goal is set
                        else:
                            # 如果已存在，直接替换为 LLM 返回的最新思考，并保留 long_term_goal
                            original_long_term_goal = self_char_instance.internal_thoughts.long_term_goal
                            self_char_instance.internal_thoughts = validated_data.internal_thoughts
                            if not self_char_instance.internal_thoughts.long_term_goal: # Ensure long term goal persists
                                self_char_instance.internal_thoughts.long_term_goal = original_long_term_goal or self_chara_info.secret_goal

                        # 更新时间戳
                        self_char_instance.internal_thoughts.last_updated = datetime.now()
                        self_char_instance.internal_thoughts.last_updated_round = game_state.round_number
                        self.logger.info(f"更新了 {self.agent_name} 的 InternalThoughts。")
                    else:
                         self.logger.warning(f"LLM决策响应中未包含 InternalThoughts，无法更新内心状态。")

                    # 创建行动对象 (不包含 internal_thoughts)
                    return PlayerAction(
                        character_id=self.character_id,
                        # internal_thoughts=None, # Field removed
                        action_type=validated_data.action_type,
                        content=validated_data.action, # This is the main dialogue/action content
                        target=validated_data.target,
                        minor_action=validated_data.minor_action, # +++ 添加 minor_action +++
                        generated_consequences=[] # 移除旧的后果列表
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
                        internal_thoughts=None,
                        action_type=ActionType.WAIT,
                        content=action_content,
                        target=None,
                        minor_action=None, # +++ 添加 minor_action (None on error) +++
                        generated_consequences=[] # 移除旧的后果列表
                    )
            else:
                 self.logger.warning(f"CompanionAgent {self.agent_id} received no valid response from LLM assistant.")
                 # Fallback action if LLM fails completely，附加关系后果
                 # +++ 注意：修复 internal_thoughts 拼写，设为 None +++
                 return PlayerAction(
                        character_id=self.character_id,
                        internal_thoughts=None,
                        action_type=ActionType.WAIT,
                        content="...",
                        target=None,
                        minor_action=None, # +++ 添加 minor_action (None on error) +++
                        generated_consequences=[] # 移除旧的后果列表
                    )

        # --- 两阶段思考逻辑结束 ---

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
                   minor_action=None, # +++ 添加 minor_action (None on error) +++
                   generated_consequences=[] # 移除旧的后果列表
               )
