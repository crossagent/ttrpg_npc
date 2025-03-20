from autogen_agentchat.messages import TextMessage, ChatMessage
from autogen_core import CancellationToken
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from src.models.scenario_models import Scenario
from src.models.game_state_models import GameState
from src.models.action_models import PlayerAction
from src.agents.base_agent import BaseAgent
import uuid

class PlayerAgent(BaseAgent):
    """
    玩家Agent类，负责生成玩家的观察、状态、思考和行动
    """
    
    def __init__(self, agent_id: str, agent_name: str, character_id:str, model_client=None):
        """
        初始化玩家Agent
        
        Args:
            agent_id: Agent唯一标识符
            agent_name: Agent名称
            character_id: 角色ID
            model_client: 模型客户端
        """
        # 初始化BaseAgent
        BaseAgent.__init__(self, agent_id=agent_id, agent_name=agent_name, model_client=model_client)

        self.character_id = character_id

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

    async def player_decide_action(self, game_state: GameState) -> PlayerAction:
        """
        玩家决策行动
        
        Args:
            game_state: 游戏状态，包含消息历史
            
        Returns:
            PlayerAction: 玩家行动
        """
        # 获取未读消息
        unread_messages = self.get_unread_messages(game_state)
        
        # 从game_state中获取角色信息
        if self.character_id in game_state.characters:
            character_ref = game_state.characters[self.character_id]
            # 创建包含角色信息的字典
            character_profile = {
                "name": character_ref.name,
                "personality": character_ref.additional_info.get("personality", "无特定性格"),
                "background": character_ref.additional_info.get("background", "无背景故事")
            }
            system_message = self._generate_system_message(character_profile)
        
        formatted = []
        for msg in unread_messages:
            formatted.append(f"{msg.source}: {msg.content}")

        # 处理未读消息，生成行动
        # 这里是简化的实现，实际应该调用LLM生成行动
        player_action = PlayerAction(
            player_id=self.agent_id,
            character_id=self.character_id,
            action_type="对话",
            content=f"我是{self.name},我看到了{formatted}\n,基于此我正在思考下一步行动...\n",
            target="all",
            timestamp=datetime.now().isoformat()
        )
        
        return player_action