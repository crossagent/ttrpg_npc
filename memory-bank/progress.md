# Progress: TTRPG NPC 模拟引擎

## 已完成

*   **V4 架构设计**: 定义了新的 Agent 职责 (Narrative, Referee, Player, Companion) 和四阶段回合流程。
*   **核心 Agent 骨架**: 创建了 `NarrativeAgent`, `RefereeAgent`, `PlayerAgent`, `CompanionAgent` 的基本类结构。
*   **回合阶段处理器骨架**: 创建了 `NarrationPhase`, `ActionDeclarationPhase`, `JudgementPhase`, `UpdatePhase` 的基本类结构。
*   **CharacterInstance 模型**: 将角色的运行时状态（属性、技能、健康、位置、物品、知识）整合到 `CharacterInstance` 中，并更新了 `GameState`。
*   **GameState 重构**:
    *   将 `GameState` 模型变得更轻量，移除了 `scenario` 和 `chat_history`，替换为 `scenario_id`。
    *   引入了独立的 `ChatHistoryManager` 按回合管理聊天记录。
    *   更新了相关模块 (`GameStateManager`, `Context Builders`, `PlayerAgent`, `MessageDispatcher`, `GameEngine`) 以适应新的结构和依赖关系。
    *   为 `GameStateManager` 添加了 `save_state` 和 `load_state` 方法用于核心状态的序列化。

## 进行中 / 下一步

*   **实现完整的保存/加载流程**:
    *   在 `GameEngine` 或类似协调器中，实现调用 `GameStateManager.save_state`/`load_state` 和 `ChatHistoryManager.save_history`/`load_history` 的逻辑。
    *   确定保存时机和文件组织方式。
*   **更新 Context Builders (聊天记录)**:
    *   修改所有需要聊天记录的 Context Builders，使其从 `ChatHistoryManager` 获取数据。
*   **完善 `RefereeAgent`**:
    *   实现详细的行动判定逻辑（结合 `CharacterInstance` 的属性/技能）。
    *   实现事件触发判定逻辑。
*   **完善 `GameStateManager`**:
    *   实现 `check_stage_completion` 方法，确保能根据 Flags 正确判断。
*   **完善 `RoundManager` 和阶段处理器**:
    *   填充各个阶段处理器的具体逻辑。
    *   确保 `RoundManager` 正确协调各阶段。
*   **集成与测试**: 对整个 V4 架构和 GameState 重构后的功能进行集成测试。

## 已知问题 / 待办

*   需要实现玩家输入处理 (`InputHandler`)。
*   需要完善 `MessageDispatcher` 的消息过滤逻辑。
*   需要为新 Agent 设计 LLM Prompts。
*   需要添加更全面的错误处理和日志记录。
