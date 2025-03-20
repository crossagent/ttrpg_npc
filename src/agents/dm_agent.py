from autogen_agentchat.messages import TextMessage, ChatMessage
from autogen_core import CancellationToken
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from src.models.scenario_models import Scenario
from src.models.game_state_models import GameState
from src.models.action_models import PlayerAction, ActionResult
from src.agents.base_agent import BaseAgent

class DMAgent(BaseAgent):
    """
    DM Agent类，负责生成游戏叙述和处理玩家行动
    """
    
    def __init__(self, agent_id: str, name: str):
        """
        初始化DMAgent
        
        Args:
            agent_id: Agent唯一标识符
            name: Agent名称
            scenario: 游戏剧本
            game_state: 游戏状态
            model_client: 模型客户端
        """
        # 初始化BaseAgent
        BaseAgent.__init__(self, agent_id=agent_id, name=name)

    def _generate_system_message(self, scenario: Optional[Scenario]) -> str:
        """
        根据剧本生成系统提示
        
        Args:
            scenario: 游戏剧本
            
        Returns:
            str: 系统提示
        """
        if not scenario:
            return "你是一个桌面角色扮演游戏的主持人(DM)，负责描述场景、推动故事情节发展，并处理玩家的行动。"
            
        return f"""你是一个桌面角色扮演游戏的主持人(DM)，负责描述场景、推动故事情节发展，并处理玩家的行动。
当前游戏的背景设定是：{scenario.背景设定}
主要场景包括：{', '.join(scenario.场景列表)}
主要NPC包括：{', '.join(scenario.NPC列表)}

你的任务是：
1. 生成生动的场景描述
2. 根据玩家行动给出合理的结果
3. 推动故事情节发展
4. 确保游戏体验有趣且具有挑战性

请记住，你是一个公正的裁判，不要偏袒任何玩家，也不要过于严苛或宽松。
"""

    async def dm_generate_narrative(self, game_state: GameState, scenario: Scenario) -> str:
        """
        DM生成叙述
        
        Args:
            game_state: 游戏状态
            scenario: 剧本
            
        Returns:
            str: 生成的叙述文本
        """
        # 获取未读消息，了解最新情况
        unread_messages = self.get_unread_messages(game_state)
        
        # 生成系统消息
        system_message = self._generate_system_message(scenario)
        
        # 这里是简化的实现，实际应该调用LLM生成叙述
        round_number = game_state.round_number
        current_scene = scenario.场景列表[min(round_number, len(scenario.场景列表) - 1)]
        
        narrative = f"【第{round_number}回合】\n\n{current_scene}场景中，冒险继续进行...\n\n"
        narrative += "你们看到了什么？你们将如何行动？"
        
        return narrative

    async def dm_resolve_action(self, action: PlayerAction, game_state: GameState) -> ActionResult:
        """
        DM解析玩家行动并生成结果
        
        Args:
            action: 玩家行动
            game_state: 游戏状态
            
        Returns:
            ActionResult: 行动结果
        """
        # 这里是简化的实现，实际应该调用LLM生成结果
        success = True  # 简单示例，实际应根据行动难度和角色能力判定
        
        narrative = f"{action.player_id}尝试{action.content}...\n"
        if success:
            narrative += f"成功了！{action.player_id}的行动取得了预期效果。"
        else:
            narrative += f"失败了。{action.player_id}的行动没有达到预期效果。"
        
        # 创建行动结果
        result = ActionResult(
            player_id=action.player_id,
            action=action,
            success=success,
            narrative=narrative,
            state_changes={}  # 实际应根据行动更新游戏状态
        )
        
        return result
