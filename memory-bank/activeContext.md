# Active Context: GameState 重构与聊天记录分离

## 当前工作焦点: 即时状态更新架构调整

*   **目标**: 解决当前架构中行动后果应用延迟的问题，实现状态变更的即时生效。
*   **核心改动**: 移除独立的 `UpdatePhase`，将后果的判定、校验、**即时应用**和记录整合到 `JudgementPhase`（或紧随其后）。
*   **记录机制**:
    *   在回合结束时对包含最终状态和回合内事件记录（宣告的行动、应用的后果、触发的事件）的 `GameState` 进行快照。
    *   回合内宣告的行动 (`PlayerAction`)，包括 `CompanionAgent` 生成的 `internal_thoughts` 等描述性内容，记录在快照的 `current_round_actions` 中。
    *   回合内**实际应用**的机制性后果 (`AppliedConsequenceRecord`) 和触发的事件 (`TriggeredEventRecord`) 记录在快照的相应列表中。
*   **原则**: 保持机制层（Hard Mechanisms - 应用的后果）和描述层（Soft Descriptions - 如 `internal_thoughts`）的分离。叙事基于快照中的机制性变化事实，可参考描述性内容进行润色。

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

## 下一步计划 (基于后果处理器重构后)

1.  **更新测试:** (优先级最高)
    *   修改现有测试用例以适应新的基于 Handler 的后果处理流程。
    *   为 `src/engine/consequence_handlers/` 下的每个 Handler 类编写单元测试，验证其应用和记录逻辑。
    *   执行集成测试，确保 `GameStateManager.apply_consequences` 和 `JudgementPhase` 能够正确调用 Handler 并处理后果。
2.  **更新 `progress.md`**: (完成测试后) 标记后果处理重构任务完成。
3.  **实现未完成的 Handler:** (优先级高)
    *   实现 `TriggerEventHandler` 和 `SendMessageHandler`（如果需要）。
    *   将它们添加到 `HANDLER_REGISTRY`。
4.  **更新数据模型 (Models):** (优先级高)
    *   在 `CharacterTemplate` (`src/models/scenario_models.py`) 和 `CharacterInstance` (`src/models/game_state_models.py`) 中添加用于描述 NPC 内在设定的字段，例如 `values: List[str]`, `likes: List[str]`, `dislikes: List[str]`。
5.  **实现基于 LLM 的关系评估 (RefereeAgent):** (优先级高)
    *   设计并实现 `RefereeAgent` 中的逻辑：调用 LLM 来解读玩家行动/对话与目标 NPC 内在设定 (`values`, `likes`, `dislikes` 等) 的匹配/冲突程度。
    *   定义 LLM 的输入（玩家行为、情境、NPC 设定、当前关系值）和结构化输出（例如 `RelationshipImpactAssessment` 模型，包含影响类型、强度、原因、建议变化值）。
    *   设计引导 LLM 进行评估的 Prompt。
    *   确定 `RefereeAgent` 如何结合 LLM 的建议和基础规则来最终决定 `relationship_player` 的变化量（可能生成 `CHANGE_RELATIONSHIP` 后果）。
6.  **细化 `Context Builders` 逻辑:** (优先级中)
    *   实现从 `ChatHistoryManager` 智能提取/总结关键近期互动信息（记忆）的策略。
    *   确保能将 NPC 的目标、态度（关系值、内在设定）、状态 (`status`) 和关键记忆有效整合进给 Agent 的 Prompt。
7.  **设计和迭代 Agent Prompts:** (优先级中)
    *   为 `CompanionAgent` 设计核心“思考”Prompt，强调结合目标、态度（包含关系值和内在设定）、状态和记忆进行决策。
    *   为 `NarrativeAgent` 设计 Prompt，使其能基于上下文生成生动描述，并建议更新 NPC 状态。
8.  **完善状态更新与事件驱动 (GameStateManager):** (优先级低，大部分已通过 Handler 实现)
    *   确保 `GameStateManager` 在更新阶段能正确应用 `RefereeAgent` 判定的关系值变化 (已通过 `ChangeRelationshipHandler` 实现)。
    *   继续支持通过剧本事件 (`ScenarioEvent`) 的后果直接修改 `relationship_player` (需要 `TriggerEventHandler` 实现事件后果的应用)。
    *   实现基于关系值或其他新字段的行动判定调整（如根据 `status` 调整难度，这部分逻辑在 `RefereeAgent` 中）。
9.  **实现完整的保存/加载流程**: (优先级中)
    *   在 `GameEngine` 中集成 `GameStateManager` 和 `ChatHistoryManager` 的保存/加载调用。
    *   确定保存时机和文件结构。
10. **(稍后)** 检查并清理可能冗余的 `src/models/record_models.py`。

## 待解决/考虑事项

*   确定保存游戏状态和聊天记录的具体时机（例如，每回合结束时自动保存，还是提供手动保存选项）。
*   设计保存文件的命名和组织方式（例如，每个存档一个文件夹，包含 game_state.json 和 chat_history.json）。
*   错误处理：加载状态时，如果剧本 ID 不匹配或文件损坏，应如何处理？
