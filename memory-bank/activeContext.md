# Active Context: GameState 重构与聊天记录分离

## 当前工作焦点

*   **核心策略确立: 硬机制与软描述分层**
    *   明确了游戏实现的分层策略：核心规则/进展/状态使用可靠的**硬机制**（Flags, 数值属性, 预定义逻辑）；角色行为/个性/氛围/交互细节依赖**软描述**（LLM 上下文理解, 宏观状态字段, Prompt 设计）。(详见 `systemPatterns.md`)
    *   当前阶段优先利用**软描述**和 LLM 能力快速实现动态交互，辅以必要的硬机制。
*   **聚焦 NPC 核心要素:**
    *   当前设计和开发工作的核心是实现 NPC 的三个关键要素，以驱动智能交互和突破性体验：
        1.  **目标 (Goals):** 结合预设背景和 LLM 动态生成的情境意图。
        2.  **对玩家的态度 (Attitude):** 结合硬性关系值和 LLM 演绎的细微情绪/行为。
        3.  **重要事件记忆 (Memory):** 结合硬性关键 Flags 和由 `Context Builders` 提取/总结的近期重要互动信息。
*   **基础架构调整完成:**
    *   `GameState` 重构完成，变得更轻量。
    *   引入独立的 `ChatHistoryManager` 管理聊天记录。
    *   更新了相关模块以适应新的数据结构和访问方式。
    *   初步实现了 `GameStateManager` 的核心状态保存/加载接口。

## 近期变更

*   修改了 `src/models/game_state_models.py`：移除 `scenario`, `chat_history`, `item_states` 等字段，添加 `scenario_id`。清理冗余模型。
*   创建了 `src/engine/chat_history_manager.py`。
*   修改了 `src/engine/game_state_manager.py`：移除对 `game_state.scenario` 的访问，添加 `save_state`/`load_state`。
*   修改了 `src/context/context_utils.py`：添加 `scenario_manager` 参数，更新剧本访问逻辑。
*   修改了 `src/context/player_context_builder.py`：添加 `scenario_manager` 参数，更新剧本访问逻辑。
*   修改了 `src/agents/player_agent.py`：添加 `scenario_manager` 依赖，更新剧本访问逻辑。
*   修改了 `src/communication/message_dispatcher.py`：添加 `chat_history_manager` 和 `game_state_manager` 依赖，更新消息记录和历史获取逻辑。
*   修改了 `src/engine/game_engine.py`：实例化 `ChatHistoryManager` 并正确注入依赖。
*   **修改了 `src/models/game_state_models.py`**: 为 `CharacterInstance` 添加了 `relationship_player`, `attitude_description`, `long_term_goal`, `short_term_goals`, `key_memories`, `status` 字段，以支持 NPC 核心要素（态度、目标、记忆、状态）。

## 下一步计划 (围绕 NPC 核心要素)

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
8.  **更新 `progress.md`**: (完成此步骤后) 跟踪上述任务的进展。

## 待解决/考虑事项

*   确定保存游戏状态和聊天记录的具体时机（例如，每回合结束时自动保存，还是提供手动保存选项）。
*   设计保存文件的命名和组织方式（例如，每个存档一个文件夹，包含 game_state.json 和 chat_history.json）。
*   错误处理：加载状态时，如果剧本 ID 不匹配或文件损坏，应如何处理？
