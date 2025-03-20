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
            
        # 提取NPC列表（角色名称）
        npc_list = list(scenario.characters.keys())
        
        # 提取地点列表
        location_list = list(scenario.locations.keys()) if scenario.locations else []
        
        return f"""你是一个桌面角色扮演游戏的主持人(DM)，负责描述场景、推动故事情节发展，并处理玩家的行动。
    当前游戏的背景设定是：{scenario.story_info.background}
    主要场景包括：{', '.join(location_list) if location_list else '未指定'}
    主要NPC包括：{', '.join(npc_list) if npc_list else '未指定'}
    
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
        """
        # 获取未读消息和当前场景
        unread_messages = self.get_unread_messages(game_state)
        current_scene = self._get_current_scene(scenario, game_state.round_number)
        
        # 格式化未读消息
        formatted_messages = "\n".join([f"{msg.source}: {msg.content}" for msg in unread_messages]) or "没有新消息"
        
        # 如果有模型客户端，使用AutoGen的方式生成叙述
        if not self.assistant:
            return "Assistant未初始化"
        
        # 设置系统消息
        system_message = self._generate_system_message(scenario)
        self.assistant.system_message = system_message
        
        # 构建用户消息
        user_message = TextMessage(
            content=f"""
【第{game_state.round_number}回合】

最近的玩家消息:
{formatted_messages}

当前场景:
{current_scene}

请基于以上信息，生成一段生动的场景描述。描述应该:
1. 提及重要的场景元素和NPC
2. 反映玩家之前行动的影响
3. 暗示可能的行动方向
4. 以一个引导性问题结束，如"你们看到了什么？你们将如何行动？"
""",
            source="system"
        )
        
        try:
            # 使用assistant的on_messages方法
            response = await self.assistant.on_messages([user_message], CancellationToken())
            if response and response.chat_message:
                return response.chat_message.content
        except Exception as e:
            print(f"Assistant生成叙述失败，回退到模板方法: {str(e)}")
        

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

    def _get_current_scene(self, scenario: Scenario, round_number: int) -> str:
        """获取当前场景描述"""
        if not scenario.locations:
            return "未指定场景"
            
        location_keys = list(scenario.locations.keys())
        if not location_keys:
            return "未指定场景"
            
        current_loc_key = location_keys[min(round_number, len(location_keys) - 1)]
        return scenario.locations[current_loc_key].description
