from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
import asyncio
import logging

from src.models.game_state_models import GameState
from src.models.message_models import Message, MessageType, MessageVisibility
from src.models.action_models import PlayerAction, ActionResult, ItemQuery, DiceResult
from src.models.context_models import StateUpdateRequest
from src.engine.game_state_manager import GameStateManager
from src.communication.perspective_info_manager import PerspectiveInfoManager
from src.communication.message_dispatcher import MessageDispatcher
from src.engine.agent_manager import AgentManager
from src.engine.scenario_manager import ScenarioManager


class RoundManager:
    """
    回合管理器类，负责协调整个回合的执行流程，调度各个模块之间的交互。
    """
    
    def __init__(self, game_state_manager: GameStateManager = None, 
                 message_dispatcher: MessageDispatcher = None, 
                 perspective_info_manager: PerspectiveInfoManager = None, 
                 agent_manager: AgentManager = None, 
                 scenario_manager: ScenarioManager = None):
        """
        初始化回合管理器
        
        Args:
            game_state_manager: 游戏状态管理器
            message_dispatcher: 消息分发器
            perspective_info_manager: 个人视角信息管理器
            agent_manager: Agent系统
            scenario_manager: 剧本管理器
        """
        self.game_state_manager = game_state_manager
        self.message_dispatcher = message_dispatcher
        self.perspective_info_manager = perspective_info_manager
        self.agent_manager = agent_manager
        self.scenario_manager = scenario_manager
        
        # 回合状态相关变量
        self.current_round_id: int = 0
        self.round_start_time: datetime = None
        self.current_state: GameState = None
        self.dm_narrative: str = None
        self.player_actions: List[PlayerAction] = []
        self.action_results: List[ActionResult] = []
        
        # 日志配置
        self.logger = logging.getLogger("RoundManager")
    
    def start_round(self, round_id: int) -> None:
        """
        启动新回合，初始化状态
        
        Args:
            round_id: 回合ID
        """
        # 记录回合信息
        self.current_round_id = round_id
        self.round_start_time = datetime.now()
        
        # 初始化回合状态
        self.current_state = self.game_state_manager.get_current_state()
        self.current_state.round_number = round_id
        
        # 重置回合变量
        self.dm_narrative = None
        self.player_actions = []
        self.action_results = []
        
        # 记录日志
        self.logger.info(f"回合 {round_id} 开始于 {self.round_start_time}")
    
    def process_dm_turn(self) -> Message:
        """
        处理DM回合，获取DM的叙述推进
        
        Returns:
            Message: DM的叙述消息
        """
        # 获取当前游戏状态和剧本
        game_state = self.current_state
        scenario = self.scenario_manager.get_current_scenario()
        
        # 通过DM代理生成叙述
        dm_agent = self.agent_manager.get_dm_agent()
        dm_narrative = asyncio.run(dm_agent.dm_generate_narrative(game_state, scenario))
        self.dm_narrative = dm_narrative
        
        # 创建DM消息
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        dm_message = Message(
            message_id=message_id,
            type=MessageType.DM,
            sender="DM",
            content=dm_narrative,
            timestamp=timestamp,
            visibility=MessageVisibility.PUBLIC,
            recipients=self.game_state_manager.get_player_ids(),
            round_id=self.current_round_id
        )
        
        # 广播DM消息
        self.message_dispatcher.broadcast_message(dm_message)
        
        # 更新游戏状态
        update_request = StateUpdateRequest(
            dm_narrative=dm_narrative,
            action_context={
                "type": "dm_narration",
                "round": self.current_round_id
            }
        )
        self.current_state = self.game_state_manager.update_state(update_request)
        
        return dm_message
    
    async def process_player_turns(self) -> List[PlayerAction]:
        """
        处理所有玩家回合，收集玩家行动
        使用gather模式并行处理所有玩家行动，统一处理结果
        
        Returns:
            List[PlayerAction]: 玩家行动列表
        """
        player_ids = self.game_state_manager.get_player_ids()
        
        # 准备所有玩家的行动任务
        player_tasks = []
        player_id_to_index = {}
        
        for i, player_id in enumerate(player_ids):
            # 获取玩家上下文
            player_memory = self.perspective_info_manager.get_player_memory(player_id)
            
            # 玩家决策行动（异步）
            player_agent = self.agent_manager.get_player_agent(player_id)
            task = player_agent.player_decide_action(player_id, player_memory)
            player_tasks.append(task)
            player_id_to_index[player_id] = i
        
        # 并行等待所有玩家行动完成
        try:
            # 使用gather并行处理所有行动
            action_results = await asyncio.gather(*player_tasks)
            player_actions = []
            player_messages = []
            
            # 处理每个玩家的行动结果
            for i, player_id in enumerate(player_ids):
                player_action = action_results[i]
                player_actions.append(player_action)
                
                # 创建玩家消息
                message_id = str(uuid.uuid4())
                timestamp = datetime.now().isoformat()
                
                player_message = Message(
                    message_id=message_id,
                    type=MessageType.PLAYER if player_action.action_type == "对话" else MessageType.ACTION,
                    sender=player_id,
                    content=player_action.content,
                    timestamp=timestamp,
                    visibility=MessageVisibility.PUBLIC,
                    recipients=player_action.target if isinstance(player_action.target, list) else [player_action.target],
                    round_id=self.current_round_id
                )
                player_messages.append(player_message)
            
            # 统一广播所有玩家消息
            for message in player_messages:
                self.message_dispatcher.broadcast_message(message)
            
            # 统一更新所有玩家上下文
            for player_id in player_ids:
                for message in player_messages:
                    if message.sender != player_id:  # 不更新自己发的消息
                        self.perspective_info_manager.update_player_context(player_id, message)
            
            self.logger.info(f"所有玩家行动已完成并广播，共 {len(player_actions)} 个")
            
            # 统一保存玩家行动
            self.player_actions = player_actions
            
            return player_actions
            
        except Exception as e:
            self.logger.error(f"处理玩家行动时出错: {str(e)}")
            # 发生错误时返回空列表
            return []

    def resolve_actions(self, actions: List[PlayerAction]) -> List[ActionResult]:
        """
        解析处理玩家行动的判定
        
        Args:
            actions: 玩家行动列表
            
        Returns:
            List[ActionResult]: 行动结果列表
        """
        action_results = []
        
        # 过滤出需要解析的实质性行动（非对话类）
        substantive_actions = [action for action in actions if action.action_type == "行动"]
        
        # 处理每个实质性行动
        for action in substantive_actions:
            # 检查前置条件（如物品检查）
            if "使用" in action.content.lower():
                # 简单的物品检查示例
                item_name = action.content.split("使用")[1].strip().split()[0]
                item_result = self.game_state_manager.check_item(action.player_id, item_name)
                
                if not item_result.has_item:
                    # 如果玩家没有物品，创建失败结果
                    action_result = ActionResult(
                        player_id=action.player_id,
                        action=action,
                        success=False,
                        narrative=f"{action.player_id}尝试使用{item_name}，但没有这个物品。",
                        state_changes={}
                    )
                    action_results.append(action_result)
                    
                    # 创建结果消息
                    message_id = str(uuid.uuid4())
                    timestamp = datetime.now().isoformat()
                    
                    result_message = Message(
                        message_id=message_id,
                        type=MessageType.RESULT,
                        sender="DM",
                        content=action_result.narrative,
                        timestamp=timestamp,
                        visibility=MessageVisibility.PUBLIC,
                        recipients=self.game_state_manager.get_player_ids(),
                        round_id=self.current_round_id
                    )
                    
                    # 广播结果消息
                    self.message_dispatcher.broadcast_message(result_message)
                    continue
            
            # 检查是否需要掷骰子
            dice_result = None
            if any(keyword in action.content.lower() for keyword in ["检查", "尝试", "技能", "攻击"]):
                raw_value = self.agent_manager.roll_dice("d20")
                dice_result = DiceResult(
                    raw_value=raw_value,
                    modified_value=raw_value + 5,  # 简单示例，实际应考虑角色技能加成
                    modifiers={"技能": 3, "属性": 2}
                )
                
                # 创建骰子消息
                message_id = str(uuid.uuid4())
                timestamp = datetime.now().isoformat()
                
                dice_message = Message(
                    message_id=message_id,
                    type=MessageType.DICE,
                    sender=action.player_id,
                    content=f"掷骰结果: {dice_result.raw_value} + 修正值 {5} = {dice_result.modified_value}",
                    timestamp=timestamp,
                    visibility=MessageVisibility.PUBLIC,
                    recipients=self.game_state_manager.get_player_ids(),
                    round_id=self.current_round_id
                )
                
                # 广播骰子消息
                self.message_dispatcher.broadcast_message(dice_message)
            
            # DM解析行动结果
            dm_agent = self.agent_manager.get_dm_agent()
            action_result = asyncio.run(dm_agent.dm_resolve_action(action, self.current_state))
            action_results.append(action_result)
            
            # 创建结果消息
            message_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            result_message = Message(
                message_id=message_id,
                type=MessageType.RESULT,
                sender="DM",
                content=action_result.narrative,
                timestamp=timestamp,
                visibility=MessageVisibility.PUBLIC,
                recipients=self.game_state_manager.get_player_ids(),
                round_id=self.current_round_id
            )
            
            # 广播结果消息
            self.message_dispatcher.broadcast_message(result_message)
            
            # 更新游戏状态
            update_request = StateUpdateRequest(
                dm_narrative=action_result.narrative,
                action_context={
                    "player": action.player_id,
                    "action": action.content,
                    "success": action_result.success
                }
            )
            self.current_state = self.game_state_manager.update_state(update_request)
        
        # 保存行动结果
        self.action_results = action_results
        
        return action_results
    
    def end_round(self) -> GameState:
        """
        结束回合，更新并返回最终游戏状态
        
        Returns:
            GameState: 更新后的游戏状态
        """
        # 检查是否有新的事件触发
        triggered_events = self.scenario_manager.check_event_triggers(self.current_state)
        
        # 处理触发的事件
        for event in triggered_events:
            if not any(e.event_id == event.event_id for e in self.current_state.active_events):
                self.current_state.active_events.append(event)
                self.logger.info(f"触发新事件: {event.name}")
        
        # 检查是否有完成的事件
        completed_events = []
        for event in self.current_state.active_events:
            if event.is_completed:
                completed_events.append(event)
                self.scenario_manager.complete_event(event.event_id)
        
        # 将完成的事件从活跃事件中移除，添加到已完成事件中
        for event in completed_events:
            self.current_state.active_events.remove(event)
            self.current_state.completed_events.append(event)
        
        # 保存当前游戏状态
        self.game_state_manager.save_state()
        
        # 检查游戏是否结束
        if self.should_terminate(self.current_state):
            self.current_state.is_finished = True
            self.logger.info("游戏满足结束条件，已标记为结束状态")
        
        # 记录回合结束
        round_duration = datetime.now() - self.round_start_time
        self.logger.info(f"回合 {self.current_round_id} 结束，持续时间: {round_duration}")
        
        return self.current_state

    async def execute_round(self, state: GameState) -> GameState:
        """
        执行单个回合的所有步骤
        
        Args:
            state: 当前游戏状态
            
        Returns:
            GameState: 更新后的游戏状态
        """
        try:
            # 设置当前状态
            self.current_state = state
            
            # 1. 开始回合
            round_id = state.round_number + 1
            self.start_round(round_id)
            
            # 2. 处理DM回合
            dm_message = self.process_dm_turn()
            
            # 3. 处理玩家回合
            player_actions = await self.process_player_turns()
            
            # 4. 解析玩家行动
            action_results = self.resolve_actions(player_actions)
            
            # 5. 结束回合
            updated_state = self.end_round()
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"回合执行过程中出现错误: {str(e)}")
            # 处理异常情况，记录错误并返回原始状态
            return state

    def should_terminate(self, state: GameState) -> bool:
        """
        判断当前回合是否满足终止条件
        
        Args:
            state: 当前游戏状态
            
        Returns:
            bool: 是否应该终止游戏
        """
        # 检查是否达到最大回合数
        if state.round_number >= state.max_rounds:
            self.logger.info(f"已达到最大回合数 {state.max_rounds}，游戏将结束")
            return True
        
        # 检查是否有特殊事件触发游戏结束
        for event in state.active_events:
            if hasattr(event, 'consequences') and "终止游戏" in event.consequences:
                self.logger.info(f"事件 '{event.name}' 触发了游戏结束")
                return True
        
        # 检查玩家状态，例如是否所有玩家都已达成目标或全部阵亡
        all_players_completed = True
        all_players_dead = True
        
        for player_id, status in state.characters.items():
            # 假设玩家有目标完成标志
            if not status.metadata.get('goal_completed', False):
                all_players_completed = False
            
            # 假设血量为0表示阵亡
            if status.health > 0:
                all_players_dead = False
        
        if all_players_completed:
            self.logger.info("所有玩家都已完成目标，游戏将结束")
            return True
            
        if all_players_dead:
            self.logger.info("所有玩家都已阵亡，游戏将结束")
            return True
        
        return False
