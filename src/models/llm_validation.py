"""
LLM输出验证模块，用于验证LLM输出的格式是否符合预期。
使用Pydantic的内置功能进行JSON验证和模式生成。
"""
import re
import json
from typing import TypeVar, Type, Dict, Any, Optional, Generic
from pydantic import BaseModel, ValidationError
import logging

# 获取日志记录器
logger = logging.getLogger(__name__)

# 定义泛型类型变量，表示任何Pydantic模型
T = TypeVar('T', bound=BaseModel)

class LLMOutputError(Exception):
    """LLM输出错误异常类"""
    def __init__(self, message: str, model_type: Type[BaseModel], raw_output: str, validation_errors: Optional[ValidationError] = None):
        self.message = message
        self.model_type = model_type
        self.raw_output = raw_output
        self.validation_errors = validation_errors
        super().__init__(message)


def _preprocess_json_string(json_str: str) -> str:
    """
    预处理JSON字符串，修复常见的LLM生成错误。
    
    Args:
        json_str: 原始JSON字符串
        
    Returns:
        str: 预处理后的JSON字符串
    """
    # 保存原始字符串以检测是否有变化
    original_str = json_str
    
    # 1. 移除对象末尾的逗号: ,} -> }
    json_str = re.sub(r",\s*}", "}", json_str)
    
    # 2. 移除数组末尾的逗号: ,] -> ]
    json_str = re.sub(r",\s*]", "]", json_str)
    
    # 3. 修复数组属性缺少逗号的问题
    # 例如: "type": "array" "options": [...] -> "type": "array", "options": [...]
    json_str = re.sub(r'"(type|[a-zA-Z_]+)":\s*"([^"]+)"\s+"([a-zA-Z_]+)":', 
                     r'"\1": "\2", "\3":', json_str)
    
    # 4. 修复属性之间缺少逗号的问题
    # 例如: "prop1": "value1" "prop2": "value2" -> "prop1": "value1", "prop2": "value2"
    json_str = re.sub(r'("[^"]+"\s*:\s*(?:"[^"]*"|true|false|\d+(?:\.\d+)?))\s+(")', r'\1, \2', json_str)
    
    # 5. 修复数组元素之间缺少逗号的问题
    # 例如: [{"id":1} {"id":2}] -> [{"id":1}, {"id":2}]
    json_str = re.sub(r'(}|"])\s+({"|\[)', r'\1, \2', json_str)
    
    if json_str != original_str:
        logger.debug("JSON string preprocessed to fix common formatting issues.")
    
    return json_str


def extract_json_from_llm_response(response: str) -> str:
    """
    严格从LLM响应中提取Markdown代码块内的JSON字符串。
    只接受被 ```json ... ``` 或 ``` ... ``` 包裹的内容。
    会对提取的内容进行预处理以修复常见的JSON格式错误。
    
    Args:
        response: LLM的原始响应文本
        
    Returns:
        str: 提取出的有效JSON字符串。如果找不到有效的Markdown代码块或块内不是有效JSON，
             则返回空字符串，这将导致后续的 json.loads 失败。
    """
    response_cleaned = response.strip()

    # 1. 尝试从Markdown代码块中提取JSON
    json_match_markdown = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_cleaned)
    if json_match_markdown:
        raw_json_str = json_match_markdown.group(1).strip()
        
        # 2. 应用预处理以修复所有可能的JSON格式错误
        preprocessed_json_str = _preprocess_json_string(raw_json_str)
        
        # 3. 尝试解析预处理后的JSON
        try:
            json.loads(preprocessed_json_str)  # 仅为验证有效性
            return preprocessed_json_str
        except json.JSONDecodeError as e:
            # 如果修复失败，记录错误信息并返回空字符串
            logger.warning(f"JSON解析错误({str(e)}): {raw_json_str[:100]}...")
            return ""
            
    # 4. 如果没有找到Markdown代码块，直接返回空字符串
    logger.warning("未在LLM响应中找到有效的JSON Markdown代码块。")
    return ""


class ModelValidator(Generic[T]):
    """
    模型验证器类，用于验证LLM输出
    """
    
    def __init__(self, model_class: Type[T]):
        """
        初始化验证器
        
        Args:
            model_class: 要验证的Pydantic模型类
        """
        self.model_class = model_class
    
    def get_prompt_instruction(self) -> str:
        """
        获取提示指令
        
        Returns:
            str: 提示指令文本
        """
        # 获取模型的JSON schema
        schema = self.model_class.model_json_schema()
        
        # 将schema转换为格式化的JSON字符串
        schema_json = json.dumps(schema, ensure_ascii=False, indent=2)
        
        # 修改后的 Prompt 指令
        prompt = f"""请严格按照以下 JSON Schema 格式返回响应。你的输出必须是一个单独的、有效的 JSON 对象，并被包裹在 ```json ... ``` 代码块中。
代码块内部 **只能** 包含 JSON 对象本身，**不得包含**任何其他文字、注释、标记（如 'json\\n'）或解释。

```json
{schema_json}
```

确保 JSON 包含所有必填字段，并且值符合定义的类型和约束。"""
        
        return prompt
    
    def validate_response(self, response: str) -> T:
        """
        验证响应
        
        Args:
            response: LLM响应文本
            
        Returns:
            T: 验证后的模型实例
            
        Raises:
            LLMOutputError: 当验证失败时抛出
        """
        # 提取JSON字符串 (已包含预处理步骤)
        json_str = extract_json_from_llm_response(response)
        
        if not json_str:
             raise LLMOutputError(
                "未能从LLM响应中提取有效的JSON内容。",
                self.model_class,
                response
            )

        # 尝试解析JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            # 如果解析失败，则抛出错误
            raise LLMOutputError(
                f"JSON解析错误: {str(e)}", 
                self.model_class, 
                response
            )
        
        # 验证数据结构
        try:
            # 直接使用Pydantic的model_validate方法进行验证（Pydantic v2）
            validated_model = self.model_class.model_validate(data)
            return validated_model
        except ValidationError as e:
            raise LLMOutputError(
                f"数据验证错误: {str(e)}", 
                self.model_class, 
                response, 
                e
            )


# 创建常用模型的验证器工厂函数
def create_validator_for(model_class: Type[T]) -> ModelValidator[T]:
    """
    为指定模型创建验证器
    
    Args:
        model_class: Pydantic模型类
        
    Returns:
        ModelValidator[T]: 模型验证器
    """
    return ModelValidator(model_class)
