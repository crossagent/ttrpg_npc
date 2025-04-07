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
*   **修复了 `src/agents/companion_agent.py`**: 将 `get_messages_for_round` 调用修正为 `get_messages`。
*   **修复了 `src/engine/consequence_handlers/base_handler.py`**: 在 `_create_record` 中添加了 `source_description` 和 `applied_consequence` 字段，以解决 `ValidationError`。
*   **更新了 `src/context/referee_context_builder.py`**: 修改了 `build_action_resolve_system_prompt`，指导 LLM 为角色属性/技能生成正确的后果类型 (`UPDATE_CHARACTER_ATTRIBUTE` / `UPDATE_CHARACTER_SKILL`)。
*   **更新了 `memory-bank/systemPatterns.md`**: 明确了 `GameStateManager` 和 `ChatHistoryManager` 的职责差异。
*   **更新了 `src/context/referee_context_builder.py`**: 再次修改 `build_action_resolve_system_prompt`，添加明确指令要求 LLM 必须使用有效的实体 ID。
*   **重构后果处理模型**:
    *   修改了 `src/models/consequence_models.py`，使用 Pydantic Discriminated Unions 定义了 `AnyConsequence`，为每种后果类型创建了精确的模型。
    *   修改了 `src/engine/consequence_handlers/base_handler.py`，更新 `apply` 和 `_create_record` 方法以接受 `AnyConsequence`。
    *   修改了 `src/engine/consequence_handlers/` 目录下的所有具体 Handler 实现，使其适应新的模型和基类接口。
    *   修改了 `src/agents/referee_agent.py` 中解析 LLM 返回后果的部分，使用 `AnyConsequence.model_validate`。
*   **移除了 `GameState.last_active_round`**: 不再显式跟踪最后一个活跃回合。
*   **更新了 `NarrationPhase` 活跃度判断**: 现在通过检查历史回合快照中的实际活动记录（行动、后果、事件）来判断是否需要触发叙事。

## 下一步计划 (基于日志分析和 Bug 修复后)

1.  **运行游戏测试**: (当前最高优先级) 运行游戏以验证移除 `last_active_round` 及 `NarrationPhase` 新逻辑的效果，以及整体流程。
2.  **优化 Agent Prompts 和数据源**: (优先级次高) 在核心 Bug 修复并通过测试后，重新审视并优化各个 Agent (特别是 `CompanionAgent`, `RefereeAgent`, `NarrativeAgent`) 的 Prompt，并确认它们获取的数据源是否准确、充分。
3.  **更新测试用例**: (优先级中) 修改或添加测试用例以覆盖新的逻辑和修复。
4.  **更新测试用例**: (优先级中) 修改或添加测试用例以覆盖新的逻辑和修复。
5.  **实现未完成的 Handler**: (优先级中)
    *   实现 `TriggerEventHandler` 。
    *   将它们添加到 `HANDLER_REGISTRY`。
6.  **更新数据模型 (Models):** (优先级中)
    *   在 `CharacterTemplate` (`src/models/scenario_models.py`) 和 `CharacterInstance` (`src/models/game_state_models.py`) 中添加用于描述 NPC 内在设定的字段，例如 `values: List[str]`, `likes: List[str]`, `dislikes: List[str]`。
7.  **实现基于 LLM 的关系评估 (RefereeAgent):** (优先级中)
    *   设计并实现 `RefereeAgent` 中的逻辑：调用 LLM 来解读玩家行动/对话与目标 NPC 内在设定 (`values`, `likes`, `dislikes` 等) 的匹配/冲突程度。
    *   定义 LLM 的输入（玩家行为、情境、NPC 设定、当前关系值）和结构化输出（例如 `RelationshipImpactAssessment` 模型，包含影响类型、强度、原因、建议变化值）。
    *   设计引导 LLM 进行评估的 Prompt。
    *   确定 `RefereeAgent` 如何结合 LLM 的建议和基础规则来最终决定 `relationship_player` 的变化量（可能生成 `CHANGE_RELATIONSHIP` 后果）。
8.  **细化 `Context Builders` 逻辑:** (优先级中)
    *   实现从 `ChatHistoryManager` 智能提取/总结关键近期互动信息（记忆）的策略。
    *   确保能将 NPC 的目标、态度（关系值、内在设定）、状态 (`status`) 和关键记忆有效整合进给 Agent 的 Prompt。
9.  **实现完整的保存/加载流程**: (优先级中)
    *   在 `GameEngine` 中集成 `GameStateManager` 和 `ChatHistoryManager` 的保存/加载调用。
    *   确定保存时机和文件结构。
10. **更新 `progress.md`**: (在完成主要 Bug 修复和测试后) 更新项目进展。
11. **(稍后)** 检查并清理可能冗余的 `src/models/record_models.py`。

## 待解决/考虑事项

## 架构理解深化

*   **明确职责**: 进一步明确了 `GameState` (核心机制状态、全局信息、世界快照) 与 `ChatHistoryManager` (交互历史、上下文、信息可见性) 的不同职责和重要性。`GameState` 是硬性规则和后果的基础，而 `ChatHistoryManager` 为 Agent 理解对话流、进行关系评估和生成符合情境的反应提供关键上下文。保持此分离对实现智能交互至关重要。

*   确定保存游戏状态和聊天记录的具体时机（例如，每回合结束时自动保存，还是提供手动保存选项）。
*   设计保存文件的命名和组织方式（例如，每个存档一个文件夹，包含 game_state.json 和 chat_history.json）。
*   错误处理：加载状态时，如果剧本 ID 不匹配或文件损坏，应如何处理？
