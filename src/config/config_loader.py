import yaml
import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class LLMSettings(BaseModel):
    """大语言模型配置"""
    openai_api_key: str = Field(description="OpenAI API密钥")
    model: str = Field(description="使用的模型名称")
    temperature: float = Field(description="生成的随机性", default=0.7)
    base_url: Optional[str] = Field(description="API基础URL", default=None)
    
    # 可选配置
    langsmith_api_key: Optional[str] = Field(description="LangSmith API密钥", default="")
    prompt_name: Optional[str] = Field(description="从LangSmith拉取的prompt名称", default="story_prompt")
    history_length: int = Field(description="保留的历史记录长度", default=50)

def get_config_path(file_name: str) -> str:
    """
    获取配置文件的完整路径
    
    Args:
        file_name: 配置文件名
        
    Returns:
        str: 配置文件的完整路径
    """
    project_root = Path(__file__).parent.parent.parent
    return os.path.join(project_root, "config", file_name)

def load_llm_settings(config_path: Optional[str] = None) -> LLMSettings:
    """
    从YAML文件加载LLM设置
    
    Args:
        config_path: 配置文件路径，如果为None则使用默认路径
        
    Returns:
        LLMSettings: LLM配置对象
    """
    if config_path is None:
        config_path = get_config_path("llm_settings.yaml")
        
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config_data = yaml.safe_load(file)
            return LLMSettings(**config_data)
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        # 返回默认配置
        return LLMSettings(
            openai_api_key="",
            model="gpt-4o",
            temperature=0.7
        )

def load_config(config_name: str = "game_config.yaml") -> Dict[str, Any]:
    """
    加载游戏配置
    
    Args:
        config_name: 配置文件名，默认为game_config.yaml
        
    Returns:
        Dict[str, Any]: 加载的配置数据
    """
    config_path = get_config_path(config_name)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config_data = yaml.safe_load(file)
            return config_data
    except Exception as e:
        print(f"加载配置文件失败 {config_path}: {e}")
        return {}  # 返回空字典作为默认配置

def get_config_value(key: str, default: Any = None, config_name: str = "game_config.yaml") -> Any:
    """
    获取配置值
    
    Args:
        key: 配置键，使用点号分隔层级，例如"game.rules.default_difficulty"
        default: 如果配置不存在时返回的默认值
        config_name: 配置文件名
        
    Returns:
        Any: 配置值或默认值
    """
    config_data = load_config(config_name)
    
    # 使用点号分隔层级
    keys = key.split('.')
    value = config_data
    
    try:
        for k in keys:
            value = value[k]
        return value
    except (KeyError, TypeError):
        return default

# 导出函数和类
__all__ = ["LLMSettings", "load_llm_settings", "load_config", "get_config_value"]