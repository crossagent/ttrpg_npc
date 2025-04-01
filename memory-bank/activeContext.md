# Active Context: 玩家角色 (PC) 与选项式交互实现

## 当前任务焦点

实现玩家控制角色 (PC) 的完整流程，包括：
1.  在剧本层面明确区分 PC、Agent 驱动的陪玩角色 (Companion) 和普通 NPC。
2.  实现游戏开始时的角色选择机制。
3.  引入代表玩家的 `UserAgent`。
4.  实现 `UserAgent` 的特殊行动逻辑：通过 LLM 生成行动选项（交谈、行动、待机），供玩家选择。
5.  调整游戏循环和 Agent 管理器以支持 `UserAgent` 和 `CompanionAgent` 的不同行为模式。

## 主要目标

*   让玩家能够选择一个剧本中指定的角色进行游戏。
*   玩家的操作通过选择系统生成的选项来完成，而非自由输入。
*   系统能够正确区分并处理 PC、陪玩角色和普通 NPC 的行为。

## 后续步骤

1.  更新 `progress.md` 以反映详细的实施计划。
2.  更新 `systemPatterns.md` 以包含新的 Agent 类型 (`UserAgent`, `CompanionAgent`) 和交互模式。
3.  切换到 ACT MODE 开始编码实现。
