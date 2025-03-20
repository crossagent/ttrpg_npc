"""
颜色工具模块，提供终端彩色输出功能
"""
from enum import Enum
from typing import Any

class Color(Enum):
    """终端颜色枚举"""
    GREEN = '\033[92m'  # 绿色 - DM和玩家的说话
    YELLOW = '\033[93m'  # 黄色 - 观察、状态变化、分析内容
    GRAY = '\033[90m'    # 灰色 - 每回合向agent输入的内容
    RESET = '\033[0m'    # 重置颜色
    BOLD = '\033[1m'     # 粗体
    UNDERLINE = '\033[4m'  # 下划线

def print_colored(text: str, color: Color, end: str = '\n') -> None:
    """
    打印彩色文本
    
    Args:
        text: 要打印的文本
        color: 颜色枚举
        end: 结束字符，默认为换行
    """
    print(f"{color.value}{text}{Color.RESET.value}", end=end)

def green_text(text: str) -> str:
    """
    返回绿色文本
    
    Args:
        text: 要着色的文本
        
    Returns:
        str: 着色后的文本
    """
    return f"{Color.GREEN.value}{text}{Color.RESET.value}"

def yellow_text(text: str) -> str:
    """
    返回黄色文本
    
    Args:
        text: 要着色的文本
        
    Returns:
        str: 着色后的文本
    """
    return f"{Color.YELLOW.value}{text}{Color.RESET.value}"

def gray_text(text: str) -> str:
    """
    返回灰色文本
    
    Args:
        text: 要着色的文本
        
    Returns:
        str: 着色后的文本
    """
    return f"{Color.GRAY.value}{text}{Color.RESET.value}"

def format_dm_message(name: str, content: str) -> str:
    """
    格式化DM消息
    
    Args:
        name: DM名称
        content: 消息内容
        
    Returns:
        str: 格式化后的消息
    """
    return green_text(f"{name}: {content}")

def format_player_message(name: str, content: str) -> str:
    """
    格式化玩家消息
    
    Args:
        name: 玩家名称
        content: 消息内容
        
    Returns:
        str: 格式化后的消息
    """
    return gray_text(f"{name}: {content}")

def format_observation(text: str) -> str:
    """
    格式化观察内容
    
    Args:
        text: 观察内容
        
    Returns:
        str: 格式化后的内容
    """
    return yellow_text(f"观察: {text}")

def format_state(goal: str, plan: str, mood: str, health: int) -> str:
    """
    格式化状态内容
    
    Args:
        goal: 目标
        plan: 计划
        mood: 心情
        health: 血量
        
    Returns:
        str: 格式化后的内容
    """
    return yellow_text(f"状态: 目标={goal}, 计划={plan}, 心情={mood}, 血量={health}")

def format_thinking(text: str) -> str:
    """
    格式化思考内容
    
    Args:
        text: 思考内容
        
    Returns:
        str: 格式化后的内容
    """
    return yellow_text(f"思考: {text}")
