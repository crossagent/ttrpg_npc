import yaml
from pydantic import BaseModel, Field
from typing import Optional

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

def load_llm_settings(config_path: str = "config/llm_settings.yaml") -> LLMSettings:
    """
    从YAML文件加载LLM设置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        LLMSettings: LLM配置对象
    """
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
