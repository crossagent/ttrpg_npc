# Active Context: 实现属性后果与 Flag 后果分离

## 当前任务焦点

根据最终确定的设计原则，重构游戏引擎以明确区分“属性化影响”和“关键事件/Flag 变化”：

*   **核心原则**:
    *   行动判定后只产生**属性后果**（修改 HP、物品、关系等）。
    *   **Flag** 只能由被触发的 **`ScenarioEvent` 的结局后果**来设置。
    *   `RefereeAgent` 在回合评估时，根据自然语言条件判断活跃的 `ScenarioEvent` 是否被触发。
    *   `UpdatePhase` 在应用所有后果后，检查 `GameState.flags` 是否满足阶段完成条件。

## 主要目标

*   修改数据模型以支持 Flag 存储和 Flag 设置后果。
*   调整 `RefereeAgent` 的职责，使其 `judge_action` 只处理属性后果，而 `determine_triggered_events_and_outcomes` 专注于事件触发判断。
*   修改 `JudgementPhase` 和 `UpdatePhase` 的逻辑，以符合新的后果处理流程。
*   确保剧本中的 `ScenarioEvent` 可以定义设置 Flag 的后果。

## 最终实施计划

1.  **模型层修改**:
    *   `ConsequenceType`: 添加 `UPDATE_FLAG`。
    *   `Consequence`: 添加 `flag_name`, `flag_value`。
    *   `GameState`: 添加 `flags: Dict[str, bool]`。
    *   `Scenario`: 确认 `ScenarioEvent` 的 `trigger_condition` 支持字符串，且 `EventOutcome.consequences` 可以包含 `UPDATE_FLAG` 类型。**不**添加独立的 `flag_definitions`。
    *   `ActionResult`: 只包含属性类后果。
2.  **`RefereeAgent` 修改**:
    *   `judge_action`: 简化，只处理属性后果。
    *   `determine_triggered_events_and_outcomes`: 保持核心功能，输入简化 `ActionResult`，判断活跃 `ScenarioEvent` 触发，输出触发的 `event_id` 和 `outcome_id`。
3.  **`JudgementPhase` 修改**:
    *   先调用 `_resolve_direct_actions` 获取简化 `ActionResult`。
    *   再调用 `determine_triggered_events_and_outcomes` 获取触发的事件列表。
    *   返回包含 `action_results` 和 `triggered_events` 的字典。
4.  **`UpdatePhase` 修改**:
    *   应用 `action_results` 中的属性后果。
    *   处理 `triggered_events`：查找对应 `EventOutcome`，应用其 `consequences`（**这是唯一设置 Flag 的地方**）。
    *   检查阶段完成条件。

## 后续步骤

1.  更新 `progress.md` 以反映此任务。
2.  更新 `systemPatterns.md` 以反映此设计。
3.  更新 `.clinerules` 添加核心设计原则。
4.  完成本文档 (`activeContext.md`) 的更新。
5.  切换到 ACT MODE 开始代码修改。
