from autogen_agentchat.agents import AssistantAgent, BaseChatAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage, ChatMessage
from typing import Dict, List, Any, Callable, Optional
import asyncio
from datetime import datetime

# 导入我们的数据模型和Agent
from src.models.gameSchema import GameState, AgentConfig
from src.agents.player_agent import PlayerAgent
from src.config.config_loader import load_llm_settings
from src.config.color_utils import (
    format_dm_message, format_player_message, format_observation,
    format_state, format_thinking, print_colored,
    Color, green_text, yellow_text, gray_text
)

# 默认配置
DEFAULT_MAX_ROUNDS = 5

class GameEngine:
    """
    游戏引擎类，负责初始化游戏配置和状态，创建并管理所有Agent，建立GroupChat，并提供游戏启动接口
    """
    
    def __init__(self, max_rounds: int = DEFAULT_MAX_ROUNDS):
        """
        初始化游戏引擎
        
        Args:
            max_rounds: 最大回合数，默认为配置中的DEFAULT_MAX_ROUNDS
        """
        self.state = GameState(max_rounds=max_rounds)
        
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
                "context_length": 16000,  # 通义千问模型的上下文窗口大小
                "token_limit": 16000,     # 通义千问模型的令牌限制
                "max_tokens": 8000,        # 通义千问模型的最大输出令牌数
                "vision": False,
                "function_calling": False,
                "json_output": False,
                'family': 'gpt-4o'
            }
        )
        
        self.agents = []
        self.cancellation_token = CancellationToken()
    
    def init_config(self) -> GameState:
        """
        加载并解析全局配置和剧本数据
        
        Returns:
            GameState: 初始化后的游戏状态
        """
        # 在这个简单实现中，我们直接返回已初始化的状态
        return self.state
    
    def initialize_agents(self) -> List[BaseChatAgent]:
        """
        根据配置创建并注册各Agent
        
        Returns:
            List[BaseChatAgent]: 初始化后的Agent列表
        """
        # 创建DM代理 - 暂时使用简单的伪装DM
        dm_agent = AssistantAgent(
            name="dm",
            model_client=self.model_client,
            system_message="你是游戏的主持人，负责推动故事和描述场景。描述要生动有趣，富有想象力。",
        )
        
        # 创建3个玩家Agent
        player1 = PlayerAgent(
            name="warrior",
            character_profile={
                "name": "高山",
                "personality": "勇敢，直接，喜欢冲锋在前",
                "background": "来自北方山区的战士，精通近战技能",
            },
            model_client=self.model_client
        )
        
        player2 = PlayerAgent(
            name="mage",
            character_profile={
                "name": "星辰",
                "personality": "聪明，谨慎，思考周全",
                "background": "皇家魔法学院的毕业生，精通元素魔法",
            },
            model_client=self.model_client
        )
        
        player3 = PlayerAgent(
            name="rogue",
            character_profile={
                "name": "影子",
                "personality": "狡猾，机智，喜欢探索",
                "background": "出身于贫民窟，自学成才的地下城探险家",
            },
            model_client=self.model_client
        )
        
        # 人类玩家代理
        human_agent = AssistantAgent(
            name="human_player",
            model_client=self.model_client, 
            system_message="你是人类玩家的代理人，负责转达玩家的指令。"
        )
        
        self.agents = [dm_agent, player1, player2, player3, human_agent]
        return self.agents
    
    async def start_game(self) -> GameState:
        """
        启动游戏，执行回合流程
        
        Returns:
            GameState: 游戏结束后的最终状态
        """
        # 初始化配置
        self.state = self.init_config()
        
        # 初始化代理
        if not self.agents:
            self.initialize_agents()
        
        # 创建回合管理器
        from src.engine.round_manager import RoundManager
        round_manager = RoundManager(self.agents, self.cancellation_token)
        
        # 保存回合管理器的引用，以便CLI可以访问
        self.round_manager = round_manager
        
        # 执行游戏循环
        while not round_manager.should_terminate(self.state):
            self.state = await round_manager.execute_round(self.state)
            
            # 检查是否有命令
            cmd = input("输入命令(例如 /history warrior)或按回车继续: ").strip()
            if cmd.startswith("/"):
                parts = cmd.split()
                command = parts[0]
                args = parts[1:] if len(parts) > 1 else []
                
                if command == "/history" and args:
                    await self._show_player_history(args[0])
                elif command == "/chat":
                    await self._show_chat_history()
                elif command == "/quit":
                    break
                else:
                    print("未知命令，可用命令: /history [玩家名称], /chat, /quit")
        
        print(green_text(f"游戏结束，共进行了{self.state.round_number}回合。"))
    
    async def _show_player_history(self, player_name: str) -> None:
        """
        显示指定玩家的历史记录
        
        Args:
            player_name: 玩家名称
        """
        # 中文名称到英文名称的映射
        name_mapping = {
            "战士": "warrior",
            "法师": "mage",
            "盗贼": "rogue"
        }
        
        # 如果输入的是中文名称，转换为对应的英文名称
        if player_name in name_mapping:
            player_name = name_mapping[player_name]
            
        history = self.round_manager.get_player_history(player_name)
        if not history:
            print(f"找不到玩家 '{player_name}' 的历史记录")
            return
        
        print(f"\n--- {player_name} 的历史记录 ---")
        
        # 按回合分组
        rounds = {}
        for entry in history:
            # 检查entry是否为HistoryMessage对象
            if hasattr(entry, 'round'):
                round_num = entry.round
            else:
                # 兼容字典类型
                round_num = entry.get("round", 0) if hasattr(entry, 'get') else 0
                
            if round_num not in rounds:
                rounds[round_num] = []
            rounds[round_num].append(entry)
        
        # 按回合显示历史记录
        for round_num in sorted(rounds.keys()):
            if round_num == 0:  # 跳过回合为0的记录
                continue
            
            # 获取时间戳
            first_entry = rounds[round_num][0]
            if hasattr(first_entry, 'timestamp'):
                timestamp = first_entry.timestamp
            else:
                timestamp = first_entry.get('timestamp', '') if hasattr(first_entry, 'get') else ''
                
            print(f"\n回合 {round_num} ({timestamp})")
            entries = rounds[round_num]
            
            # 按时间戳排序
            def get_timestamp(x):
                if hasattr(x, 'timestamp'):
                    return x.timestamp
                return x.get('timestamp', '') if hasattr(x, 'get') else ''
            
            entries.sort(key=get_timestamp)
            
            # 显示该回合的所有记录
            for entry in entries:
                if hasattr(entry, 'message'):
                    # 如果message是TextMessage对象
                    if hasattr(entry.message, 'content'):
                        print(entry.message.content)
                    # 如果message是字符串
                    elif isinstance(entry.message, str):
                        print(entry.message)
                    # 其他情况
                    else:
                        print(str(entry.message))
                else:
                    # 兼容字典类型
                    message = entry.get('message', '') if hasattr(entry, 'get') else str(entry)
                    print(message)
    
    async def _show_chat_history(self) -> None:
        """
        显示全局聊天历史
        """
        if not self.state.chat_history:
            print("聊天历史为空")
            return
        
        print("\n--- 全局聊天历史 ---")
        for i, history_msg in enumerate(self.state.chat_history):
            # 获取消息
            message = history_msg.message
            
            # 获取消息时间戳
            timestamp = history_msg.timestamp
            
            # 根据消息来源确定颜色
            if message.source == "dm":
                # DM消息使用绿色
                print(f"\n[{timestamp}] {format_dm_message(message.source, message.content)}")
            elif message.source == "human_player":
                # 人类玩家输入使用灰色
                print(f"\n[{timestamp}] {gray_text(f'{message.source}: {message.content}')}")
            else:
                # 其他玩家消息使用绿色
                print(f"\n[{timestamp}] {format_player_message(message.source, message.content)}")
        
        print("\n" + "-" * 50)
