from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import TextMessage
import asyncio
from typing import Optional, List, Dict, Any

# 导入我们的游戏引擎
from src.engine.game_engine import GameEngine
from src.models.gameSchema import GameState

async def get_user_input() -> str:
    """
    获取命令行输入
    
    Returns:
        str: 用户输入的文本
    """
    return input("玩家输入 > ")

async def display_output(message: TextMessage) -> None:
    """
    将消息输出到终端
    
    Args:
        message: 要显示的消息
    """
    print(f"{message.source}: {message.content}")

async def main() -> None:
    """
    CLI入口，管理整个游戏流程
    """
    print("=== TTRPG NPC游戏系统启动 ===")
    print("这是一个最多5回合的简单游戏，包含一个只会数数的Agent")
    print("每回合Agent会给出一个比上回合大1的数字")
    print("你可以输入任何内容回应，游戏会继续\n")
    
    # 创建游戏引擎
    engine = GameEngine(max_rounds=5)
    
    try:
        # 启动游戏
        final_state = await engine.start_game()
        print("\n=== 游戏结束 ===")
        print(f"共进行了{final_state.round_number}回合")
        print(f"最终计数: {final_state.current_count}")
    except KeyboardInterrupt:
        print("\n游戏被用户中断")
    except Exception as e:
        print(f"\n游戏出错: {str(e)}")

if __name__ == "__main__":
    # 启动异步事件循环
    asyncio.run(main())
