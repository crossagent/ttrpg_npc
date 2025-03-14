# 导出配置加载函数
from src.config.config_loader import load_llm_settings, LLMSettings

# 预加载默认配置
default_llm_settings = load_llm_settings()
