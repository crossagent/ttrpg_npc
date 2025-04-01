# Active Context: 玩家角色 (PC) 与选项式交互实现

## 当前任务焦点

实现玩家控制角色 (PC) 的完整流程，包括：
1.  在剧本层面明确区分 PC、Agent 驱动的陪玩角色 (Companion) 和普通 NPC。
2.  实现游戏开始时的角色选择机制。
3.  重命名当前的 `PlayerAgent` 为 `CompanionAgent` (代表 AI 陪玩)。
4.  引入新的 `PlayerAgent` (代表人类玩家)。
5.  实现 `PlayerAgent` 的特殊行动逻辑：通过 LLM 生成行动选项（交谈、行动、待机），供玩家选择。
6.  调整游戏循环和 Agent 管理器以支持 `PlayerAgent` 和 `CompanionAgent` 的不同行为模式。

## 主要目标

*   让玩家能够选择一个剧本中指定的角色进行游戏。
*   玩家的操作通过选择系统生成的选项来完成，而非自由输入。
*   系统能够正确区分并处理 PC (`PlayerAgent`)、陪玩角色 (`CompanionAgent`) 和普通 NPC 的行为。

## 后续步骤

1.  更新 `progress.md` 以反映详细的实施计划。
2.  更新 `progress.md` 以反映详细的实施计划（包含重命名步骤）。
3.  更新 `systemPatterns.md` 以包含正确的 Agent 类型 (`PlayerAgent`, `CompanionAgent`) 和交互模式。
4.  切换到 ACT MODE 开始编码实现。
