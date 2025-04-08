"""
玩家上下文构建模块，负责构建玩家Agent所需的各类上下文文本。
"""
import logging # +++ Add logging import +++
from typing import List, Dict, Any, Optional
# +++ 添加 CharacterInstance 导入 +++
from src.models.game_state_models import GameState, CharacterInstance
from src.models.message_models import Message
from src.engine.scenario_manager import ScenarioManager # Import ScenarioManager
from src.engine.chat_history_manager import ChatHistoryManager # +++ Add ChatHistoryManager import +++
from src.context.context_utils import format_messages
# +++ 添加 RelationshipImpactAssessment 导入 +++
from src.models.action_models import RelationshipImpactAssessment
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

5. 行动 (action) 与 微小动作 (minor_action):
   - **如果 `action_type` 是 "主要行动" (ACTION):** 在 `action` 字段中清晰描述你决定采取的行动，包括目标、方式和预期效果。`minor_action` 字段应为 `null`。
   - **如果 `action_type` 是 "讨论沟通" (TALK):**
     - 在 `action` 字段中 **直接输出** 你要说的对话内容，不要添加任何描述性语句（例如，不要写“我说：‘你好’”或“我走向他并说：‘你好’”）。
     - （可选）在 `minor_action` 字段中，用简短的文字描述一个伴随对话的、非交互性的微小动作（例如：“叹了口气”、“撩了一下头发”、“揉了揉眼睛”）。如果无此动作，则 `minor_action` 字段为 `null`。
   - **如果 `action_type` 是 "继续旁观" (WAIT):** `action` 字段应简述你的状态（如“继续观察”），`minor_action` 字段应为 `null`。
   - 确保行动符合你的角色性格和动机。

{model_instruction}

**重要输出格式说明：**
- 你的回应必须是一个包含 `observation`, `internal_thoughts`, `action`, `action_type`, `target`, `minor_action` 字段的 JSON 对象。
- `internal_thoughts` 必须是一个包含 `short_term_goals`, `primary_emotion`, `psychological_state`, `narrative_analysis`, `other_players_assessment`, `perceived_risks`, `perceived_opportunities` 字段的嵌套 JSON 对象。
- 在 `internal_thoughts.other_players_assessment` 中，每个角色的 `attitude_toward_self` 字段的值**必须**严格从以下选项中选择一个：'友好', '中立', '敌对', '未知'。
- `minor_action` 字段**必须**包含在输出中，即使其值为 `null`。

注意：只有 `action` 和 `minor_action` 部分会被其他人看到，其他部分只有你自己知道。
根据当前情境和角色性格来调整你的目标、计划、心情和行动。
你的回应必须包含上述所有必需的字段，各部分应有明确的逻辑关联，展现角色的思考过程。
"""

def build_decision_user_prompt(
    game_state: GameState,
    scenario_manager: ScenarioManager, # Add scenario_manager parameter
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
    
    # 获取角色当前状态和位置
    character_instance = game_state.characters.get(character_id)
    if not character_instance:
        return "错误：无法找到角色信息"
        
    current_location_id = character_instance.location
    
    # 从 ScenarioManager 获取位置信息
    location_desc = "无描述"
    current_location = scenario_manager.get_location_info(current_location_id)
    if current_location:
        location_desc = current_location.description
    
    # 获取同一位置的其他角色
    other_characters = []
    for char_id, char in game_state.characters.items():
        if char_id != character_id and char.location == current_location_id:
            other_characters.append(char.name)
    
    other_chars_text = ", ".join(other_characters) if other_characters else "无"
    
    # 获取最近的内部思考记录(如果有)
    recent_thoughts_text = ""
    if hasattr(game_state, 'character_internal_thoughts') and isinstance(game_state.character_internal_thoughts, dict):
        recent_thoughts = game_state.character_internal_thoughts.get(character_id)
        if recent_thoughts and isinstance(recent_thoughts, list) and recent_thoughts: 
            latest_thought = recent_thoughts[-1]
            recent_thoughts_text = f"""
你的最近思考记录:
- 主要情绪: {latest_thought.primary_emotion}
- 短期目标: {', '.join(latest_thought.short_term_goals)}
- 感知的风险: {', '.join(latest_thought.perceived_risks)}
- 感知的机会: {', '.join(latest_thought.perceived_opportunities)}
"""
    
    return f"""
【第{game_state.round_number}回合】

你当前位置: {current_location_id if current_location_id else "未知"}
位置描述: {location_desc}
场景中的其他角色: {other_chars_text}
你的健康状态: {character_instance.health}
你的物品: {', '.join([item.name for item in character_instance.items]) if character_instance.items else "无"}

最近的信息:
{formatted_messages}

{recent_thoughts_text}

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


# +++ 新增：关系评估 Prompt 构建函数 +++

