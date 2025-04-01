"""
玩家上下文构建模块，负责构建玩家Agent所需的各类上下文文本。
"""
from typing import List, Dict, Any, Optional
from src.models.game_state_models import GameState
from src.models.message_models import Message
from src.context.context_utils import format_messages
from src.models.context_models import PlayerActionLLMOutput
from src.models.llm_validation import create_validator_for
from src.models.context_models import PlayerActionSystemContext
from src.models.scenario_models import ScenarioCharacterInfo
from src.models.action_models import InternalThoughts

def build_decision_system_prompt(charaInfo: ScenarioCharacterInfo) -> str:
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


    
    return f"""你是一个名为{charaInfo.name}的角色。
你的身份：{charaInfo.public_identity}
你的背景故事：{charaInfo.background}
你的秘密目标：{charaInfo.secret_goal}
你的弱点：{charaInfo.weakness}

在每个回合中，你需要通过以下步骤进行角色思考和决策：

1. 观察 (observation)：
   - 分析当前游戏环境和最新信息
   - 关注与你的目标相关的关键事件和线索
   - 思考其他角色的行为和可能的动机

2. 分析 (analysis)：
   - 当前形势对你的优劣势分析
   - 其他角色对你的态度评估
   - 可能存在的机会和威胁

3. 决策逻辑 (decision_logic)：
   - 考虑符合你性格的多种可能行动
   - 权衡各选项的风险和收益
   - 选择最符合你目标和性格的行动路线

4. 内心独白 (inner_monologue)：
   - 表达你真实的情绪和想法
   - 揭示你的担忧、希望或疑虑

5. 行动 (action)：
   - 清晰描述你决定采取的行动
   - 包括行动目标、方式和预期效果
   - 确保行动符合你的角色性格和动机

{model_instruction}

**特别注意：** 在 `internal_thoughts.other_players_assessment` 中，每个角色的 `attitude_toward_self` 字段，其值**必须**严格从以下选项中选择一个：'友好', '中立', '敌对', '未知'。请勿包含任何其他字符或解释。

注意：只有"action"部分会被其他人看到，其他部分只有你自己知道。
根据当前情境和角色性格来调整你的目标、计划、心情和行动。
你的回应必须包含上述五个部分，各部分应有明确的逻辑关联，展现角色的思考过程。
"""

def build_decision_user_prompt(
    game_state: GameState, 
    unread_messages: List[Message],
    character_id: str
) -> str:
    """
    构建玩家决策的用户提示
    
    Args:
        game_state: 游戏状态
        unread_messages: 未读消息列表
        character_id: 当前角色ID
        
    Returns:
        str: 用户提示文本
    """
    # 格式化未读消息
    formatted_messages = format_messages(unread_messages)
    
    # 获取角色当前状态
    character_status = game_state.character_states.get(character_id)
    current_location = game_state.location_states.get(character_status.location) if character_status else None
    
    # 获取最近的内部思考记录(如果有)
    recent_thoughts = game_state.character_internal_thoughts.get(character_id)
    if recent_thoughts: 
        latest_thought:InternalThoughts = recent_thoughts[-1]
        recent_thoughts = f"""
你的最近思考记录:
- 主要情绪: {latest_thought.primary_emotion}
- 短期目标: {', '.join(latest_thought.short_term_goals)}
- 感知的风险: {', '.join(latest_thought.perceived_risks)}
- 感知的机会: {', '.join(latest_thought.perceived_opportunities)}
"""
    
    return f"""
【第{game_state.round_number}回合】

你当前位置: {current_location.location_id if current_location else "未知"}
位置描述: {current_location.description_state if current_location else "无描述"}
场景中的其他角色: {', '.join(current_location.present_characters) if current_location and current_location.present_characters else "无"}

最近的信息:
{formatted_messages}

{recent_thoughts}

根据角色性格、背景故事和当前情境，思考并决定你的下一步行动。
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
