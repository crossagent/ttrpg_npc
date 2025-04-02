# src/engine/round_phases/action_declaration_phase.py
import uuid
from datetime import datetime
from typing import List, Optional

from src.engine.round_phases.base_phase import BaseRoundPhase, PhaseContext
from src.models.action_models import PlayerAction, ActionType
from src.models.message_models import Message, MessageType, MessageVisibility
from src.engine.agent_manager import PlayerAgent, CompanionAgent # Import specific agent types

class ActionDeclarationPhase(BaseRoundPhase):
    """
    回合阶段：行动宣告阶段。
    负责收集所有玩家和陪玩角色的行动意图，并广播宣告消息。
    """
    def __init__(self, context: PhaseContext):
        super().__init__(context)

    async def execute(self) -> List[PlayerAction]:
        """
        执行行动宣告阶段逻辑。

        Returns:
            List[PlayerAction]: 本回合所有宣告的玩家/陪玩行动列表。
        """
        self.logger.info("--- 开始行动宣告阶段 ---")
        player_actions: List[PlayerAction] = []
        game_state = self.get_current_state()
        all_agent_ids = self.agent_manager.get_all_agent_ids() # 获取一次接收者列表

        # 遍历所有 PlayerAgent 和 CompanionAgent
        # agent_manager.player_agents 包含这两种类型的实例
        for character_id, agent in self.agent_manager.player_agents.items():
            self.logger.info(f"处理角色 {character_id} 的行动宣告 (Agent 类型: {type(agent).__name__})")
            player_action: Optional[PlayerAction] = None
            character_info = self.scenario_manager.get_character_info(character_id)
            if not character_info:
                 self.logger.warning(f"无法获取角色 {character_id} 的信息，跳过其行动宣告。")
                 continue

            try:
                if isinstance(agent, PlayerAgent):
                    # --- 玩家代理: 生成选项并等待选择 ---
                    self.logger.debug(f"玩家代理 {agent.agent_id} 正在生成行动选项...")
                    options = await agent.generate_action_options(game_state, character_info)

                    # --- UI 交互占位符 ---
                    self.logger.warning(f"--- 需要玩家为 {character_id} ({agent.agent_name}) 选择行动 ---")
                    print(f"--- 需要玩家为 {character_id} ({agent.agent_name}) 选择行动 ---")
                    for idx, option in enumerate(options):
                        print(f"  {idx + 1}. [{option.action_type.name}] {option.content} (目标: {option.target})")
                        self.logger.warning(f"  {idx + 1}. [{option.action_type.name}] {option.content} (目标: {option.target})")

                    # !!! 关键: 这里需要替换为实际的 UI 交互逻辑来获取玩家选择 !!!
                    # 目前暂时自动选择第一个选项作为占位符
                    chosen_option_index = 0 # 假设玩家选了第一个
                    chosen_option = options[chosen_option_index] if options else None
                    self.logger.warning(f"!!! 占位符: 自动选择选项 {chosen_option_index + 1}: {chosen_option}")
                    print(f"!!! 占位符: 自动选择选项 {chosen_option_index + 1}: {chosen_option}")
                    # --- UI 交互占位符结束 ---

                    if chosen_option:
                        player_action = PlayerAction(
                            character_id=character_id,
                            action_type=chosen_option.action_type,
                            content=chosen_option.content,
                            target=chosen_option.target,
                            internal_thoughts="行动由玩家选择。", # PlayerAgent 通常没有内部思考过程
                            timestamp=datetime.now().isoformat()
                        )
                    else:
                         self.logger.error(f"玩家代理 {character_id} 未能生成有效选项或接收选择。")
                         # 创建默认的等待行动
                         player_action = PlayerAction(
                             character_id=character_id,
                             action_type=ActionType.WAIT,
                             content="...",
                             target="environment",
                             internal_thoughts="未能选择行动。",
                             timestamp=datetime.now().isoformat()
                         )

                elif isinstance(agent, CompanionAgent):
                    # --- 陪玩代理: 自主决定行动 ---
                    self.logger.debug(f"陪玩代理 {agent.agent_id} 正在决定行动...")
                    # 注意: CompanionAgent 可能仍然使用名为 player_decide_action 的方法
                    player_action = await agent.player_decide_action(game_state, character_info)
                else:
                    self.logger.warning(f"未知的 Agent 类型: {type(agent).__name__} for character {character_id}")
                    continue # 跳过此代理

                # --- 处理已决定的行动 (来自玩家选择或陪玩 AI) ---
                if player_action:
                    player_actions.append(player_action)
                    # 立即创建并广播行动宣告消息
                    character_state = game_state.characters.get(character_id)
                    character_name = character_state.name if character_state else character_id
                    message_id = str(uuid.uuid4())
                    timestamp = datetime.now().isoformat()
                    # 根据行动类型确定消息类型
                    message_type = MessageType.PLAYER if player_action.action_type == ActionType.TALK else MessageType.ACTION
                    message_subtype = "dialogue" if player_action.action_type == ActionType.TALK else "action_description"

                    action_message = Message(
                        message_id=message_id,
                        type=message_type,
                        source=character_name,
                        source_id=character_id,
                        content=player_action.content, # 广播行动内容
                        timestamp=timestamp,
                        visibility=MessageVisibility.PUBLIC,
                        recipients=all_agent_ids, # 广播给所有 Agent
                        round_id=self.current_round_id,
                        message_subtype=message_subtype
                    )
                    try:
                        self.message_dispatcher.broadcast_message(action_message)
                        self.logger.debug(f"广播了角色 {character_id} 的行动宣告: {action_message.content[:50]}...")
                    except Exception as broadcast_error:
                        self.logger.error(f"广播角色 {character_id} 行动宣告消息时出错: {broadcast_error}")

            except Exception as e:
                 self.logger.exception(f"处理角色 {character_id} ({type(agent).__name__}) 行动宣告时出错: {e}")
                 # 可以选择创建一个默认的 WAIT 行动，或者直接跳过

        self.logger.info(f"--- 结束行动宣告阶段，共收集 {len(player_actions)} 个行动意图 ---")
        return player_actions
