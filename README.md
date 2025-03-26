# TTRPG NPC 模拟引擎

本项目是一个基于 Python 的桌上角色扮演游戏（TTRPG）模拟引擎，利用大型语言模型（LLM）来驱动地下城主（DM）和玩家角色（PC）的行为，实现动态的游戏叙事和交互。

## 主要特性

*   **LLM 驱动**: 深度集成 LLM，用于生成叙事、处理行动、驱动决策。
*   **模块化设计**: 清晰的模块划分，易于理解和扩展。
*   **Pydantic 模型**: 使用 Pydantic 定义所有核心数据结构，保证类型安全和数据一致性。
*   **剧本驱动**: 通过 JSON 文件定义游戏场景和故事结构。
*   **回合制流程**: 模拟经典 TTRPG 的回合制游戏玩法。

## 模块结构 (`src/`)

项目核心代码位于 `src` 目录下，主要模块包括：

*   **`agents/`**: 定义了游戏中的代理（Agent）。
    *   `BaseAgent`: 所有代理的基类，提供通用功能（消息处理、上下文管理等）。
    *   `DMAgent`: 地下城主代理，负责生成叙事和处理玩家行动。
    *   `PlayerAgent`: 玩家代理，负责根据当前状态和角色信息决定行动。
*   **`engine/`**: 包含游戏的核心引擎逻辑。
    *   `GameEngine`: 游戏主引擎，负责启动和管理整个游戏流程。
    *   `GameStateManager`: 负责管理和更新游戏状态 (`GameState`)。
    *   `RoundManager`: 控制游戏的回合流程，协调 DM 和玩家的回合。
    *   `ScenarioManager`: 负责加载、解析和提供剧本 (`Scenario`) 数据。
    *   `AgentManager`: 管理游戏中的所有代理实例。
*   **`models/`**: 使用 Pydantic 定义了项目中的所有核心数据结构。
    *   `GameState`: 游戏状态的核心模型。
    *   `Scenario`: 游戏剧本的数据结构。
    *   `PlayerAction`, `ActionResult`: 定义玩家行动及其结果。
    *   `Message`: 游戏中的消息模型。
    *   `Context Models`: 用于构建 LLM 输入上下文的模型。
    *   `LLM Validation`: 用于验证 LLM 输出的模型和工具。
*   **`context/`**: 负责构建与 LLM 交互所需的上下文（Prompt）。
    *   `context_utils.py`: 提供格式化游戏状态信息的工具函数。
    *   `dm_context_builder.py`: 构建 DM 代理所需的提示。
    *   `player_context_builder.py`: 构建玩家代理所需的提示。
*   **`config/`**: 处理配置加载和格式化输出。
    *   `config_loader.py`: 加载 `config/` 目录下的 YAML 配置文件（如 `game_config.yaml`, `llm_settings.yaml`）。
    *   `color_utils.py`: 提供控制台彩色输出和格式化功能。
*   **`scripts/`**: 包含运行项目的入口脚本。
    *   `cli_runner.py`: 命令行界面运行入口。
    *   `web_runner.py`: (推测) 可能的 Web 界面运行入口。
*   **`communication/`**: (推测) 可能处理代理间或系统与代理间的消息分发。
*   **`utils/`**: 包含一些通用的工具函数。

## 游戏流程（业务流转）

游戏以回合制方式进行，基本流程如下：

1.  **初始化**:
    *   `ScenarioManager` 加载指定的剧本文件 (`scenarios/*.json`)。
    *   `GameStateManager` 根据剧本初始化 `GameState`（包括角色、地点、事件、初始环境等）。
    *   `AgentManager` 根据剧本中的角色信息创建并注册 `DMAgent` 和 `PlayerAgent` 实例。
2.  **回合开始 (`RoundManager`)**:
    *   标记新回合开始。
3.  **DM 回合**:
    *   `DMAgent` (通过 `dm_context_builder` 构建提示并调用 LLM) 根据当前 `GameState` 生成环境描述、事件触发或故事进展的叙事 (`Message`)。
    *   叙事消息被添加到 `GameState` 中。
4.  **玩家回合**:
    *   对于每个 `PlayerAgent`:
        *   代理获取其可见的最新 `GameState` 和未读消息。
        *   代理 (通过 `player_context_builder` 构建提示并调用 LLM) 根据其角色信息、目标、当前状态和收到的信息，决定要执行的行动 (`PlayerAction`)。
    *   所有玩家的行动被收集起来。
5.  **行动处理**:
    *   `DMAgent` (通过 `dm_context_builder` 构建提示并调用 LLM) 接收所有玩家的 `PlayerAction`。
    *   DM 代理根据游戏规则、当前状态和可能的随机性（如 `AgentManager.roll_dice`）来处理这些行动，生成每个行动的结果 (`ActionResult`)。
    *   行动结果可能包含状态变化、新的叙事等。
6.  **状态更新**:
    *   `GameStateManager` 根据 `ActionResult` 更新 `GameState`。这可能涉及修改角色状态、物品栏、位置、环境描述等。
7.  **回合结束 (`RoundManager`)**:
    *   检查是否满足游戏结束条件（如达到最大回合数、完成剧本目标等）。
    *   如果不结束，则进入下一回合（返回步骤 2）。
8.  **游戏结束**:
    *   `GameEngine` 执行清理工作。

这个流程通过 `RoundManager` 进行协调，并依赖 `GameStateManager` 来维护一致的游戏世界状态，同时利用 LLM 驱动 `DMAgent` 和 `PlayerAgent` 的行为。

## 如何运行

(请在此处添加运行项目的具体说明，例如：)

```bash
# 安装依赖
pip install -r requirements.txt

# 运行默认场景
python src/scripts/cli_runner.py
```

## 配置

*   **游戏配置**: `config/game_config.yaml` (例如：最大回合数)
*   **LLM 配置**: `config/llm_settings.yaml` (例如：API Key, 模型名称)
*   **剧本**: `scenarios/` 目录下的 JSON 文件。