def build_relationship_assessment_system_prompt() -> str:
    """
    构建关系影响评估的系统提示。
    指示 LLM (扮演 NPC 自身) 评估互动并输出结构化 JSON。
    """
    # 获取 RelationshipImpactAssessment 的 Pydantic 模型验证器和指令
    # 需要确保 RelationshipImpactAssessment 和 create_validator_for 已导入
    try:
        validator = create_validator_for(RelationshipImpactAssessment)
        model_instruction = validator.get_prompt_instruction()
    except NameError: # Fallback if imports are missing (should not happen ideally)
        model_instruction = """请确保你的输出是一个有效的 JSON 对象，包含以下字段：
- interaction_type: 字符串，必须是 "positive_match", "negative_clash", 或 "neutral" 中的一个。
- intensity: 字符串，必须是 "low", "medium", 或 "high" 中的一个。
- reason: 字符串，解释你判断的理由。
- suggested_change: 整数，建议的关系值变化量。"""
        print("警告：无法创建 RelationshipImpactAssessment 验证器，使用备用指令。请检查导入。")


    return f"""你正在扮演一个角色，需要评估另一个人（通常是玩家）刚刚对你进行的互动（行动或对话）。
你需要根据你自己的性格、价值观、好恶以及当前你对这个人的整体好感度，来判断这次互动对你与他/她关系的影响。

你的内在设定包括：
- 核心价值观 (values): 你认为重要且指导你行为的原则。
- 喜好 (likes): 你喜欢的事物、行为或话题。
- 厌恶 (dislikes): 你反感的事物、行为或话题。
- 性格总结 (personality_summary): 对你核心性格的简要描述。
- 当前关系值 (relationship_player): 一个从 -100 (极度厌恶) 到 +100 (极度亲近) 的数值，代表你对互动者的整体好感度。

评估步骤：
1.  **理解互动**: 分析互动内容（行动描述或对话）。
2.  **对照内在设定**: 判断互动内容是否符合或违背了你的价值观、喜好或厌恶点？是否与你的性格总结相符？
3.  **考虑当前关系**: 当前的好感度会影响你对互动的解读吗？（例如，好感度高时可能更容易原谅小冒犯，好感度低时可能更容易产生负面解读）。
4.  **判断影响类型**: 确定互动是正面匹配 (positive_match)、负面冲突 (negative_clash) 还是中立 (neutral)。
5.  **判断影响强度**: 评估这种匹配或冲突的程度是低 (low)、中 (medium) 还是高 (high)。
6.  **给出理由**: 简要解释你做出判断的原因，必须联系你的内在设定或当前关系。
7.  **建议变化值**: 根据影响类型和强度，给出一个具体的关系值变化建议（整数，例如 +10, -5, 0）。

{model_instruction}

请严格按照 JSON 格式输出你的评估结果。
"""

def build_relationship_assessment_user_prompt(
    interacting_actor_instance: CharacterInstance, # 发起互动者
    self_char_info: ScenarioCharacterInfo,         # 自己的静态信息
    self_char_instance: CharacterInstance,          # 自己的运行时状态
    interaction_content: str,                     # 互动内容
    game_state: GameState                         # 游戏状态 (提供情境)
) -> str:
    """
    构建关系影响评估的用户提示。
    提供 LLM (扮演 NPC 自身) 进行评估所需的上下文。
    """
    # 提取自己的内在设定信息
    values_str = ", ".join(self_char_info.values) if self_char_info.values else "未定义"
    likes_str = ", ".join(self_char_info.likes) if self_char_info.likes else "未定义"
    dislikes_str = ", ".join(self_char_info.dislikes) if self_char_info.dislikes else "未定义"
    personality_summary_str = self_char_info.personality_summary if self_char_info.personality_summary else "未定义"
    current_relationship = self_char_instance.relationship_player

    # 简要情境 (可选，可以根据需要添加更多游戏状态信息)
    current_location_id = self_char_instance.location
    # Safely access location description
    location_desc = "未知地点"
    if current_location_id and game_state.location_states and current_location_id in game_state.location_states:
         location_state = game_state.location_states[current_location_id]
         # Try to get description from state first, then fallback to scenario manager if needed
         location_desc = location_state.description_state if location_state.description_state else "未知地点状态"
         # Example fallback (requires scenario_manager to be passed or accessible):
         # if not location_desc or location_desc == "未知地点状态":
         #     loc_info = scenario_manager.get_location_info(current_location_id)
         #     location_desc = loc_info.description if loc_info else "未知地点"

    context_summary = f"当前情境：你在 {location_desc}。" # 可以扩展

    return f"""
【评估互动影响】

你的身份: {self_char_info.name} ({self_char_info.public_identity})
你的内在设定:
- 核心价值观: {values_str}
- 喜好: {likes_str}
- 厌恶: {dislikes_str}
- 性格总结: {personality_summary_str}

互动发起者: {interacting_actor_instance.name} ({interacting_actor_instance.public_identity})
你当前对 {interacting_actor_instance.name} 的好感度: {current_relationship} (-100 到 +100)

互动内容:
"{interaction_content}"

{context_summary}

    请根据你的内在设定和当前好感度，评估这次互动对你与 {interacting_actor_instance.name} 关系的影响。
"""


