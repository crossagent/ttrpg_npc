# Active Context: GameState 重构与聊天记录分离

## 当前工作焦点

*   **GameState 重构完成**: `GameState` 模型 (`src/models/game_state_models.py`) 已被重构，移除了完整的 `Scenario` 对象（替换为 `scenario_id`）和 `chat_history` 列表，使其更轻量，适合序列化为回合快照。同时清理了冗余的模型定义（如 `ItemStatus`）。
*   **引入 ChatHistoryManager**: 创建了新的 `ChatHistoryManager` (`src/engine/chat_history_manager.py`)，用于独立管理按回合存储的聊天记录。
*   **Scenario 访问更新**: 修改了 `GameStateManager`, `Context Builders` (`context_utils.py`, `player_context_builder.py`), 和 `PlayerAgent`，使其通过 `ScenarioManager` 实例（通常通过依赖注入传递）和 `GameState.scenario_id` 来访问剧本信息，而不是直接访问 `game_state.scenario`。
*   **MessageDispatcher 集成**: 更新了 `MessageDispatcher`，使其在分发消息后调用 `ChatHistoryManager` 来记录消息，并从 `ChatHistoryManager` 获取历史记录。
*   **GameStateManager 保存/加载**: 为 `GameStateManager` 添加了 `save_state` 和 `load_state` 方法，用于序列化/反序列化核心游戏状态到 JSON 文件（不含聊天记录）。

## 近期变更

*   修改了 `src/models/game_state_models.py`：移除 `scenario`, `chat_history`, `item_states` 等字段，添加 `scenario_id`。清理冗余模型。
*   创建了 `src/engine/chat_history_manager.py`。
*   修改了 `src/engine/game_state_manager.py`：移除对 `game_state.scenario` 的访问，添加 `save_state`/`load_state`。
*   修改了 `src/context/context_utils.py`：添加 `scenario_manager` 参数，更新剧本访问逻辑。
*   修改了 `src/context/player_context_builder.py`：添加 `scenario_manager` 参数，更新剧本访问逻辑。
*   修改了 `src/agents/player_agent.py`：添加 `scenario_manager` 依赖，更新剧本访问逻辑。
*   修改了 `src/communication/message_dispatcher.py`：添加 `chat_history_manager` 和 `game_state_manager` 依赖，更新消息记录和历史获取逻辑。
*   修改了 `src/engine/game_engine.py`：实例化 `ChatHistoryManager` 并正确注入依赖。

## 下一步计划

1.  **实现完整的保存/加载流程**: 在 `GameEngine` 或其他协调层调用 `GameStateManager.save_state`/`load_state` 和 `ChatHistoryManager.save_history`/`load_history`，以实现完整的游戏进度保存和加载功能。
2.  **更新 Context Builders**: 确保所有需要聊天记录的 Context Builders（例如用于构建 LLM prompt）现在从 `ChatHistoryManager` 获取所需回合的消息。
3.  **测试**: 对重构后的状态管理、聊天记录、保存/加载功能进行全面测试。
4.  **更新 `progress.md`**: 标记 GameState 重构任务的完成状态。

## 待解决/考虑事项

*   确定保存游戏状态和聊天记录的具体时机（例如，每回合结束时自动保存，还是提供手动保存选项）。
*   设计保存文件的命名和组织方式（例如，每个存档一个文件夹，包含 game_state.json 和 chat_history.json）。
*   错误处理：加载状态时，如果剧本 ID 不匹配或文件损坏，应如何处理？
