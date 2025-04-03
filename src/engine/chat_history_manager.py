import logging
from typing import List, Dict, Optional
from collections import defaultdict
import json
import os

from src.models.message_models import Message

class ChatHistoryManager:
    """
    管理游戏聊天记录，按回合存储和检索。
    独立于 GameState，便于状态快照和历史查询。
    """
    def __init__(self, save_path: Optional[str] = None):
        """
        初始化聊天记录管理器。

        Args:
            save_path: (可选) 保存聊天记录的文件路径。如果提供，将启用加载和保存功能。
        """
        self._history: Dict[int, List[Message]] = defaultdict(list)
        self.save_path = save_path
        self.logger = logging.getLogger(__name__)
        if self.save_path:
            self.load_history()

    def add_message(self, round_number: int, message: Message):
        """
        添加一条消息到指定回合的记录中。

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
        self.logger.debug(f"消息已添加到回合 {round_number}。来源: {message.source}, 类型: {message.type}")
        # Optionally save after adding each message or batch save later
        # self.save_history() 

    def get_messages(self, start_round: int, end_round: Optional[int] = None) -> List[Message]:
        """
        获取指定回合范围内的所有消息。

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
                
        self.logger.debug(f"获取到回合 {start_round}-{end_round} 的 {len(messages)} 条消息。")
        return messages

    def get_all_messages(self) -> List[Message]:
        """
        获取所有回合的所有消息。

        Returns:
            List[Message]: 所有消息列表，按回合和添加顺序排序。
        """
        all_messages: List[Message] = []
        sorted_rounds = sorted(self._history.keys())
        for round_num in sorted_rounds:
            all_messages.extend(self._history[round_num])
        self.logger.debug(f"获取到所有回合共 {len(all_messages)} 条消息。")
        return all_messages

    def get_latest_round_messages(self) -> List[Message]:
        """
        获取最近一个有消息的回合的所有消息。

        Returns:
            List[Message]: 最近回合的消息列表。
        """
        if not self._history:
            return []
        latest_round = max(self._history.keys())
        return self._history[latest_round]

    def save_history(self):
        """
        将当前聊天记录保存到文件（如果指定了 save_path）。
        """
        if not self.save_path:
            self.logger.debug("未指定保存路径，跳过保存聊天记录。")
            return

        try:
            # 将 Message 对象转换为字典列表以便 JSON 序列化
            serializable_history = {
                str(round_num): [msg.model_dump() for msg in messages]
                for round_num, messages in self._history.items()
            }
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
            with open(self.save_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_history, f, ensure_ascii=False, indent=4)
            self.logger.info(f"聊天记录已保存到: {self.save_path}")
        except Exception as e:
            self.logger.exception(f"保存聊天记录到 '{self.save_path}' 时出错: {e}")

    def load_history(self):
        """
        从文件加载聊天记录（如果指定了 save_path 且文件存在）。
        """
        if not self.save_path or not os.path.exists(self.save_path):
            self.logger.debug(f"未找到聊天记录文件或未指定路径，跳过加载: {self.save_path}")
            self._history = defaultdict(list) # Ensure it's reset if file not found
            return

        try:
            with open(self.save_path, 'r', encoding='utf-8') as f:
                serializable_history = json.load(f)
            
            loaded_history: Dict[int, List[Message]] = defaultdict(list)
            for round_str, msg_dicts in serializable_history.items():
                try:
                    round_num = int(round_str)
                    loaded_history[round_num] = [Message(**msg_dict) for msg_dict in msg_dicts]
                except ValueError:
                    self.logger.warning(f"加载聊天记录时跳过无效的回合键: '{round_str}'")
                except Exception as inner_e: # Catch errors during Message model parsing
                     self.logger.warning(f"加载回合 {round_str} 的消息时出错: {inner_e}. 跳过此回合。")

            self._history = loaded_history
            self.logger.info(f"聊天记录已从 '{self.save_path}' 加载。")
        except json.JSONDecodeError:
            self.logger.error(f"加载聊天记录失败：文件 '{self.save_path}' 格式错误。")
            self._history = defaultdict(list) # Reset on error
        except Exception as e:
            self.logger.exception(f"加载聊天记录从 '{self.save_path}' 时发生未知错误: {e}")
            self._history = defaultdict(list) # Reset on error

    def clear_history(self):
        """清空所有聊天记录。"""
        self._history = defaultdict(list)
        self.logger.info("聊天记录已清空。")
        # Optionally delete the save file
        # if self.save_path and os.path.exists(self.save_path):
        #     try:
        #         os.remove(self.save_path)
        #         self.logger.info(f"聊天记录保存文件已删除: {self.save_path}")
        #     except Exception as e:
        #         self.logger.error(f"删除聊天记录文件时出错: {e}")
