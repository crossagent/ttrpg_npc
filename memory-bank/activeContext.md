# Active Context: 玩家角色 (PC) 与选项式交互实现

## 当前任务焦点

实现玩家控制角色 (PC) 的完整流程（基于仅使用 `is_playable` 标志的修订策略），包括：
1.  在剧本层面使用 `is_playable` 标志区分潜在的 PC/Companion 和普通 NPC。
2.  实现游戏开始时的角色选择机制（从 `is_playable=True` 的角色中选择）。
3.  重命名当前的 `PlayerAgent` 为 `CompanionAgent` (代表 AI 陪玩，即未被玩家选择的 `is_playable=True` 角色)。
4.  引入新的 `PlayerAgent` (代表人类玩家选择的 PC)。
5.  实现 `PlayerAgent` 的特殊行动逻辑：通过 LLM 生成行动选项（交谈、行动、待机），供玩家选择。
6.  调整游戏循环和 Agent 管理器以支持 `PlayerAgent` (选项式) 和 `CompanionAgent` (自主行动) 的不同行为模式，并根据 `is_playable` 和玩家选择来创建正确的 Agent 实例。

## 主要目标

*   让玩家能够从剧本中标记为 `is_playable=True` 的角色中选择一个进行游戏。
*   玩家的操作通过选择系统生成的选项来完成，而非自由输入。
*   系统能够根据 `is_playable` 标志和玩家选择，正确创建并处理 PC (`PlayerAgent`)、陪玩角色 (`CompanionAgent`) 的行为，并区分普通 NPC。

## 后续步骤 (本次文档更新任务)

1.  更新 `progress.md` 以反映修订后的实施计划（仅使用 `is_playable`）。
2.  更新 `systemPatterns.md` 以反映修订后的 Agent 创建逻辑和描述（仅使用 `is_playable`）。
3.  完成本文档 (`activeContext.md`) 的更新。
4.  向用户报告文档更新完成。

*(注意：实际的代码修改将在后续任务中进行)*
