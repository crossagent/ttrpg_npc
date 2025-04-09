# src/io/input_handler.py
import abc
from typing import List, Optional
import asyncio
import re # Import re for dice validation

from src.models.action_models import ActionOption

class UserInputHandler(abc.ABC):
    """
    用户输入处理器的抽象基类。
    定义了获取玩家行动选择和投骰结果的标准接口。
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

    @abc.abstractmethod
    async def get_dice_roll_input(
        self,
        character_name: str,
        character_id: str,
        dice_type: str,
        reason: str
    ) -> Optional[int]:
        """
        提示玩家进行投骰并获取结果。

        Args:
            character_name: 需要投骰的角色名称。
            character_id: 需要投骰的角色 ID。
            dice_type: 需要投掷的骰子类型 (例如 "d20", "d6")。
            reason: 投骰的原因或目的。

        Returns:
            玩家输入的投骰结果 (int)，如果无法获取则返回 None。
        """
        pass

class CliInputHandler(UserInputHandler):
    """
    命令行用户输入处理器。
    通过标准输入/输出来获取玩家选择和投骰结果。
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

    async def get_dice_roll_input(
        self,
        character_name: str,
        character_id: str,
        dice_type: str,
        reason: str
    ) -> Optional[int]:
        """
        在命令行中提示玩家进行投骰并获取结果。
        """
        # 解析骰子类型以确定有效范围
        max_roll = 20 # Default
        match = re.match(r'd(\d+)', dice_type.lower())
        if match:
            num_sides = int(match.group(1))
            if num_sides > 0:
                max_roll = num_sides
            else:
                print(f"警告：无效的骰子类型 '{dice_type}'，将使用 d20 的范围。")
                dice_type = "d20"
                max_roll = 20
        else:
            print(f"警告：无法解析的骰子类型 '{dice_type}'，将使用 d20 的范围。")
            dice_type = "d20"
            max_roll = 20

        print(f"\n角色 {character_name} ({character_id}) 需要进行一次 {dice_type} 检定。")
        print(f"原因: {reason}")

        while True:
            try:
                # 使用 asyncio.to_thread 运行同步的 input()
                roll_str = await asyncio.to_thread(input, f"请输入你的 {dice_type} 投骰结果 (1-{max_roll}): ")
                roll_value = int(roll_str)
                if 1 <= roll_value <= max_roll:
                    return roll_value
                else:
                    print(f"无效的投骰结果，请输入 1 到 {max_roll} 之间的数字。")
            except ValueError:
                print("无效的输入，请输入一个整数。")
            except EOFError:
                print("\n输入流结束，无法获取投骰结果。")
                return None
            except Exception as e:
                print(f"获取投骰结果时发生错误: {e}")
                return None

# 可以在这里添加 WebInputHandler 的占位符或实现
# class WebInputHandler(UserInputHandler):
#     async def get_player_choice(self, options: List[ActionOption], character_name: str, character_id: str) -> Optional[ActionOption]:
#         # Web 实现将涉及 WebSocket 或其他通信机制
#         print("WebInputHandler 尚未实现。")
#         return None
