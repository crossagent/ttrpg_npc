# Tech Context: TTRPG NPC 模拟引擎

## 1. 主要语言

*   **Python**: 项目的主要开发语言。

## 2. 核心框架与库

*   **AutoGen**:
    *   `autogen-agentchat>=0.2.0`: 用于构建和协调多代理对话的核心库，可能用于管理玩家、NPC、叙事和裁判代理之间的交互。
    *   `autogen-core>=0.2.0`: AutoGen 框架的基础核心库。
    *   `autogen-ext[openai]>=0.2.0`: AutoGen 的 OpenAI 扩展，表明项目主要集成 OpenAI 的 LLM API。
*   **Pydantic**:
    *   `pydantic>=2.0.0`: 用于定义所有核心数据模型（如游戏状态、行动、消息、剧本结构等），提供类型检查和数据验证。
*   **PyYAML**:
    *   `pyyaml>=6.0.0`: 用于加载和解析 YAML 格式的配置文件（如 `config/game_config.yaml`, `config/llm_settings.yaml`）。

## 3. 数据格式

*   **YAML**: 用于项目配置。
*   **JSON**: 用于定义游戏剧本 (`scenarios/`)。

## 4. LLM 集成

*   **主要集成**: OpenAI API (通过 `autogen-ext[openai]`)。
*   **配置**: LLM 相关设置（如 API Key, 模型名称）存储在 `config/llm_settings.yaml` 中。

## 5. 开发与运行环境

*   **依赖管理**: 使用 `requirements.txt` 和 `pip` 进行包管理。
*   **运行方式**: 主要通过命令行界面 (`src/scripts/cli_runner.py`) 启动。
*   **环境**: 标准 Python 开发环境（可能使用 `venv`）。

## 6. 技术约束与考虑

*   项目强依赖于 AutoGen 框架进行代理管理和 LLM 交互。
*   数据模型的准确性和一致性依赖于 Pydantic。
*   游戏逻辑和剧本结构与所选用的数据格式 (JSON, YAML) 紧密相关。

*(此文件基于 requirements.txt, README.md, docs/重要模块设计.md 及项目结构生成)*
