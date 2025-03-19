from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage, ChatMessage
from autogen_core import CancellationToken
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from src.models.scenario_models import Scenario
from src.models.context_models import PlayerContext
from src.models.game_state_models import GameState
from src.models.action_models import PlayerAction
from src.models.message_models import MessageReadMemory
from src.models.message_models import Message

class PlayerAgent(AssistantAgent):
    """
    玩家Agent类，负责生成玩家的观察、状态、思考和行动
    """
    
    def __init__(self, name: str, character_profile: Dict[str, Any], model_client, **kwargs):
        """
        初始化玩家Agent
        
        Args:
            name: Agent名称
            character_profile: 角色资料
            model_client: 模型客户端
        """
        system_message = self._generate_system_message(character_profile)
        super().__init__(name=name, model_client=model_client, system_message=system_message, **kwargs)
        self.character_profile = character_profile
        
        # 初始化角色状态
        self.character_state = PlayerContext(
            goal="探索冒险世界",
            plan="跟随团队，根据情况调整策略",
            mood="期待",
        )
        
        self.message_memory = MessageReadMemory()

    def _generate_system_message(self, character_profile: Dict[str, Any]) -> str:
        """
        根据角色资料生成系统提示
        
        Args:
            character_profile: 角色资料
            
        Returns:
            str: 系统提示
        """
        return f"""你是一个名为{character_profile.get('name', '未知')}的角色。
你的性格特点：{character_profile.get('personality', '无特定性格')}
你的背景故事：{character_profile.get('background', '无背景故事')}

在每个回合中，你需要生成以下内容：
1. 观察(observation)：你观察到的环境和其他角色的信息
2. 角色状态(character_state)：包含以下内容：
   - 目标(goal)：你当前的主要目标
   - 计划(plan)：你实现目标的计划
   - 心情(mood)：你当前的心情
   - 血量(health)：你当前的血量(0-100)
3. 思考(thinking)：你的内心想法和决策过程
4. 行动(action)：你实际采取的行动，这部分将被发送到群聊中

你的响应必须是一个JSON格式，包含以上字段。例如：

```json
{{
  "observation": "我看到DM描述了一个森林场景，其他玩家正在讨论如何前进。",
  "character_state": {{
    "goal": "找到森林中的古老神殿",
    "plan": "先侦查周围环境，然后找出安全路径",
    "mood": "警惕",
    "health": 95
  }},
  "thinking": "考虑到我的角色擅长侦查，我应该提出先侦察周围环境。地图上显示北边可能有古迹，但听说那里很危险。",
  "action": "我举起手说：'等一下，让我先侦查一下周围有没有危险，我的侦查技能很强。'"
}}
```

注意：只有"action"部分会被其他人看到，其他部分只有你自己知道。
根据当前情境和角色性格来调整你的目标、计划、心情和行动。
"""
async def player_decide_action(player_id: str, context: PlayerContext) -> PlayerAction:
    """
    玩家决策行动
    
    Args:
        player_id: 玩家ID
        context: 玩家上下文
        
    Returns:
        PlayerAction: 玩家行动
    """
    pass

async def receive_message(messages:List[Message]) -> bool:
    """
    接收消息
    
    Args:
        message: 消息
        
    Returns:
        bool: 是否接收成功
    """
    pass


