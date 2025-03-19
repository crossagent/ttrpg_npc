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
    
    def __init__(self, game_state=None, perspective_manager=None):
        """
        初始化Agent系统
        
        Args:
            dm_agent: DM代理
            player_agents: 玩家代理字典，键为玩家ID
            perspective_manager: 个人视角信息管理器
        """
        self.dm_agent = None
        self.player_agents = []
        self.game_state = game_state
        self.perspective_manager = perspective_manager or PerspectiveInfoManager()
    
    def initialize_agents_from_characters(self, scenario: Scenario):
        """
        从游戏角色初始化代理
        
        Args:
            scenario: 剧本对象
        """
        if not self.game_state or not self.player_manager:
            raise ValueError("游戏状态或玩家管理器未初始化")
        
        # 初始化DM代理
        self.dm_agent = DMAgent(
            scenario=scenario,
            game_state=self.game_state
        )
        
        # 对每个已分配给玩家的角色，创建相应的代理
        for character_id, character_ref in self.game_state.characters.items():
            controller = self.player_manager.get_character_controller(character_id)
            
            if controller:  # 角色由玩家控制
                # 角色已分配给玩家，创建玩家代理
                player_agent = PlayerAgent(
                    player_id=controller.player_id,
                    character_id=character_id,
                    character_name=character_ref.name,
                    character_profile=self._build_character_profile(character_id, scenario)
                )
                self.player_agents.append(player_agent)
                
                # 初始化玩家代理的视角
                self.perspective_manager.initialize_player_memory(
                    controller.player_id, 
                    character_ref.name
                )
    
    def _build_character_profile(self, character_id: str, scenario: Scenario) -> Dict[str, Any]:
        """
        构建角色档案，用于代理初始化
        
        Args:
            character_id: 角色ID
            scenario: 剧本对象
            
        Returns:
            Dict[str, Any]: 角色档案
        """
        character_info = scenario.角色信息.get(character_id, {})
        character_ref = self.game_state.characters.get(character_id)
        
        if not character_ref:
            return {}
        
        return {
            "name": character_ref.name,
            "background": character_info.get("背景故事", ""),
            "goal": character_info.get("秘密目标", ""),
            "abilities": character_info.get("特殊能力", ""),
            "weaknesses": character_info.get("弱点", ""),
            "personality": character_info.get("性格", "")
        }

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
