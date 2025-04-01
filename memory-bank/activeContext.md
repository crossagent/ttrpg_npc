# Active Context: 裁判代理增强与游戏状态管理

## 1. 当前工作焦点

当前的开发重点是增强 **裁判代理 (Referee Agent)** 和 **游戏状态管理器 (Game State Manager)** 的功能，以实现更完善的事件触发、结构化后果处理和游戏进程管理，从而更好地支持“结构化的自由叙事”核心特性。

## 2. 近期主要任务 (开发计划)

按照 `docs/开发计划_裁判与状态管理.md` 文件规划，后续步骤分为四个阶段：

*   **阶段一：数据模型定义与完善 (Models Refinement)**
    *   定义结构化的 `Consequence` 模型。
    *   调整 `EventOutcome` 以包含 `List[Consequence]`。
    *   为 `StoryStage` 添加 `completion_criteria` 字段。
    *   为 `GameState` 添加 `active_event_ids` 列表。
    *   调整 `ActionResult` 以使用 `List[Consequence]` 替换 `state_changes`。
*   **阶段二：裁判代理增强 (Referee Agent Enhancement)**
    *   更新 `judge_action` 方法以返回结构化后果。
    *   实现基于 `active_event_ids` 的事件触发检查逻辑。
    *   实现基于触发事件确定 `possible_outcomes` 的逻辑。
    *   实现提取和整合行动本身及事件后果到 `ActionResult.consequences` 的逻辑。
    *   调整 LLM Prompts，让其专注于判断和叙述，后果处理由代码完成。
*   **阶段三：游戏状态管理器增强 (Game State Manager Enhancement)**
    *   实现核心方法 `apply_consequences` 来处理后果列表。
    *   重构/移除旧的 `update_state`。
    *   实现 `check_item`、`check_stage_completion`、`advance_stage` 和 `update_active_events` 等核心状态管理和进程推进方法。
    *   更新初始化逻辑以调用 `update_active_events`。
*   **阶段四：集成与测试 (Integration and Testing)**
    *   将修改后的模块整合回 `GameEngine` 的游戏循环。
    *   编写单元测试和集成测试。

## 3. 当前决策与考虑

*   需要确定结构化后果 (`Consequence`) 模型的具体实现细节（例如，放在哪个文件，具体的类定义）。
*   需要设计裁判代理中事件触发条件的评估逻辑（如何将 `action` 与 `trigger_condition` 匹配）。
*   需要调整裁判代理的 LLM Prompt，以适应新的职责划分。

*(此文件基于 docs/开发计划_裁判与状态管理.md 生成)*
