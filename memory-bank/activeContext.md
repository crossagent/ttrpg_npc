# Active Context: 裁判代理增强与游戏状态管理

## 1. 当前工作焦点

**阶段一：数据模型定义与完善** 已完成。
**阶段二：裁判代理增强 (Referee Agent Enhancement)** 的**结构性调整**也已完成：
*   `ScenarioEvent.trigger_condition` 支持结构化和文本条件。
*   添加了 `context_utils.format_trigger_condition` 用于预处理结构化条件。
*   创建了 `context/referee_context_builder.py` 并迁移/添加了 Prompt 函数骨架。
*   `RefereeAgent` 职责分离：`judge_action` (直接结果) 和 `determine_triggered_event_ids` (事件触发判断)。
*   `RoundManager` 流程调整：分离行动判定和事件触发调用，添加 `_extract_consequences_for_triggered_events` 辅助方法（含占位符结局选择逻辑）。

当前的开发重点是**实现阶段二的核心逻辑**:
1.  **实现事件结局选择与后果提取**: 在 `RoundManager._extract_consequences_for_triggered_events` 中实现选择 `EventOutcome` 并提取其 `consequences` 的具体逻辑。
2.  **调整 LLM Prompts**: 修改 `referee_context_builder.py` 中的 Prompt 函数 (`build_action_resolve_*`, `build_event_trigger_*`)，使其与 `RefereeAgent` 的新职责精确匹配。
3.  **(可选/后续)** 实现更复杂的事件触发条件评估逻辑（如果需要超越 `RefereeAgent.determine_triggered_event_ids` 中 LLM 的判断）。

## 2. 近期主要任务 (开发计划)

按照 `docs/开发计划_裁判与状态管理.md` 文件规划，后续步骤分为四个阶段：

*   **阶段一：数据模型定义与完善 (Models Refinement) - 已完成**
    *   已定义结构化的 `Consequence` 模型 (`src/models/consequence_models.py`)。
    *   已调整 `EventOutcome`, `StoryStage` (`src/models/scenario_models.py`), `GameState` (`src/models/game_state_models.py`), `ActionResult` (`src/models/action_models.py`)。
*   **阶段二：裁判代理增强 (Referee Agent Enhancement) - 已完成**
    *   **结构调整 (已完成)**:
        *   `ScenarioEvent.trigger_condition` 类型已更新。
        *   `context_utils.format_trigger_condition` 已添加。
        *   `context/referee_context_builder.py` 已创建，Prompt 函数骨架已迁移/添加。
        *   `RefereeAgent` 职责已分离 (`judge_action`, `determine_triggered_events_and_outcomes`)。
        *   `RoundManager` 流程已调整，使用 `_extract_consequences_for_chosen_outcomes` 辅助方法。
    *   **核心逻辑实现 (已完成)**:
        *   `RoundManager._extract_consequences_for_chosen_outcomes` 已实现，依赖 `RefereeAgent` 提供选定结局。
        *   `referee_context_builder.py` 中的 Prompts 已调整，明确指示 LLM 选择结局 ID。
        *   (可选的复杂条件评估逻辑未实现，当前依赖 LLM)。
*   **阶段三：游戏状态管理器增强 (Game State Manager Enhancement) - 当前阶段 (主要完成)**
    *   **核心方法 `apply_consequences` (已实现框架)**:
        *   已在 `GameStateManager` 中实现 `apply_consequences` 方法。
        *   已实现 `UPDATE_ATTRIBUTE`, `ADD_ITEM`, `REMOVE_ITEM` 的处理逻辑。
        *   `CHANGE_RELATIONSHIP`, `TRIGGER_EVENT`, `SEND_MESSAGE` 的处理逻辑为 **TODO** 占位符。
    *   **旧逻辑移除 (已完成)**: 旧 `update_state` 方法已注释掉。
    *   **核心状态管理与进程推进方法 (已实现)**:
        *   已实现 `check_item`。
        *   已实现 `check_stage_completion` (包含基础的 flag 和 item 条件检查)。
        *   已实现 `advance_stage` (包含调用 `update_active_events`)。
        *   已实现 `update_active_events` (基于 `activation_stage_id`)。
    *   **初始化逻辑更新 (已完成)**: `initialize_game_state` 现在调用 `update_active_events`。
    *   **`RoundManager` 整合 (已完成)**: `execute_round` 现在调用 `apply_consequences` 和 `advance_stage`。
*   **阶段四：集成与测试 (Integration and Testing) - 下一阶段**
    *   将修改后的模块整合回 `GameEngine` 的游戏循环。
    *   编写单元测试和集成测试，特别是针对 `GameStateManager` 的新方法和 `RoundManager` 的流程。
    *   (可选) 实现 `apply_consequences` 中剩余的 TODO 处理逻辑。
    *   (可选) 优化 `referee_context_builder.py` 中的 Prompts。

## 3. 当前决策与考虑 (阶段三完成，准备阶段四)

*   **`apply_consequences` TODOs**: `CHANGE_RELATIONSHIP`, `TRIGGER_EVENT`, `SEND_MESSAGE` 的处理逻辑尚未实现。这些可以在阶段四测试期间或根据需要再实现。`SEND_MESSAGE` 可能需要 `GameStateManager` 能够访问 `MessageDispatcher`。
*   **`check_stage_completion` 复杂性**: 当前实现只处理了基础的 `flag_set` 和 `item_possession` 条件。如果剧本需要更复杂的条件（如属性检查、组合条件等），需要后续扩展。
*   **测试覆盖**: 阶段四需要重点测试 `GameStateManager` 的状态更新和阶段推进逻辑，以及 `RoundManager` 中这些新调用的正确性。
*   **Prompt 调优**: `referee_context_builder.py` 中的 Prompt 可能需要根据测试结果进行调优。

*(此文件基于 docs/开发计划_裁判与状态管理.md 和近期开发活动更新)*
