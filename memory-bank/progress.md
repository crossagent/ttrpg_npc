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

1.  **更新数据模型 (Models):** (优先级最高)
    *   在 `CharacterTemplate` (`src/models/scenario_models.py`) 和 `CharacterInstance` (`src/models/game_state_models.py`) 中添加用于描述 NPC 内在设定的字段，例如 `values: List[str]`, `likes: List[str]`, `dislikes: List[str]`。
2.  **实现基于 LLM 的关系评估 (RefereeAgent):** (优先级最高)
    *   设计并实现 `RefereeAgent` 中的逻辑：调用 LLM 来解读玩家行动/对话与目标 NPC 内在设定 (`values`, `likes`, `dislikes` 等) 的匹配/冲突程度。
    *   定义 LLM 的输入（玩家行为、情境、NPC 设定、当前关系值）和结构化输出（例如 `RelationshipImpactAssessment` 模型，包含影响类型、强度、原因、建议变化值）。
    *   设计引导 LLM 进行评估的 Prompt。
    *   确定 `RefereeAgent` 如何结合 LLM 的建议和基础规则来最终决定 `relationship_player` 的变化量。
3.  **细化 `Context Builders` 逻辑:** (优先级高)
    *   实现从 `ChatHistoryManager` 智能提取/总结关键近期互动信息（记忆）的策略。
    *   确保能将 NPC 的目标、态度（关系值、内在设定）、状态 (`status`) 和关键记忆有效整合进给 Agent 的 Prompt。
4.  **设计和迭代 Agent Prompts:** (优先级高)
    *   为 `CompanionAgent` 设计核心“思考”Prompt，强调结合目标、态度（包含关系值和内在设定）、状态和记忆进行决策。
    *   为 `NarrativeAgent` 设计 Prompt，使其能基于上下文生成生动描述，并建议更新 NPC 状态。
5.  **完善状态更新与事件驱动 (GameStateManager):** (优先级中)
    *   确保 `GameStateManager` 在更新阶段能正确应用 `RefereeAgent` 判定的关系值变化。
    *   继续支持通过剧本事件 (`ScenarioEvent`) 的后果直接修改 `relationship_player`。
    *   实现基于关系值或其他新字段的行动判定调整（如根据 `status` 调整难度）。
6.  **实现完整的保存/加载流程**: (优先级中)
    *   在 `GameEngine` 中集成 `GameStateManager` 和 `ChatHistoryManager` 的保存/加载调用。
    *   确定保存时机和文件结构。
7.  **集成测试**: (持续进行) 重点测试新的关系更新机制是否有效，NPC 行为是否符合其目标、态度和记忆。

## 已知问题 / 待办

*   需要实现玩家输入处理 (`InputHandler`)。
*   需要完善 `MessageDispatcher` 的消息过滤逻辑。
*   需要添加更全面的错误处理和日志记录。
*   需要设计具体的剧本内容 (`Scenario`) 来测试和展示新机制。
