# src/engine/round_phases/action_declaration_phase.py
import asyncio
import uuid
from datetime import datetime
from typing import List, Optional, Tuple, Union

from src.engine.round_phases.base_phase import BaseRoundPhase, PhaseContext
from src.models.action_models import PlayerAction, ActionType, ActionOption
from src.models.message_models import Message, MessageType, MessageVisibility
from src.engine.agent_manager import PlayerAgent, CompanionAgent, BaseAgent # Import BaseAgent for type hint
from src.models.game_state_models import GameState
from src.models.scenario_models import ScenarioCharacterInfo

class ActionDeclarationPhase(BaseRoundPhase):
    """
    回合阶段：行动宣告阶段。
    负责收集所有玩家和陪玩角色的行动意图，并广播宣告消息。
    """
    def __init__(self, context: PhaseContext):
        super().__init__(context)

    async def _get_player_agent_action(
        self,
        agent: PlayerAgent,
        character_id: str,
        game_state: GameState,
        character_info: ScenarioCharacterInfo
    ) -> Optional[PlayerAction]:
        """获取单个 PlayerAgent 的行动。"""
        self.logger.debug(f"玩家代理 {agent.agent_id} 正在生成行动选项...")
        try:
            options = await agent.generate_action_options(game_state, character_info)
        except Exception as gen_err:
            self.logger.error(f"玩家代理 {character_id} 生成选项时出错: {gen_err}")
            options = [] # 出错则无选项

        chosen_option: Optional[ActionOption] = None
        input_handler = self.context.input_handler

        if input_handler and options:
            self.logger.info(f"使用 Input Handler ({type(input_handler).__name__}) 获取角色 {character_id} 的选择...")
            try:
                chosen_option = await input_handler.get_player_choice(
                    options=options,
                    character_name=character_info.name,
                    character_id=character_id
                )
            except Exception as input_err:
                self.logger.error(f"从 Input Handler 获取角色 {character_id} 选择时出错: {input_err}")
                chosen_option = options[0] # 备选：选第一个
                self.logger.warning(f"Input Handler 出错，自动选择第一个选项: {chosen_option}")
        elif options:
            self.logger.warning(f"未配置 Input Handler 或选项为空，将自动为角色 {character_id} 选择第一个选项。")
            chosen_option = options[0]
            print(f"警告：未配置 Input Handler 或选项为空，自动为角色 {character_id} 选择第一个选项。")

        if chosen_option:
            self.logger.info(f"角色 {character_id} 选择了行动: [{chosen_option.action_type.name}] {chosen_option.content}")
            return PlayerAction(
                character_id=character_id,
                action_type=chosen_option.action_type,
                content=chosen_option.content,
                target=chosen_option.target,
                internal_thoughts="行动由玩家选择。",
                timestamp=datetime.now().isoformat()
            )
        else:
            self.logger.error(f"玩家代理 {character_id} 未能生成有效选项或接收选择。创建默认等待行动。")
            return PlayerAction(
                character_id=character_id,
                action_type=ActionType.WAIT,
                content="...",
                target="environment",
                internal_thoughts="未能选择行动。",
                timestamp=datetime.now().isoformat()
            )

    async def _get_companion_agent_action(
        self,
        agent: CompanionAgent,
        character_id: str,
        game_state: GameState,
        character_info: ScenarioCharacterInfo
    ) -> Optional[PlayerAction]:
        """获取单个 CompanionAgent 的行动。"""
        self.logger.debug(f"陪玩代理 {agent.agent_id} 正在决定行动...")
        try:
            player_action = await agent.player_decide_action(game_state, character_info)
            if player_action:
                 self.logger.info(f"陪玩代理 {character_id} 决定了行动: [{player_action.action_type.name}] {player_action.content[:50]}...")
            return player_action
        except Exception as decide_err:
            self.logger.error(f"陪玩代理 {character_id} 决定行动时出错: {decide_err}")
            # 出错时创建默认等待行动
            return PlayerAction(
                character_id=character_id,
                action_type=ActionType.WAIT,
                content="...",
                target="environment",
                internal_thoughts="决定行动时出错。",
                timestamp=datetime.now().isoformat()
            )

    async def execute(self) -> List[PlayerAction]:
        """
        执行行动宣告阶段逻辑（并行）。

        Returns:
            List[PlayerAction]: 本回合所有宣告的玩家/陪玩行动列表。
        """
        self.logger.info("--- 开始行动宣告阶段 (并行) ---")
        tasks = []
        game_state = self.get_current_state()
        all_agent_ids = self.agent_manager.get_all_agent_ids() # 获取一次接收者列表

        # 1. 创建所有代理的行动决定任务
        for character_id, agent in self.agent_manager.player_agents.items():
            self.logger.debug(f"为角色 {character_id} ({type(agent).__name__}) 创建行动任务...")
            character_info = self.scenario_manager.get_character_info(character_id)
            if not character_info:
                self.logger.warning(f"无法获取角色 {character_id} 的信息，跳过其行动任务创建。")
                continue

            if isinstance(agent, PlayerAgent):
                task = asyncio.create_task(
                    self._get_player_agent_action(agent, character_id, game_state, character_info),
                    name=f"PlayerActionTask_{character_id}"
                )
                tasks.append(task)
            elif isinstance(agent, CompanionAgent):
                task = asyncio.create_task(
                    self._get_companion_agent_action(agent, character_id, game_state, character_info),
                    name=f"CompanionActionTask_{character_id}"
                )
                tasks.append(task)
            else:
                self.logger.warning(f"未知的 Agent 类型: {type(agent).__name__} for character {character_id}")

        # 2. 并发执行所有任务并收集结果
        self.logger.info(f"并发执行 {len(tasks)} 个行动决定任务...")
        results: List[Union[PlayerAction, Exception, None]] = await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.info("所有行动决定任务已完成。")

        # 3. 处理结果并收集有效行动
        player_actions: List[PlayerAction] = []
        for i, result in enumerate(results):
            task_name = tasks[i].get_name() # 获取任务名称以识别角色
            character_id_from_task = task_name.split('_')[-1] # 从任务名提取 character_id

            if isinstance(result, Exception):
                self.logger.error(f"角色 {character_id_from_task} 的行动任务失败: {result}")
                # 可以选择创建一个默认的 WAIT 行动
                default_action = PlayerAction(
                    character_id=character_id_from_task,
                    action_type=ActionType.WAIT,
                    content="...",
                    target="environment",
                    internal_thoughts=f"行动任务执行出错: {result}",
                    timestamp=datetime.now().isoformat()
                )
                player_actions.append(default_action)
            elif isinstance(result, PlayerAction):
                player_actions.append(result)
            elif result is None:
                 self.logger.warning(f"角色 {character_id_from_task} 的行动任务返回 None。")
                 # 可以选择创建一个默认的 WAIT 行动
                 default_action = PlayerAction(
                    character_id=character_id_from_task,
                    action_type=ActionType.WAIT,
                    content="...",
                    target="environment",
                    internal_thoughts="行动任务返回 None。",
                    timestamp=datetime.now().isoformat()
                 )
                 player_actions.append(default_action)
            else:
                self.logger.error(f"角色 {character_id_from_task} 的行动任务返回未知类型: {type(result)}")


        # 4. 统一广播所有收集到的行动宣告消息
        self.logger.info(f"收集到 {len(player_actions)} 个行动意图，开始广播...")
        for player_action in player_actions:
            character_state = game_state.characters.get(player_action.character_id)
            character_name = character_state.name if character_state else player_action.character_id
            message_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat() # 使用统一的时间戳或行动各自的时间戳？这里用新的
            message_type = MessageType.PLAYER if player_action.action_type == ActionType.TALK else MessageType.ACTION
            message_subtype = "dialogue" if player_action.action_type == ActionType.TALK else "action_description"

            action_message = Message(
                message_id=message_id,
                type=message_type,
                source=character_name,
                source_id=player_action.character_id,
                content=player_action.content,
                timestamp=timestamp,
                visibility=MessageVisibility.PUBLIC,
                recipients=all_agent_ids,
                round_id=self.current_round_id,
                message_subtype=message_subtype
            )
            try:
                self.message_dispatcher.broadcast_message(action_message)
                self.logger.debug(f"广播了角色 {player_action.character_id} 的行动宣告: {action_message.content[:50]}...")
            except Exception as broadcast_error:
                self.logger.error(f"广播角色 {player_action.character_id} 行动宣告消息时出错: {broadcast_error}")

        self.logger.info(f"--- 结束行动宣告阶段 (并行)，共处理 {len(player_actions)} 个行动意图 ---")
        return player_actions
