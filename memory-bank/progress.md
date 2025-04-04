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
*   **核心实现策略确立**: 明确了采用“硬机制与软描述分层”的策略，当前阶段优先利用软描述和 LLM 上下文能力实现动态交互 (详见 `systemPatterns.md`)。
*   **开发焦点明确**: 确定当前开发核心是围绕 NPC 的三大要素：目标 (Goals)、态度 (Attitude)、记忆 (Memory)。
*   **`CharacterInstance` 扩展**: 在 `CharacterInstance` 模型中添加了 `relationship_player`, `attitude_description`, `long_term_goal`, `short_term_goals`, `key_memories`, `status` 字段，为实现 NPC 核心要素奠定基础。

## 进行中 / 下一步 (围绕 NPC 核心要素，按优先级)

1.  **细化 `Context Builders` 逻辑 (High Priority)**:
    *   实现从 `ChatHistoryManager` 智能提取/总结关键近期互动信息（记忆）的策略。
    *   确保将 NPC 目标、态度（关系值）、状态 (`status`) 和关键记忆有效整合进 Prompt。
2.  **设计和迭代 Agent Prompts (High Priority)**:
    *   为 `CompanionAgent` 设计核心“思考”Prompt，强调结合目标、态度、状态和记忆进行决策。
    *   为 `NarrativeAgent` 设计 Prompt，使其能基于上下文生成生动描述，并建议更新 NPC 状态。
3.  **完善 `RefereeAgent` 和 `GameStateManager` (Medium Priority)**:
    *   实现对新 `CharacterInstance` 字段（如关系值）的硬性更新逻辑。
    *   实现基于新字段的行动判定调整（如根据 `status` 调整难度）。
4.  **实现完整的保存/加载流程 (Medium Priority)**:
    *   集成 `GameStateManager` 和 `ChatHistoryManager` 的保存/加载调用。
    *   确定保存时机和文件结构。
5.  **完善 `RoundManager` 和阶段处理器 (Low Priority / As Needed)**:
    *   根据上述功能的实现，填充和调整各阶段处理器的具体逻辑。
6.  **集成与测试 (Ongoing)**:
    *   持续测试 NPC 行为是否符合其核心要素，分层机制是否有效。

## 已知问题 / 待办

*   需要实现玩家输入处理 (`InputHandler`)。
*   需要完善 `MessageDispatcher` 的消息过滤逻辑。
*   需要添加更全面的错误处理和日志记录。
*   需要设计具体的剧本内容 (`Scenario`) 来测试和展示新机制。
