# System Patterns: TTRPG NPC 模拟引擎 V5 (Async Engine Arch)

## 1. 核心架构概述

本系统采用模块化设计，支持 **命令行 (CLI)** 和 **Web 服务 (FastAPI + WebSocket)** 两种运行模式。

*   **核心**: **游戏引擎 (Game Engine)** 负责驱动游戏的核心逻辑，其主循环 (`run_game`) 设计为**异步**执行。
*   **状态管理**: **游戏状态管理器 (Game State Manager)** 作为单一事实来源 (Single Source of Truth)，管理核心机制状态。
*   **交互**: **代理管理器 (Agent Manager)** 调度不同类型的 **代理 (Agents)**。**消息分发器 (Message Dispatcher)** 处理通信，根据运行模式将输出路由到控制台或 WebSocket。
*   **输入处理**: 通过抽象的 **用户输入处理器 (UserInputHandler)** 接口处理玩家输入，具体实现 (`CliInputHandler` 或 `ApiInputHandler`) 根据运行模式注入。
*   **Web 模式协调**: 在 Web 模式下，**会话管理器 (Session Manager)** 负责创建和管理多个并行的游戏会话（每个会话包含一个异步运行的 `GameEngine` 实例），处理 WebSocket 连接，并在 `GameEngine` 和 Web 客户端之间传递输入/输出。
*   **内容**: **剧本管理器 (Scenario Manager)** 负责结构化的剧本内容。**上下文构建器 (Context Builders)** 负责格式化数据。

## 2. 主要模块及其职责

*   **游戏引擎 (Game Engine)**:
    *   **职责**: 包含核心的**异步**游戏循环 (`async def run_game`)，按回合驱动游戏进程，协调 `RoundManager`、`AgentManager` 等。接收一个 `UserInputHandler` 实例用于处理玩家交互。
    *   **模式**: 异步协调器 (Asynchronous Coordinator)。
*   **代理管理器 & 代理 (Agent Manager & Agents)**:
    *   **职责**: (同 V4) 管理所有智能体（玩家、NPC、叙事、裁判）的生命周期和调度。Agent 的思考/行动方法可能需要调整为 `async` 以适应整体异步流程。
    *   **模式**: 代理模式 (Agent Pattern)，面向对象设计。
    *   **核心代理类型**: (基本同 V4，但与 `InputHandler` 的交互变为异步)
        *   PlayerAgent, CompanionAgent, NarrativeAgent, RefereeAgent。
*   **游戏状态管理器 (Game State Manager)**:
    *   **职责**: (同 V4) 存储和管理核心游戏状态，应用后果，提供状态保存/加载。方法基本保持同步，因为状态变更通常是原子性的。
    *   **模式**: 单一事实来源 (Single Source of Truth)。
*   **后果处理器 (Consequence Handlers)**:
    *   **职责 & 模式**: (同 V4) 实现具体后果应用逻辑。
*   **剧本管理器 (Scenario Manager)**:
    *   **职责 & 模式**: (同 V4) 加载、存储和提供剧本数据访问。
*   **聊天记录管理器 (Chat History Manager)**:
    *   **职责 & 模式**: (同 V4) 存储和检索游戏交互历史。
*   **消息分发器 (Message Dispatcher)**:
    *   **职责**: 路由和分发消息。**新增职责**: 根据当前运行模式（通过配置或注入的处理器判断）将消息路由到不同的输出处理器（控制台打印或 WebSocket 广播）。
    *   **模式**: 发布/订阅模式 (Publish/Subscribe)，模式切换路由。
*   **上下文构建器 (Context Builders)**:
    *   **职责 & 模式**: (同 V4) 格式化数据供 Agent 使用。
*   **用户输入处理器 (UserInputHandler - Interface/Base)**:
    *   **职责**: 定义处理玩家输入的**异步**接口，例如 `async def get_player_action(...)`, `async def get_dice_roll_input(...)`, `async def display_message(...)`。
    *   **模式**: 策略模式 (Strategy Pattern) / 接口隔离。
*   **命令行输入处理器 (CliInputHandler)**:
    *   **职责**: 实现 `UserInputHandler` 接口，用于 CLI 模式。使用 `asyncio.to_thread` 将阻塞的 `input()` 调用包装成异步操作，避免阻塞事件循环。直接将 `display_message` 的内容打印到控制台。
    *   **模式**: 策略实现。
*   **API 输入处理器 (ApiInputHandler)**:
    *   **职责**: 实现 `UserInputHandler` 接口，用于 Web 模式。
        *   当 `GameEngine` 调用其 `async get_...` 方法时，它不直接等待输入。而是：
            1.  生成一个内部的 `asyncio.Future` 或 `asyncio.Event` 来代表待完成的输入。
            2.  调用 `SessionManager` 提供的回调函数，将输入请求（包含提示、类型、选项和用于标识本次请求的 ID）通过 WebSocket 发送给客户端。
            3.  `await` 内部的 `Future/Event`，暂停 `GameEngine` 的执行。
        *   当 `SessionManager` 从 WebSocket 或 API 接收到对应请求 ID 的输入时，它会设置该 `Future/Event` 的结果，从而唤醒 `ApiInputHandler` 的 `await`，将结果返回给 `GameEngine`。
        *   `display_message` 方法调用 `SessionManager` 提供的回调，将消息通过 WebSocket 发送出去。
    *   **模式**: 策略实现，异步回调/Future 模式。
