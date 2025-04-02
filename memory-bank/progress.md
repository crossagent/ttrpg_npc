# Progress: 玩家角色 (PC) 与选项式交互实现

## 当前状态

*   已完成 Memory Bank 文件阅读和上下文同步。
*   已与用户确认 PC 实现方案和选项式交互流程。
*   已更新 `activeContext.md`。

## 下一步实施计划

1.  **修改数据模型 (`src/models/scenario_models.py`)**:
    *   在 `ScenarioCharacterInfo` 类中**仅添加** `is_playable: bool = Field(False, description="是否可供玩家选择或作为陪玩角色")` 字段。
    *   更新 `Scenario.from_json` 方法以解析新字段。

2.  **更新剧本数据 (`scenarios/default.json`)**:
    *   为 `default.json` 中的角色添加 `is_playable` 字段（需要用户指定哪些角色是 `True`）。

3.  **实现角色选择与 Agent 初始化 (主要在 `src/scripts/cli_runner.py`, `src/engine/game_engine.py`, `src/engine/agent_manager.py`)**:
    *   游戏启动时加载剧本，筛选出所有 `is_playable=True` 的角色。
    *   向玩家展示这些角色，让玩家选择一个作为 PC。
    *   在 `GameState` 中记录玩家选择的 `player_character_id`。

4.  **重命名 Agent**:
    *   将 `src/agents/player_agent.py` 重命名为 `src/agents/companion_agent.py`。
    *   将类 `PlayerAgent` 重命名为 `CompanionAgent`。
    *   更新所有引用该文件和类的地方。

5.  **调整 Agent 管理 (`src/engine/agent_manager.py`)**:
    *   遍历剧本中的所有角色。
    *   如果角色 ID 与 `player_character_id` 匹配，则创建 `PlayerAgent`。
    *   如果角色 ID 与 `player_character_id` **不匹配**，但其 `is_playable` 为 `True`，则创建 `CompanionAgent`。
    *   如果角色的 `is_playable` 为 `False`，则不创建 Agent。

6.  **实现 `PlayerAgent` (`src/agents/player_agent.py` - 新文件)**:
    *   创建新的 `PlayerAgent` 类 (继承 `BaseAgent`)。
    *   实现 `generate_action_options()` 方法，调用 LLM 生成 3 个结构化选项。
    *   (可能需要) 实现接收玩家选择的方法。

7.  **调整游戏循环 (`src/engine/round_manager.py` 或 `src/engine/game_engine.py`)**:
    *   在处理活动 Agent 时，判断 Agent 类型。
    *   如果是 `PlayerAgent`，调用 `generate_action_options()`，展示选项，获取选择，传递给 `RefereeAgent`。
    *   如果是 `CompanionAgent`，调用其行动生成方法，传递给 `RefereeAgent`。

8.  **更新 `systemPatterns.md`**:
    *   反映正确的 Agent 类型 (`PlayerAgent`, `CompanionAgent`) 和交互流程。

## 待办事项 (代码实现阶段)

*   等待用户指定 `default.json` 中各角色的 `is_playable` 值。
*   完成上述所有代码实施步骤。
*   进行测试。

## 已完成 (本次文档更新任务)

*   Memory Bank 同步与计划修订（仅使用 `is_playable`）。
*   `activeContext.md` 更新。
