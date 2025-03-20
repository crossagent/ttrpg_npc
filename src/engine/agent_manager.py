from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from autogen_agentchat.agents import BaseChatAgent

from src.models.game_state_models import GameState
from src.models.scenario_models import Scenario
from src.models.action_models import PlayerAction, ActionResult
from src.agents.dm_agent import DMAgent
from src.agents.player_agent import PlayerAgent
from src.agents.base_agent import BaseAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from src.config.config_loader import load_llm_settings, load_config
from autogen_core.models import ModelFamily

class AgentManager:
    """
    Agent管理器类，负责管理DM和玩家的AI代理，处理决策生成。
    """
    
    def __init__(self, game_state=None):
        """
        初始化Agent系统
        
        Args:
            game_state: 游戏状态
        """
        self.dm_agent = None
        self.player_agents = {}  # 改为字典，键为玩家ID
        self.game_state = game_state
        self.all_agents = {}  # 存储所有Agent实例，键为agent_id
        
                # 加载LLM配置
        llm_settings = load_llm_settings()
        
        # 使用配置初始化模型客户端
        self.model_client = OpenAIChatCompletionClient(
            model=llm_settings.model,
            api_key=llm_settings.openai_api_key,
            temperature=llm_settings.temperature,
            base_url=llm_settings.base_url,
            model_info={
                "name": llm_settings.model,
                "vision": False,
                "function_calling": False,
                "json_output": False,
                'family': ModelFamily.UNKNOWN
            }
        )
    
    def initialize_agents_from_characters(self, scenario: Scenario):
        """
        从游戏角色初始化代理。为所有角色创建代理，无论是否已分配给玩家。
        
        Args:
            scenario: 剧本对象
        """
        if not self.game_state:
            raise ValueError("游戏状态未初始化")
        
        # 初始化DM代理
        self.dm_agent = DMAgent(
            agent_id="dm",
            agent_name="DM",
            model_client=self.model_client
        )
        self.all_agents["char_dm"] = self.dm_agent
        
        # 为所有角色创建代理，无论是否已分配给玩家
        for character_id, character_ref in self.game_state.characters.items():
            # 检查角色是否已分配给玩家
            player_id = None
            is_player_controlled = False
            
            # 如果未分配给玩家，使用临时ID
            if not player_id:
                player_id = f"npc_{character_id}"
            
            # 创建角色代理
            player_agent = PlayerAgent(
                agent_id=player_id,
                agent_name=character_ref.name,
                character_id=character_id,
                model_client=self.model_client
            )
            
            # 设置是否由玩家控制的标志
            player_agent.is_player_controlled = is_player_controlled
            
            # 添加到代理列表
            self.player_agents[character_id] = player_agent
            self.all_agents[character_id] = player_agent
            
            # 更新角色的控制状态
            if character_ref:
                character_ref.player_controlled = is_player_controlled
    
    def register_agent(self, agent_id: str, agent_type: str, agent_instance: BaseAgent) -> bool:
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
            self.all_agents[agent_id] = agent_instance
            return True
        elif agent_type == "player":
            self.player_agents[agent_id] = agent_instance
            self.all_agents[agent_id] = agent_instance
            return True
        else:
            return False
    
    def get_dm_agent(self) -> Optional[DMAgent]:
        """
        获取DM代理实例
        
        Returns:
            Optional[DMAgent]: DM代理实例
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
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        获取任意代理实例
        
        Args:
            agent_id: 代理ID
            
        Returns:
            Optional[BaseAgent]: 代理实例，如果不存在则为None
        """
        return self.all_agents.get(agent_id)
    
    def get_all_player_ids(self) -> List[str]:
        """
        获取所有玩家ID
        
        Returns:
            List[str]: 所有玩家ID列表
        """
        return list(self.player_agents.keys())
    
    def get_all_agent_ids(self) -> List[str]:
        """
        获取所有代理ID
        
        Returns:
            List[str]: 所有代理ID列表
        """
        return list(self.all_agents.keys())
    
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