*   **会话管理器 (Session Manager - Web Mode Only)**:
    *   **位置**: `src/server/session_manager.py`
    *   **职责**:
        *   管理活跃的游戏会话，映射 `session_id` 到 `GameEngine` 实例和关联的 `ApiInputHandler` 实例。
        *   管理每个会话的 WebSocket 连接列表。
        *   提供 API (`/sessions/start`, `/sessions/load`) 来创建/加载会话，并在后台启动对应的 `async GameEngine.run_game()` 任务。
        *   提供 WebSocket 端点 (`/ws/{session_id}`) 处理客户端连接。
        *   提供 API (`/sessions/{session_id}/action`) 接收来自客户端的输入。
        *   **核心协调**: 当从 WebSocket/API 收到输入时，找到对应的 `ApiInputHandler` 并调用其方法（如 `receive_input`）来设置 `Future/Event`，唤醒等待的 `GameEngine` 任务。
        *   提供回调函数给 `ApiInputHandler` 和 `MessageDispatcher`，用于通过 WebSocket 发送消息（输入请求或游戏消息）给客户端。
    *   **模式**: 会话管理，Web 协调器。
*   **展现层 (Presentation Layer)**:
    *   **职责**: 用户界面。可以是 CLI (`src/scripts/cli_runner.py`) 或 Web 前端（通过 FastAPI 和 WebSocket 与后端交互）。
    *   **模式**: MVC/MVP 中的 View 层。

## 3. 关键交互模式与数据流 (Async Engine)

*   **异步游戏循环**: `GameEngine.run_game()` 是一个 `async` 函数，包含主游戏循环。
*   **Web 模式启动**:
    1.  客户端通过 API (`/sessions/start`) 请求新游戏。
    2.  `SessionManager` 创建 `GameEngine` 实例，注入 `ApiInputHandler`，并创建 `session_id`。
    3.  `SessionManager` 使用 `asyncio.create_task(game_engine.run_game())` 启动游戏循环作为后台任务。
    4.  客户端通过 WebSocket (`/ws/{session_id}`) 连接到会话。
*   **Web 模式输入处理**:
    1.  `GameEngine` 循环执行到需要玩家输入的地方。
    2.  调用注入的 `ApiInputHandler` 的 `async get_...` 方法。
    3.  `ApiInputHandler` 通过 `SessionManager` 提供的回调，将输入请求发送给对应 `session_id` 的 WebSocket 客户端。
    4.  `ApiInputHandler` `await` 一个内部的 `Future/Event`，`GameEngine` 任务暂停。
    5.  客户端通过 WebSocket 或 API (`/sessions/{session_id}/action`) 发送输入。
    6.  `SessionManager` 接收输入，找到对应的 `ApiInputHandler`，调用其方法设置 `Future/Event` 的结果。
    7.  `ApiInputHandler` 的 `await` 结束，将输入返回给 `GameEngine`。
    8.  `GameEngine` 任务恢复执行。
*   **Web 模式输出处理**:
    1.  游戏过程中产生的消息（对话、叙述、状态变化）被发送到 `MessageDispatcher`。
    2.  `MessageDispatcher` 检测到是 Web 模式，调用 `SessionManager` 提供的回调。
    3.  `SessionManager` 将消息广播给对应 `session_id` 的所有 WebSocket 连接。
*   **CLI 模式启动**:
    1.  `cli_runner.py` 创建 `GameEngine` 实例，注入 `CliInputHandler`。
    2.  `cli_runner.py` 调用 `asyncio.run(game_engine.run_game())` 启动游戏。
*   **CLI 模式输入处理**:
    1.  `GameEngine` 调用注入的 `CliInputHandler` 的 `async get_...` 方法。
    2.  `CliInputHandler` 使用 `asyncio.to_thread(input, ...)` 在单独线程中执行阻塞的 `input()`。
    3.  `GameEngine` `await` 这个异步调用，事件循环可以处理其他 `asyncio` 任务（虽然 CLI 模式下通常不多）。
    4.  用户输入后，线程返回结果，`await` 结束，`GameEngine` 继续。
*   **CLI 模式输出处理**:
    1.  消息发送到 `MessageDispatcher`。
    2.  `MessageDispatcher` 检测到是 CLI 模式，调用 `simple_console_display_handler` 直接打印到控制台。

## 4. 设计原则

*   **异步优先**: 核心游戏循环和 I/O 操作设计为异步。
*   **I/O 抽象**: 通过 `UserInputHandler` 接口将输入逻辑与核心引擎分离。
*   **模式解耦**: 通过注入不同的 `InputHandler` 和配置 `MessageDispatcher` 来支持 CLI 和 Web 模式。
*   **Web 协调**: `SessionManager` 负责 Web 模式下的会话生命周期和异步协调。

## 5. 核心实现策略：硬机制与软描述分层

(此部分与 V4 基本一致，保持不变)

为了平衡游戏核心规则的稳定性和 LLM 驱动的动态交互的灵活性，系统采用分层实现策略：

*   **硬机制 (Hard Mechanisms):** ...
*   **软描述 (Soft Descriptions):** ...
*   **协同工作:** ...

*(此文件基于 V4 版本修改，采用异步 GameEngine 架构)*