# +++ 新增：目标生成 Prompt 构建函数 +++

def build_goal_generation_system_prompt(charaInfo: ScenarioCharacterInfo) -> str:
    """
    构建目标生成的系统提示。
    指示 LLM (扮演 NPC 自身) 基于长期目标、当前状态和情境生成短期目标。
    """
    # TODO: Refine this prompt based on desired goal generation behavior
    return f"""你正在扮演角色 {charaInfo.name} ({charaInfo.public_identity})。
你的长期目标是：{charaInfo.secret_goal if charaInfo.secret_goal else '未明确'}
你的背景：{charaInfo.background}
你的性格特点：{charaInfo.personality_summary if charaInfo.personality_summary else '未明确'}
你的核心价值观：{', '.join(charaInfo.values) if charaInfo.values else '未明确'}
你的喜好：{', '.join(charaInfo.likes) if charaInfo.likes else '未明确'}
你的厌恶：{', '.join(charaInfo.dislikes) if charaInfo.dislikes else '未明确'}

当前你因为没有明确的短期计划或之前的计划不可行而进入了思考状态。
你需要根据你的长期目标、性格、价值观以及当前的游戏情境，生成 1-3 个具体的、可在接下来一两个回合内尝试执行的短期目标。

重要要求：
- 目标应该是具体的行动步骤，而不是模糊的意图。
- 目标应该与你的长期目标和角色设定相关。
- 考虑当前环境、在场人物和最近发生的事件。
- 每个目标占一行，直接输出目标文本，不要添加序号或其他标记。

示例输出格式：
找到维克多的办公室钥匙
向瑞秋打听卡特最近的行踪
检查吧台下面是否有隐藏的开关
"""

def build_goal_generation_user_prompt(
    game_state: GameState,
    scenario_manager: ScenarioManager,
    chat_history_manager: "ChatHistoryManager", # Forward reference if needed
    character_id: str
) -> str:
    """
    构建目标生成的用户提示。
    提供 LLM (扮演 NPC 自身) 进行规划所需的上下文。
    """
    # 获取角色实例和静态信息
    character_instance = game_state.characters.get(character_id)
    character_info = scenario_manager.get_character_info(character_id)
    if not character_instance or not character_info:
        return "错误：无法获取角色信息，无法生成目标。"

    # 获取当前位置信息
    current_location_id = character_instance.location
    location_desc = "未知地点"
    current_location = scenario_manager.get_location_info(current_location_id)
    if current_location:
        location_desc = current_location.description

    # 获取同一位置的其他角色
    other_characters = []
    for char_id, char in game_state.characters.items():
        if char_id != character_id and char.location == current_location_id:
            # 获取更详细的信息，例如状态或与自己的关系
            other_char_info = scenario_manager.get_character_info(char_id)
            other_char_desc = f"{char.name} ({other_char_info.public_identity if other_char_info else '未知身份'})"
            if char.status:
                 other_char_desc += f" [状态: {char.status}]"
            # 可以考虑添加关系值，如果需要的话
            # rel_value = character_instance.relationships.get(char_id, 0) # Assuming relationships dict exists
            # other_char_desc += f" [关系: {rel_value}]"
            other_characters.append(other_char_desc)

    other_chars_text = "\n  - ".join(other_characters) if other_characters else "无"

    # 获取最近的聊天记录 (示例：最近2轮)
    try:
        recent_history = chat_history_manager.get_messages(
            start_round=max(0, game_state.round_number - 2) # Example: last 2 rounds
            # Removed limit=10 argument as it's not supported by the method
        )
        history_text = format_messages(recent_history) # Use existing formatter
    except Exception as hist_err:
        logging.warning(f"目标生成：获取聊天记录时出错: {hist_err}。")
        history_text = "无法获取最近的对话记录。"

    # 获取角色当前状态和关键记忆 (如果存在)
    status_text = f"你当前的状态是：{character_instance.status if character_instance.status else '正常'}"
    memories_text = "关键记忆：\n  - " + "\n  - ".join(character_instance.key_memories) if character_instance.key_memories else "无关键记忆"

    return f"""
【深度思考：规划短期目标】

当前回合: {game_state.round_number}
你当前位置: {current_location_id} ({location_desc})
当前在场角色:
  - {other_chars_text}

你的状态: {status_text}
{memories_text}
你的长期目标: {character_info.secret_goal if character_info.secret_goal else '未明确'}

最近的对话/事件回顾:
{history_text}

基于以上信息，特别是你的长期目标、当前状态、记忆和周围环境，请生成 1-3 个具体的短期目标，供你在接下来的一两个回合尝试执行。
请直接输出目标列表，每个目标占一行。
"""
