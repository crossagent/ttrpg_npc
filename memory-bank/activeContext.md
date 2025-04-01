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
*   **阶段二：裁判代理增强 (Referee Agent Enhancement) - 当前阶段**
    *   **结构调整 (已完成)**:
        *   `ScenarioEvent.trigger_condition` 类型已更新。
        *   `context_utils.format_trigger_condition` 已添加。
        *   `context/referee_context_builder.py` 已创建，Prompt 函数骨架已迁移/添加。
        *   `RefereeAgent` 职责已分离 (`judge_action`, `determine_triggered_event_ids`)。
        *   `RoundManager` 流程已调整，添加 `_extract_consequences_for_triggered_events` 占位符。
    *   **核心逻辑实现 (待办)**:
        *   实现 `RoundManager._extract_consequences_for_triggered_events` 中的结局选择和后果提取逻辑。
        *   调整 `referee_context_builder.py` 中的 LLM Prompts (行动判定和事件触发)。
        *   (可选) 实现更复杂的事件触发条件评估逻辑。
*   **阶段三：游戏状态管理器增强 (Game State Manager Enhancement)**
    *   实现核心方法 `apply_consequences` 来处理整合后的后果列表 (`all_round_consequences`)。
    *   重构/移除旧的 `update_state`。
    *   实现 `check_item`、`check_stage_completion`、`advance_stage` 和 `update_active_events` 等核心状态管理和进程推进方法。
    *   更新初始化逻辑以调用 `update_active_events`。
*   **阶段四：集成与测试 (Integration and Testing)**
    *   将修改后的模块整合回 `GameEngine` 的游戏循环。
    *   编写单元测试和集成测试。

## 3. 当前决策与考虑 (阶段二 - 核心逻辑实现)

*   **事件结局选择**: 在 `_extract_consequences_for_triggered_events` 中，当一个事件有多个 `possible_outcomes` 时，如何决定选择哪一个？（当前占位符是选择第一个）。需要确定是基于规则、随机，还是需要 LLM 判断（这将需要额外的 Prompt 和调用）。
*   **LLM Prompt 调整**:
    *   `build_action_resolve_*`: 需要细化，明确指示 LLM 只关注直接结果，并定义好可选的 `direct_consequences` 输出。
    *   `build_event_trigger_*`: 需要细化，确保提供了足够且清晰的上下文（包括格式化后的条件），并明确要求输出 `triggered_event_ids` 列表。
*   **事件触发条件评估**: `RefereeAgent.determine_triggered_event_ids` 目前完全依赖 LLM。是否需要加入一些基础的代码层面的预过滤或后验证逻辑？`format_trigger_condition` 的实现是否足够满足 LLM 理解的需求？
*   **错误处理**: 在 `determine_triggered_event_ids` 和 `_extract_consequences_for_triggered_events` 中需要考虑更健壮的错误处理（例如，LLM 返回格式错误、事件 ID 无效、结局选择失败等）。

*(此文件基于 docs/开发计划_裁判与状态管理.md 生成)*
