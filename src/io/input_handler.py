# src/io/input_handler.py
import abc
from typing import List, Optional
import asyncio

from src.models.action_models import ActionOption

class UserInputHandler(abc.ABC):
    """
    用户输入处理器的抽象基类。
    定义了获取玩家行动选择的标准接口。
    """
    @abc.abstractmethod
    async def get_player_choice(
        self,
        options: List[ActionOption],
        character_name: str,
        character_id: str
    ) -> Optional[ActionOption]:
        """
        向玩家展示行动选项并获取其选择。

        Args:
            options: 可供选择的行动选项列表。
            character_name: 需要做选择的角色名称。
            character_id: 需要做选择的角色 ID。

        Returns:
            玩家选择的 ActionOption，如果无法获取选择则返回 None。
        """
        pass

class CliInputHandler(UserInputHandler):
    """
    命令行用户输入处理器。
    通过标准输入/输出来获取玩家选择。
    """
    async def get_player_choice(
        self,
        options: List[ActionOption],
        character_name: str,
        character_id: str
    ) -> Optional[ActionOption]:
        """
        在命令行中向玩家展示选项并获取其选择。
        """
        if not options:
            print(f"警告：角色 {character_name} ({character_id}) 没有可用的行动选项。")
            return None

        print(f"\n轮到 {character_name} ({character_id}) 行动了，请选择一个选项：")
        for idx, option in enumerate(options):
            print(f"  {idx + 1}. [{option.action_type.name}] {option.content} (目标: {option.target or '无'})")

        while True:
            try:
                # 使用 asyncio.to_thread 运行同步的 input()，避免阻塞事件循环
                choice_str = await asyncio.to_thread(input, f"请输入选项编号 (1-{len(options)}): ")
                choice_idx = int(choice_str) - 1
                if 0 <= choice_idx < len(options):
                    return options[choice_idx]
                else:
                    print(f"无效的选项编号，请输入 1 到 {len(options)} 之间的数字。")
            except ValueError:
                print("无效的输入，请输入数字。")
            except EOFError:
                print("\n输入流结束，无法获取选择。")
                return None # 或者选择一个默认行为
            except Exception as e:
                print(f"获取输入时发生错误: {e}")
                return None # 或者选择一个默认行为

# 可以在这里添加 WebInputHandler 的占位符或实现
# class WebInputHandler(UserInputHandler):
#     async def get_player_choice(self, options: List[ActionOption], character_name: str, character_id: str) -> Optional[ActionOption]:
#         # Web 实现将涉及 WebSocket 或其他通信机制
#         print("WebInputHandler 尚未实现。")
#         return None
