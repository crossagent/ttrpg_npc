from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from autogen_agentchat.agents import BaseChatAgent

from src.models.game_state_models import GameState
from src.models.scenario_models import Scenario
from src.engine.scenario_manager import ScenarioManager # Import ScenarioManager
from src.engine.chat_history_manager import ChatHistoryManager # Import ChatHistoryManager
from src.models.action_models import PlayerAction, ActionResult
from src.agents.dm_agent import DMAgent
from src.agents.companion_agent import CompanionAgent
from src.agents.player_agent import PlayerAgent # 导入 PlayerAgent
from src.agents.base_agent import BaseAgent
from src.agents import RefereeAgent # 导入 RefereeAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from src.config.config_loader import load_llm_settings, load_config
from autogen_core.models import ModelFamily

class AgentManager:
    """
    Agent管理器类，负责管理DM和玩家的AI代理，处理决策生成。
    """
    
    def __init__(self, game_state: GameState, scenario_manager: ScenarioManager, chat_history_manager: ChatHistoryManager): # Add chat_history_manager
        """
        初始化Agent系统
        
        Args:
            game_state: 游戏状态
            scenario_manager: ScenarioManager 实例
            chat_history_manager: ChatHistoryManager 实例 # Add doc
        """
        self.dm_agent: Optional[DMAgent] = None
        # 这个字典现在会存储 PlayerAgent 和 CompanionAgent 实例
        self.player_agents: Dict[str, Union[PlayerAgent, CompanionAgent]] = {}
        self.referee_agent: Optional[RefereeAgent] = None # 添加 referee_agent 属性
        self.game_state = game_state
        self.scenario_manager = scenario_manager # Store scenario_manager
        self.chat_history_manager = chat_history_manager # Store chat_history_manager
        self.all_agents: Dict[str, BaseAgent] = {}  # 存储所有Agent实例，键为agent_id

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
        根据剧本信息和玩家选择初始化代理。
        - 为玩家选择的角色创建 PlayerAgent。
        - 为其他 is_playable=True 的角色创建 CompanionAgent。
        - 初始化 DM 和 Referee Agent。

        Args:
            scenario: 剧本对象
        """
        if not self.game_state:
            raise ValueError("游戏状态未初始化 (Game state not initialized)")
        if not self.game_state.player_character_id:
             raise ValueError("玩家角色ID未在游戏状态中设置 (Player character ID not set in game state)")

        print("Initializing agents...")
        self.player_agents.clear()
        self.all_agents.clear()

        # 初始化DM代理
        self.dm_agent = DMAgent(
            agent_id="dm",
            agent_name="DM",
            scenario_manager=self.scenario_manager, # Pass scenario_manager
            chat_history_manager=self.chat_history_manager, # Pass chat_history_manager
            model_client=self.model_client
        )
        self.all_agents["dm"] = self.dm_agent # 使用 "dm" 作为 agent_id

        # 初始化 RefereeAgent
        self.referee_agent = RefereeAgent(
            agent_id="referee",
            agent_name="Referee",
            scenario_manager=self.scenario_manager, # Pass scenario_manager
            chat_history_manager=self.chat_history_manager, # Pass chat_history_manager
            model_client=self.model_client
        )
        self.all_agents["referee"] = self.referee_agent # 添加到 all_agents
        print(f"  Initialized Referee Agent: {self.referee_agent.agent_id}")

        # 遍历剧本中的静态角色信息来创建 Agent
        for character_id, char_info in scenario.characters.items():
            agent_instance: Optional[Union[PlayerAgent, CompanionAgent]] = None
            agent_id = character_id # 使用角色ID作为Agent ID

            if character_id == self.game_state.player_character_id:
                # 创建玩家控制的 Agent
                print(f"  Creating PlayerAgent for selected character: {character_id} ({char_info.name})")
                agent_instance = PlayerAgent(
                    agent_id=agent_id,
                    agent_name=char_info.name,
                    character_id=character_id,
                    scenario_manager=self.scenario_manager,
                    chat_history_manager=self.chat_history_manager, # Pass chat_history_manager
                    model_client=self.model_client
                )
            elif char_info.is_playable:
                # 创建 AI 控制的陪玩 Agent
                print(f"  Creating CompanionAgent for playable character: {character_id} ({char_info.name})")
                agent_instance = CompanionAgent(
                    agent_id=agent_id,
                    agent_name=char_info.name,
                    character_id=character_id,
                    scenario_manager=self.scenario_manager,
                    chat_history_manager=self.chat_history_manager, # Pass chat_history_manager
                    model_client=self.model_client
                )
            else:
                # 非玩家角色，不创建 Agent 实例
                print(f"  Skipping Agent creation for non-playable character: {character_id} ({char_info.name})")
                continue # 跳到下一个角色

            # 存储创建的 Agent
            if agent_instance:
                self.player_agents[character_id] = agent_instance
                self.all_agents[agent_id] = agent_instance # 使用 character_id 作为 agent_id
                print(f"    Stored Agent: {agent_id} ({type(agent_instance).__name__})")

        print(f"Agent initialization complete. Total agents in all_agents: {len(self.all_agents)}")
        print(f"Playable/Companion agents in player_agents: {list(self.player_agents.keys())}")


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

    def get_referee_agent(self) -> Optional[RefereeAgent]:
        """
        获取裁判代理实例

        Returns:
            Optional[RefereeAgent]: 裁判代理实例
        """
        return self.referee_agent

    def get_player_agent(self, character_id: str) -> Optional[Union[PlayerAgent, CompanionAgent]]:
        """
        获取与指定角色ID关联的玩家或陪玩代理实例。

        Args:
            character_id: 角色ID

        Returns:
            Optional[Union[PlayerAgent, CompanionAgent]]: 代理实例，如果不存在则为None
        """
        return self.player_agents.get(character_id)

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
