# Progress: 玩家角色 (PC) 与选项式交互实现

## 当前状态

*   已完成 Memory Bank 文件阅读和上下文同步。
*   已与用户确认 PC 实现方案和选项式交互流程。
*   已更新 `activeContext.md`。

## 下一步实施计划

1.  **修改数据模型 (`src/models/scenario_models.py`)**:
    *   在 `ScenarioCharacterInfo` 类中添加 `is_companion: bool = Field(False, ...)` 和 `is_playable: bool = Field(False, ...)` 字段。
    *   更新 `Scenario.from_json` 方法以解析新字段。

2.  **更新剧本数据 (`scenarios/default.json`)**:
    *   为 `default.json` 中的角色添加 `is_companion` 和 `is_playable` 字段（需要用户指定具体值）。

3.  **实现角色选择流程 (主要在 `src/scripts/cli_runner.py` 和 `src/engine/game_engine.py` / `src/engine/game_state_manager.py`)**:
    *   游戏启动时加载并筛选可玩角色 (`is_playable=True`)。
    *   实现用户选择角色的交互界面。
    *   初始化 `GameState` 时设置 `player_character_id`。

4.  **调整 Agent 管理 (`src/engine/agent_manager.py`)**:
    *   根据 `player_character_id` 创建 `UserAgent` 实例。
    *   根据 `is_companion=True` 创建 `CompanionAgent` 实例。
    *   不为普通 NPC 创建 Agent。

5.  **实现 `UserAgent` (`src/agents/user_agent.py` - 新文件)**:
    *   创建 `UserAgent` 类 (继承 `BaseAgent`)。
    *   实现 `generate_action_options()` 方法，调用 LLM 生成 3 个结构化选项。
    *   (可能需要) 实现接收玩家选择的方法。

6.  **调整游戏循环 (`src/engine/round_manager.py` 或 `src/engine/game_engine.py`)**:
    *   在处理活动 Agent 时，判断 Agent 类型。
    *   如果是 `UserAgent`，调用 `generate_action_options()`，展示选项，获取选择，传递给 `RefereeAgent`。
    *   如果是 `CompanionAgent`，调用其行动生成方法，传递给 `RefereeAgent`。

7.  **更新 `systemPatterns.md`**:
    *   反映新的 Agent 类型和交互流程。

## 待办事项

*   等待用户指定 `default.json` 中各角色的 `is_companion` 和 `is_playable` 值。
*   完成上述所有实施步骤。
*   进行测试。

## 已完成

*   Memory Bank 同步与计划制定。
*   `activeContext.md` 更新。
