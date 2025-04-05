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

## 下一步计划 (实施即时状态更新架构 - 调整后)

1.  **定义记录模型:** (优先级最高)
    *   在 `src/models/consequence_models.py` 中定义 `AppliedConsequenceRecord` 模型，用于清晰记录**已应用的**机制性后果细节。
    *   在 `src/models/consequence_models.py` 中定义 `TriggeredEventRecord` 模型，记录触发的事件 ID 和结局。
2.  **修改 `GameState` 模型:** (优先级最高)
    *   在 `src/models/game_state_models.py` 中的 `GameState` 添加临时的回合作用域列表：
        *   `current_round_actions: List[PlayerAction] = Field(default_factory=list)`
        *   `current_round_applied_consequences: List[AppliedConsequenceRecord] = Field(default_factory=list)`
        *   `current_round_triggered_events: List[TriggeredEventRecord] = Field(default_factory=list)`
    *   确保这些字段在序列化时可以被包含（用于快照），并在新回合开始时会被清空。
3.  **修改 `GameStateManager`:** (优先级高)
    *   确保其状态修改方法（如属性更新、Flag 设置、事件应用等）是**即时生效**的。
    *   确认或添加创建/检索 `GameState` 快照的方法。
4.  **修改回合阶段处理器 (`NarrationPhase`, `ActionDeclarationPhase`, `JudgementPhase`):** (优先级高)
    *   确保所有可能修改状态的阶段都注入 `GameStateManager`。
    *   在各阶段逻辑中，任何需要修改状态的地方，都**调用 `GameStateManager` 的方法立即应用**。
    *   **在成功应用状态变更后**，创建对应的记录实例 (`PlayerAction`, `AppliedConsequenceRecord`, `TriggeredEventRecord`)，并将其添加到当前 *实时* `GameState` 的相应 `current_round_...` 列表中。
    *   `ActionDeclarationPhase` 负责记录 `PlayerAction`。
    *   `JudgementPhase` 负责判定、校验、应用后果/事件，并记录 `AppliedConsequenceRecord` / `TriggeredEventRecord`。
5.  **修改 `RoundManager` / `GameEngine`:** (优先级高)
    *   在回合开始逻辑中，清空 *实时* `GameState` 的 `current_round_...` 列表。
    *   在回合结束逻辑中，实现对 *实时* `GameState` 的**深拷贝**（快照）并存储（例如，按回合号存入内存字典）。
6.  **修改叙事逻辑 (`NarrationPhase` / `NarrativeAgent`):** (优先级中)
    *   修改逻辑，使其在回合开始时获取**上一回合**的 `GameState` 快照。
    *   基于快照中的 `current_round_applied_consequences` 和 `current_round_triggered_events` 生成核心叙事，可参考 `current_round_actions` 中的描述性内容进行丰富。
7.  **移除 `UpdatePhase`:** (优先级高)
    *   删除 `src/engine/round_phases/update_phase.py` 文件。
    *   从 `RoundManager` 的回合流程中移除该阶段。
8.  **更新测试:** (优先级高)
    *   修改现有测试用例以适应新的分布式状态更新和记录流程。
    *   添加新的测试用例，验证状态即时更新和回合记录的正确性。
9.  **更新 `progress.md`**: (完成上述步骤后) 跟踪架构调整任务的进展。
10. **(稍后)** 检查并清理可能冗余的 `src/models/record_models.py`。

## 待解决/考虑事项

*   确定保存游戏状态和聊天记录的具体时机（例如，每回合结束时自动保存，还是提供手动保存选项）。
*   设计保存文件的命名和组织方式（例如，每个存档一个文件夹，包含 game_state.json 和 chat_history.json）。
*   错误处理：加载状态时，如果剧本 ID 不匹配或文件损坏，应如何处理？
