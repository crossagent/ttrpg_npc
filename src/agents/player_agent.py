from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage, ChatMessage
from autogen_core import CancellationToken
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

from src.models.gameSchema import PlayerResponse, CharacterState, HistoryMessage

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
        self.character_state = CharacterState(
            goal="探索冒险世界",
            plan="跟随团队，根据情况调整策略",
            mood="期待",
            health=100
        )
        
        # 系统记录的玩家历史，使用标准的HistoryMessage格式
        self.history: List[HistoryMessage] = []
        
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
        
    async def generate_response(self, messages: List[HistoryMessage], cancellation_token: CancellationToken, round_number: int = 0) -> PlayerResponse:
        """
        根据聊天历史生成玩家响应
        
        Args:
            messages: 聊天历史消息，使用HistoryMessage格式
            cancellation_token: 取消令牌
            round_number: 当前回合数（新增参数）
            
        Returns:
            PlayerResponse: 包含观察、状态、思考和行动的响应
        """
        # 记录传入的消息到history中
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 将传入的消息记录到history中
        for msg in messages:
            # 消息已经是HistoryMessage格式，直接添加到历史记录中
            self.history.append(msg)
        
        # 调用LLM生成响应
        response = await super().on_messages(messages, cancellation_token)
        llm_response = response.chat_message
        
        # 解析响应中的JSON
        try:
            content = llm_response.content
            # 提取JSON部分
            if "```json" in content and "```" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content
                
            response_dict = json.loads(json_str)
            
            # 解析角色状态
            character_state_dict = response_dict.get("character_state", {})
            character_state = CharacterState(
                goal=character_state_dict.get("goal", self.character_state.goal),
                plan=character_state_dict.get("plan", self.character_state.plan),
                mood=character_state_dict.get("mood", self.character_state.mood),
                health=character_state_dict.get("health", self.character_state.health)
            )
            
            # 更新角色状态
            self.character_state = character_state
            
            player_response = PlayerResponse(
                observation=response_dict.get("observation", ""),
                character_state=character_state,
                thinking=response_dict.get("thinking", ""),
                action=response_dict.get("action", "")
            )
            
            # 记录玩家的响应到history
            self.history.append(HistoryMessage(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                round=round_number,
                character_name=self.name,
                message=f"{self.name}：观察-{player_response.observation}"
            ))
            
            # 记录角色状态
            self.history.append(HistoryMessage(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                round=round_number,
                character_name=self.name,
                message=f"{self.name}：状态-目标：{character_state.goal}，计划：{character_state.plan}，心情：{character_state.mood}，血量：{character_state.health}"
            ))
            
            # 记录思考过程
            self.history.append(HistoryMessage(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                round=round_number,
                character_name=self.name,
                message=f"{self.name}：思考-{player_response.thinking}"
            ))
            
            # 记录行动
            self.history.append(HistoryMessage(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                round=round_number,
                character_name=self.name,
                message=f"{self.name}：行动-{player_response.action}"
            ))
            
            return player_response
            
        except Exception as e:
            # 如果解析失败，返回一个默认响应
            print(f"解析玩家响应失败: {e}")
            default_response = PlayerResponse(
                observation="(解析失败)",
                character_state=self.character_state,
                thinking="(解析失败)",
                action=llm_response.content
            )
            
            # 记录失败的响应
            self.history.append(HistoryMessage(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                round=round_number,
                character_name=self.name,
                message=f"{self.name}：行动-{default_response.action} (解析失败)"
            ))
            
            return default_response
    
    # record_response方法已不再需要，所有记录都在generate_response中完成
        
    def get_history(self) -> List[HistoryMessage]:
        """
        获取玩家历史记录
        
        Returns:
            List[HistoryMessage]: 玩家历史记录列表
        """
        return self.history
