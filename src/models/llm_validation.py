"""
LLM输出验证模块，用于验证LLM输出的格式是否符合预期。
"""
import re
import json
from typing import TypeVar, Type, Dict, Any, Optional, Union, List, Tuple, Generic, get_type_hints, get_origin, get_args
from pydantic import BaseModel, ValidationError, create_model, Field
import inspect
from enum import Enum

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
    从LLM响应中提取JSON字符串
    
    Args:
        response: LLM的原始响应文本
        
    Returns:
        str: 提取出的JSON字符串
    """
    # 尝试从Markdown代码块中提取JSON
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
    if json_match:
        return json_match.group(1).strip()
    
    # 如果没有Markdown代码块，尝试查找JSON对象
    json_match = re.search(r'({[\s\S]*})', response)
    if json_match:
        return json_match.group(1).strip()
    
    # 如果上述方法都失败，返回原始响应
    return response.strip()


def parse_and_validate_llm_output(response: str, model_class: Type[T]) -> Tuple[T, Dict[str, Any]]:
    """
    解析并验证LLM输出，确保其符合指定的Pydantic模型
    
    Args:
        response: LLM的原始响应文本
        model_class: 用于验证的Pydantic模型类
        
    Returns:
        Tuple[T, Dict[str, Any]]: 验证后的模型实例和原始解析的JSON数据
        
    Raises:
        LLMOutputError: 当解析或验证失败时抛出
    """
    # 提取JSON字符串
    json_str = extract_json_from_llm_response(response)
    
    # 尝试解析JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise LLMOutputError(
            f"JSON解析错误: {str(e)}", 
            model_class, 
            response
        )
    
    # 验证数据结构
    try:
        validated_model = model_class.parse_obj(data)
        return validated_model, data
    except ValidationError as e:
        raise LLMOutputError(
            f"数据验证错误: {str(e)}", 
            model_class, 
            response, 
            e
        )


def generate_model_schema_example(model_class: Type[BaseModel]) -> Dict[str, Any]:
    """
    生成模型的示例JSON模式
    
    Args:
        model_class: Pydantic模型类
        
    Returns:
        Dict[str, Any]: 示例JSON模式
    """
    schema = model_class.schema()
    example = {}
    
    # 处理模型的每个字段
    for field_name, field_info in schema.get("properties", {}).items():
        # 获取字段类型
        field_type = field_info.get("type")
        
        # 处理不同类型的字段
        if field_type == "string":
            if "enum" in field_info:
                # 如果是枚举类型，使用第一个枚举值
                example[field_name] = field_info["enum"][0]
            else:
                # 普通字符串，使用字段描述或默认值
                example[field_name] = f"示例{field_info.get('description', field_name)}"
        
        elif field_type == "integer" or field_type == "number":
            example[field_name] = 0
        
        elif field_type == "boolean":
            example[field_name] = True
        
        elif field_type == "array":
            # 数组类型，创建一个包含一个元素的数组
            items_type = field_info.get("items", {}).get("type")
            if items_type == "string":
                example[field_name] = ["示例项"]
            elif items_type == "integer" or items_type == "number":
                example[field_name] = [0]
            elif items_type == "object":
                # 如果数组元素是对象，递归处理
                ref = field_info.get("items", {}).get("$ref")
                if ref:
                    # 从引用中提取模型名称
                    model_name = ref.split("/")[-1]
                    # 这里需要进一步处理，但简化起见，使用空对象
                    example[field_name] = [{}]
                else:
                    example[field_name] = [{}]
            else:
                example[field_name] = []
        
        elif field_type == "object":
            # 对象类型，使用空对象
            example[field_name] = {}
        
        elif field_type is None and "anyOf" in field_info:
            # 处理Union类型
            any_of = field_info["anyOf"]
            if any_of and len(any_of) > 0:
                first_type = any_of[0].get("type")
                if first_type == "string":
                    example[field_name] = "示例值"
                elif first_type == "array":
                    example[field_name] = []
                else:
                    example[field_name] = None
            else:
                example[field_name] = None
        
        else:
            # 其他类型，使用None
            example[field_name] = None
    
    return example


def generate_model_prompt_example(model_class: Type[BaseModel]) -> str:
    """
    生成用于提示的模型示例JSON字符串
    
    Args:
        model_class: Pydantic模型类
        
    Returns:
        str: 格式化的JSON示例字符串
    """
    example = generate_model_schema_example(model_class)
    return json.dumps(example, ensure_ascii=False, indent=2)


def generate_model_field_descriptions(model_class: Type[BaseModel]) -> str:
    """
    生成模型字段的描述文本，用于提示
    
    Args:
        model_class: Pydantic模型类
        
    Returns:
        str: 字段描述文本
    """
    schema = model_class.schema()
    descriptions = []
    
    # 添加模型描述
    if "description" in schema and schema["description"]:
        descriptions.append(f"{schema['title'] if 'title' in schema else model_class.__name__}: {schema['description']}")
    
    # 处理每个字段
    for field_name, field_info in schema.get("properties", {}).items():
        field_type = field_info.get("type", "未知类型")
        
        # 处理枚举类型
        if "enum" in field_info:
            enum_values = ", ".join([f'"{v}"' for v in field_info["enum"]])
            field_type = f"枚举 [{enum_values}]"
        
        # 处理数组类型
        elif field_type == "array":
            items_type = field_info.get("items", {}).get("type", "任意类型")
            field_type = f"数组[{items_type}]"
        
        # 处理Union类型
        elif field_type is None and "anyOf" in field_info:
            types = []
            for type_info in field_info["anyOf"]:
                if "type" in type_info:
                    types.append(type_info["type"])
                elif "$ref" in type_info:
                    types.append(type_info["$ref"].split("/")[-1])
            field_type = f"Union[{', '.join(types)}]"
        
        # 获取字段描述
        description = field_info.get("description", "")
        
        # 检查是否是必填字段
        required = field_name in schema.get("required", [])
        required_str = "（必填）" if required else "（可选）"
        
        # 添加字段描述
        descriptions.append(f"- {field_name}: {field_type} {required_str} - {description}")
    
    return "\n".join(descriptions)


def create_validation_function(model_class: Type[T]) -> callable:
    """
    为指定的模型类创建验证函数
    
    Args:
        model_class: 要验证的Pydantic模型类
        
    Returns:
        callable: 验证函数
    """
    def validate_function(response: str) -> T:
        """
        验证LLM响应是否符合指定模型
        
        Args:
            response: LLM响应文本
            
        Returns:
            T: 验证后的模型实例
            
        Raises:
            LLMOutputError: 当验证失败时抛出
        """
        validated_model, _ = parse_and_validate_llm_output(response, model_class)
        return validated_model
    
    # 设置函数名称和文档
    validate_function.__name__ = f"validate_{model_class.__name__}"
    validate_function.__doc__ = f"验证LLM响应是否符合{model_class.__name__}模型"
    
    return validate_function


def generate_prompt_instruction(model_class: Type[BaseModel]) -> str:
    """
    生成用于LLM提示的指令文本
    
    Args:
        model_class: Pydantic模型类
        
    Returns:
        str: 提示指令文本
    """
    # 获取模型名称
    model_name = model_class.__name__
    
    # 获取字段描述
    field_descriptions = generate_model_field_descriptions(model_class)
    
    # 生成示例
    example = generate_model_prompt_example(model_class)
    
    # 构建提示文本
    prompt = f"""请以JSON格式返回符合{model_name}模型的响应。

模型字段说明：
{field_descriptions}

示例格式：
```json
{example}
```

请确保你的响应是有效的JSON格式，并包含所有必填字段。"""
    
    return prompt


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
        self.validate = create_validation_function(model_class)
        self.prompt_instruction = generate_prompt_instruction(model_class)
    
    def get_prompt_instruction(self) -> str:
        """
        获取提示指令
        
        Returns:
            str: 提示指令文本
        """
        return self.prompt_instruction
    
    def validate_response(self, response: str) -> T:
        """
        验证响应
        
        Args:
            response: LLM响应文本
            
        Returns:
            T: 验证后的模型实例
        """
        return self.validate(response)


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
