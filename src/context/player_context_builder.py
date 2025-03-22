"""
玩家上下文构建模块，负责构建玩家Agent所需的各类上下文文本。
"""
from typing import List, Dict, Any, Optional
from src.models.game_state_models import GameState
from src.models.message_models import Message
from src.context.context_utils import format_messages
from src.models.context_models import PlayerActionLLMOutput
from src.models.llm_validation import create_validator_for

def build_decision_system_prompt(character_profile: Dict[str, Any]) -> str:
    """
    构建玩家决策的系统提示
    
    Args:
        character_profile: 角色资料
        
    Returns:
        str: 系统提示文本
    """
    # 创建验证器并获取提示指令
    validator = create_validator_for(PlayerActionLLMOutput)
    model_instruction = validator.get_prompt_instruction()
    
    return f"""你是一个名为{character_profile.get('name', '未知')}的角色。
你的性格特点：{character_profile.get('personality', '无特定性格')}
你的背景故事：{character_profile.get('background', '无背景故事')}

在每个回合中，你需要生成角色的观察、决策逻辑、思考和行动。

{model_instruction}

注意：只有"action"部分会被其他人看到，其他部分只有你自己知道。
根据当前情境和角色性格来调整你的目标、计划、心情和行动。
"""

def build_decision_user_prompt(
    game_state: GameState, 
    unread_messages: List[Message]
) -> str:
    """
    构建玩家决策的用户提示
    
    Args:
        game_state: 游戏状态
        unread_messages: 未读消息列表
        
    Returns:
        str: 用户提示文本
    """
    # 格式化未读消息
    formatted_messages = format_messages(unread_messages)
    
    return f"""
【第{game_state.round_number}回合】

最近的信息:
{formatted_messages}

请根据角色性格和当前情境，生成一个合理的响应。
"""

def build_reaction_system_prompt(character_profile: Dict[str, Any]) -> str:
    """
    构建玩家反应的系统提示
    
    Args:
        character_profile: 角色资料
        
    Returns:
        str: 系统提示文本
    """
    return f"""你是一个名为{character_profile.get('name', '未知')}的角色。
你的性格特点：{character_profile.get('personality', '无特定性格')}
你的背景故事：{character_profile.get('background', '无背景故事')}

你需要对特定事件或情况做出反应。请生成以下内容：
1. 情绪反应(emotion)：你对事件的情绪反应
2. 思考(thinking)：你的内心想法
3. 反应(reaction)：你表现出的外在反应，这部分将被其他角色看到

你的响应必须是一个JSON格式，包含以上字段。例如：

```json
{{
  "emotion": "震惊",
  "thinking": "这太出乎意料了，我需要重新评估情况...",
  "reaction": "我睁大眼睛，后退一步，结结巴巴地说：'这...这不可能！'"
}}
```

请确保你的反应符合角色的性格特点和背景故事。
"""

def build_reaction_user_prompt(
    game_state: GameState, 
    event_description: str
) -> str:
    """
    构建玩家反应的用户提示
    
    Args:
        game_state: 游戏状态
        event_description: 事件描述
        
    Returns:
        str: 用户提示文本
    """
    return f"""
【第{game_state.round_number}回合】

发生了以下事件:
{event_description}

请以你的角色身份，对这一事件做出反应。
"""
