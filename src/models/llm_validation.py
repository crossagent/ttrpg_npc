"""
LLM输出验证模块，用于验证LLM输出的格式是否符合预期。
使用Pydantic的内置功能进行JSON验证和模式生成。
"""
import re
import json
from typing import TypeVar, Type, Dict, Any, Optional, Generic
from pydantic import BaseModel, ValidationError

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


def extract_json_from_llm_response(response: str) -> str:
    """
    从LLM响应中提取JSON字符串。
    优先查找Markdown代码块，然后尝试查找独立的JSON对象或列表。
    
    Args:
        response: LLM的原始响应文本
        
    Returns:
        str: 提取出的JSON字符串，如果找不到则返回原始清理后的响应。
    """
    # 1. 尝试从Markdown代码块中提取JSON
    json_match_markdown = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
    if json_match_markdown:
        json_str = json_match_markdown.group(1).strip()
        # 尝试验证Markdown中的内容是否为有效JSON
        try:
            json.loads(json_str) # 尝试解析以确认有效性
            return json_str
        except json.JSONDecodeError:
            # 如果Markdown块内容无效，则忽略并继续尝试其他方法
            pass # 继续尝试下面的方法

    # 2. 如果没有找到有效的Markdown块，尝试查找独立的JSON对象 {...}
    json_match_object = re.search(r'({[\s\S]*})', response)
    if json_match_object:
        json_str = json_match_object.group(1).strip()
        try:
            # 尝试解析以确认找到的是一个有效的JSON对象
            # 这也有助于处理正则可能匹配到非JSON花括号的情况
            parsed_obj = json.loads(json_str)
            if isinstance(parsed_obj, dict): # 确保它是个对象
                 return json_str
        except json.JSONDecodeError:
            # 如果解析失败，说明可能不是完整的对象或无效JSON，继续尝试列表
            pass

    # 3. 如果没有找到有效的对象，尝试查找独立的JSON列表 [...]
    json_match_list = re.search(r'(\[[\s\S]*\])', response)
    if json_match_list:
        json_str = json_match_list.group(1).strip()
        try:
            # 尝试解析以确认找到的是一个有效的JSON列表
            parsed_list = json.loads(json_str)
            if isinstance(parsed_list, list): # 确保它是个列表
                return json_str
        except json.JSONDecodeError:
            # 如果解析失败，继续到最后一步
            pass

    # 4. 如果上述所有方法都失败，返回原始响应清理后的结果
    # 此时返回原始响应，让后续的 Pydantic 验证去处理错误
    return response.strip()


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
        
        # 构建提示文本
        prompt = f"""请以JSON格式返回符合以下模型的响应：

```json
{schema_json}
```

请确保你的响应是有效的JSON格式，并包含所有必填字段。"""
        
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
        # 提取JSON字符串
        json_str = extract_json_from_llm_response(response)
        
        # 尝试解析JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
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
