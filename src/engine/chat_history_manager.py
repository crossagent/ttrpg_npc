import logging
from typing import List, Dict, Optional
from collections import defaultdict
import json
import os
from datetime import datetime # Import datetime

from src.models.message_models import Message
# +++ Import GameRecord +++
from src.models.game_state_models import GameRecord, GameState # Import GameState for type hint consistency if needed

class ChatHistoryManager:
    """
    管理游戏聊天记录，按回合存储和检索。
    与 GameRecord 文件交互以实现持久化。
    """
    # --- Modified __init__ ---
    def __init__(self):
        """
        初始化聊天记录管理器。
        管理器启动时为空，历史记录通过 load_history 加载。
        """
        self._history: Dict[int, List[Message]] = defaultdict(list)
        # self.save_path = save_path # Removed save_path
        self.logger = logging.getLogger(__name__)
        # Removed automatic loading from __init__
        # if self.save_path:
        #     self.load_history()

    def add_message(self, round_number: int, message: Message):
        """
        添加一条消息到指定回合的内存记录中。

        Args:
            round_number: 消息所属的回合数。
            message: 要添加的消息对象。
        """
        if not isinstance(round_number, int) or round_number < 0:
            self.logger.error(f"添加消息失败：无效的回合数 '{round_number}'。")
            return
        if not isinstance(message, Message):
            self.logger.error(f"添加消息失败：提供的对象不是有效的 Message 实例。")
            return

        self._history[round_number].append(message)
        self.logger.debug(f"消息已添加到内存回合 {round_number}。来源: {message.source}, 类型: {message.type}")
        # Saving is now handled externally at the end of the round

    def get_messages(self, start_round: int, end_round: Optional[int] = None) -> List[Message]:
        """
        获取内存中指定回合范围内的所有消息。

        Args:
            start_round: 开始回合数（包含）。
            end_round: 结束回合数（包含）。如果为 None，则只获取 start_round 的消息。

        Returns:
            List[Message]: 指定范围内的消息列表，按回合和添加顺序排序。
        """
        messages: List[Message] = []
        if end_round is None:
            end_round = start_round

        if start_round < 0 or end_round < start_round:
            self.logger.warning(f"获取消息失败：无效的回合范围 ({start_round}-{end_round})。")
            return []

        sorted_rounds = sorted(self._history.keys())

        for round_num in sorted_rounds:
            if start_round <= round_num <= end_round:
                messages.extend(self._history[round_num])

        self.logger.debug(f"从内存获取到回合 {start_round}-{end_round} 的 {len(messages)} 条消息。")
        return messages

    def get_all_messages(self) -> List[Message]:
        """
        获取内存中所有回合的所有消息。

        Returns:
            List[Message]: 所有消息列表，按回合和添加顺序排序。
        """
        all_messages: List[Message] = []
        sorted_rounds = sorted(self._history.keys())
        for round_num in sorted_rounds:
            all_messages.extend(self._history[round_num])
        self.logger.debug(f"从内存获取到所有回合共 {len(all_messages)} 条消息。")
        return all_messages

    def get_latest_round_messages(self) -> List[Message]:
        """
        获取内存中最近一个有消息的回合的所有消息。

        Returns:
            List[Message]: 最近回合的消息列表。
        """
        if not self._history:
            return []
        latest_round = max(self._history.keys())
        return self._history[latest_round]

    # --- Removed old save_history ---

    # --- Removed old load_history ---

    # +++ New save_history method +++
    def save_history(self, record_path: str, round_number: int, current_round_messages: List[Message]):
        """
        Updates the chat history in the specified GameRecord file with messages from the current round.
        Assumes the GameRecord file exists and has been potentially updated by GameStateManager already.

        Args:
            record_path: Path to the GameRecord JSON file.
            round_number: The round number these messages belong to.
            current_round_messages: List of Message objects for the current round.
        """
        if not os.path.exists(record_path):
            self.logger.error(f"保存聊天记录失败：记录文件未找到 '{record_path}'。GameStateManager 应先创建/更新此文件。")
            return

        try:
            # Load the existing record
            with open(record_path, 'r', encoding='utf-8') as f:
                record_data = json.load(f)
            record = GameRecord.model_validate(record_data)

            # Add/Update the chat history for the current round
            record.chat_history[round_number] = current_round_messages
            record.last_saved_at = datetime.now() # Update timestamp

            # Write the updated record back
            record_json = record.model_dump_json(indent=4)
            with open(record_path, 'w', encoding='utf-8') as f:
                f.write(record_json)

            self.logger.info(f"回合 {round_number} 的聊天记录 ({len(current_round_messages)} 条) 已更新到记录: {record_path}")

        except json.JSONDecodeError:
             self.logger.error(f"保存聊天记录失败：记录文件 '{record_path}' 格式错误。")
        except Exception as e:
            self.logger.exception(f"更新记录 '{record_path}' 中的聊天记录时出错: {e}")

    # +++ New load_history method +++
    def load_history(self, record_path: str, target_round: int) -> bool:
        """
        Loads chat history from a GameRecord file up to a specified round
        and initializes the internal history dictionary.

        Args:
            record_path: Path to the GameRecord JSON file.
            target_round: The maximum round number (inclusive) to load history for.

        Returns:
            bool: True if loading was successful, False otherwise.
        """
        if not os.path.exists(record_path):
            self.logger.error(f"加载聊天记录失败：记录文件未找到 '{record_path}'。")
            return False

        try:
            with open(record_path, 'r', encoding='utf-8') as f:
                record_data = json.load(f)
            record = GameRecord.model_validate(record_data)

            # Clear internal history before loading
            self.clear_history() # Use the existing clear method

            loaded_message_count = 0
            # Load history round by round up to the target round
            sorted_record_rounds = sorted(record.chat_history.keys())
            for round_num in sorted_record_rounds:
                if round_num <= target_round:
                    # Ensure messages are valid Message objects
                    try:
                        messages_for_round = [msg for msg in record.chat_history[round_num] if isinstance(msg, Message)]
                        # If they were loaded as dicts by Pydantic, re-validate (though model_validate should handle this)
                        # messages_for_round = [Message.model_validate(msg) if isinstance(msg, dict) else msg
                        #                       for msg in record.chat_history[round_num]]
                        self._history[round_num] = messages_for_round
                        loaded_message_count += len(messages_for_round)
                    except Exception as validation_error:
                         self.logger.warning(f"加载回合 {round_num} 的聊天记录时验证消息失败: {validation_error}。跳过此回合。")


            self.logger.info(f"已从记录 '{record_path}' 加载了到回合 {target_round} 为止的 {loaded_message_count} 条聊天记录。")
            return True

        except json.JSONDecodeError:
            self.logger.error(f"加载聊天记录失败：记录文件 '{record_path}' 格式错误。")
            self.clear_history() # Ensure history is cleared on error
            return False
        except Exception as e:
            self.logger.exception(f"从记录 '{record_path}' 加载聊天记录时发生错误: {e}")
            self.clear_history() # Ensure history is cleared on error
            return False


    def clear_history(self):
        """清空内存中的所有聊天记录。"""
        self._history = defaultdict(list)
        self.logger.info("内存聊天记录已清空。")
        # Saving/Deleting file is handled externally now
