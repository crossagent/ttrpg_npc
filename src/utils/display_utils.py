from typing import Tuple
from src.models.message_models import Message

def format_message_display_parts(message: Message) -> Tuple[str, str]:
    """
    根据消息内容，格式化用于显示的来源字符串和前缀。

    Args:
        message: 要格式化的消息对象。

    Returns:
        一个元组，包含 (格式化后的来源字符串, 前缀字符串)。
        例如: ("莫妮卡(chara_01)", "(行动) ") 或 ("DM", "")
    """
    source = message.source if hasattr(message, 'source') else "未知来源"
    source_id = message.source_id if hasattr(message, 'source_id') else None

    # 1. Determine source display (Name or Name(ID))
    source_display = source
    if source_id:
        # Only add ID if it's different from the name (typical for characters)
        # Exclude agent IDs like 'dm_agent', 'referee_agent', 'system'
        is_agent_id = source_id in ["dm_agent", "referee_agent", "system"] # Add more if needed
        # Also check if source is '裁判' which uses referee_agent id
        is_referee_source = source == "裁判"
        if source != source_id and not is_agent_id and not is_referee_source:
             source_display = f"{source}({source_id})"
        # Handle Referee specifically if needed (e.g., always show "裁判")
        elif is_referee_source:
             source_display = "裁判" # Keep source as "裁判" without ID

    # 2. Determine prefix based on the new MessageType
    prefix = ""
    # Assuming MessageType and SenderRole are imported or available in scope
    from src.models.message_models import MessageType, SenderRole # Ensure both are available

    if message.type == MessageType.ACTION_DECLARATION:
        prefix = "(行动) "
    elif message.type == MessageType.DIALOGUE:
        prefix = "(对话) "
    elif message.type == MessageType.WAIT_NOTIFICATION:
        prefix = "(等待) "
    # Add prefixes for other types if desired, e.g.:
    # elif message.type == MessageType.ACTION_RESULT_NARRATIVE:
    #     prefix = "(结果) "
    # elif message.type == MessageType.EVENT_NOTIFICATION:
    #     prefix = "(事件) "

    # No prefix for NARRATION, ACTION_RESULT_SYSTEM, SYSTEM_INFO, DICE_ROLL by default

    return source_display, prefix
