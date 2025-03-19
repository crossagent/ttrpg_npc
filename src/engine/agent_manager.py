from typing import List, Dict, Any, Optional
from datetime import datetime
from autogen_agentchat.agents import BaseChatAgent

from src.models.game_state_models import GameState
from src.models.scenario_models import Scenario
from src.models.message_models import MessageReadMemory
from src.models.action_models import PlayerAction, ActionResult
from src.agents.dm_agent import DMAgent
from src.agents.player_agent import PlayerAgent
from src.communication.perspective_info_manager import PerspectiveInfoManager


class AgentManager:
    """
    Agent管理器类，负责管理DM和玩家的AI代理，处理决策生成。
    """
    
    def __init__(self, perspective_manager=None):
        """
        初始化Agent系统
        
        Args:
            dm_agent: DM代理
            player_agents: 玩家代理字典，键为玩家ID
            perspective_manager: 个人视角信息管理器
        """
        self.dm_agent = None
        self.player_agents = []
        self.perspective_manager = perspective_manager or PerspectiveInfoManager()
    
    def register_agent(self, agent_id: str, agent_type: str, agent_instance) -> bool:
        """
        注册代理
        
        Args:
            agent_id: 代理ID
            agent_type: 代理类型（dm/player）
            agent_instance: 代理实例
            
        Returns:
            bool: 是否注册成功
        """
        if agent_type == "dm":
            self.dm_agent = agent_instance
            return True
        elif agent_type == "player":
            self.player_agents[agent_id] = agent_instance
            
            # 如果是玩家代理，同时初始化该玩家的视角信息
            if self.perspective_manager:
                character_name = getattr(agent_instance, 'character_profile', {}).get('name', agent_id)
                self.perspective_manager.initialize_player_memory(agent_id, character_name)
                
            return True
        else:
            return False
    
    def get_dm_agent(self) -> DMAgent:
        """
        获取DM代理实例
        
        Returns:
            DMAgent: DM代理实例
        """
        return self.dm_agent

    def get_player_agent(self, agent_id: str) -> Optional[PlayerAgent]:
        """
        获取玩家代理实例
        
        Args:
            agent_id: 代理ID
            
        Returns:
            Optional[PlayerAgent]: 玩家代理实例，如果不存在则为None
        """
        return self.player_agents.get(agent_id)
    
    def get_player_memory(self, player_id: str) -> MessageReadMemory:
        """
        获取玩家上下文
        
        Args:
            player_id: 玩家ID
            
        Returns:
            MessageReadMemory: 玩家消息记录
        """
        if not self.perspective_manager:
            raise ValueError("视角管理器未初始化")
            
        return self.perspective_manager.get_player_memory(player_id)
    
    def get_all_players(self) -> List[BaseChatAgent]:
        """
        获取所有玩家ID
        
        Returns:
            List[str]: 所有玩家ID列表
        """
        return list(self.player_agents)
    
    def roll_dice(self, dice_type: str, modifiers: Dict[str, int] = None) -> int:
        """
        掷骰
        
        Args:
            dice_type: 骰子类型（如"d20"）
            modifiers: 修饰因素
            
        Returns:
            int: 掷骰结果
        """
        pass
