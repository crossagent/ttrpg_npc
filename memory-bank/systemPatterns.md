# System Patterns: TTRPG NPC 模拟引擎 V4

## 1. 核心架构概述

本系统采用模块化设计，以 **游戏引擎 (Game Engine)** 为核心协调器，围绕 **游戏状态管理器 (Game State Manager)** 作为单一事实来源 (Single Source of Truth) 构建。核心交互通过 **代理管理器 (Agent Manager)** 调度不同类型的 **代理 (Agents)** 来实现，并通过 **消息分发器 (Message Dispatcher)** 处理通信。**剧本管理器 (Scenario Manager)** 负责结构化的剧本内容，而 **上下文构建器 (Context Builders)** 则负责格式化数据以供代理和展现层使用。

## 2. 主要模块及其职责

*   **游戏引擎 (Game Engine)**:
    *   **职责**: 总调度，管理游戏循环，协调各模块。
    *   **模式**: 中心协调器 (Central Coordinator)。
*   **代理管理器 & 代理 (Agent Manager & Agents)**:
    *   **职责**: 管理所有智能体（玩家、NPC、叙事、裁判）的生命周期和调度。实现“深度思考的 AI 角色”。
    *   **模式**: 代理模式 (Agent Pattern)，面向对象设计。
    *   **核心代理类型**:
        *   **PlayerAgent**: 代表人类玩家控制的角色 (PC)。对应玩家在游戏开始时从 `is_playable=True` 列表中选择的角色 (其 ID 存储在 `GameState.player_character_id`)。其行动不由自身生成，而是通过调用 LLM 生成多个行动选项，由玩家通过展现层选择一个。由 `AgentManager` 在初始化时创建。
        *   **CompanionAgent**: 代表由 AI 驱动的陪玩角色（非玩家控制，但有独立思考和行动能力）。对应未被玩家选择但 `is_playable=True` 的角色。模拟 NPC 思考（感知-思考-行动循环），自主生成行动。由 `AgentManager` 在初始化时创建。（注意：此类由原 `PlayerAgent` 重命名而来）。
        *   **NarrativeAgent (叙事代理)**: 负责生成环境描述、剧情叙述、普通 NPC 的对话和行为描述（原 DM 叙事部分）。不直接代表某个角色。由 `AgentManager` 在初始化时创建。
        *   **RefereeAgent (裁判代理)**: 负责判定 Agent 行动的直接**属性后果**（将利用 `CharacterInstance` 中的属性/技能进行更细致的判定），并在回合评估阶段根据剧本和当前状态判断**活跃事件**是否触发。**不直接设置 Flag**，Flag 只能由事件后果设置。由 `AgentManager` 在初始化时创建。
        *   **普通 NPC**: 对应剧本中 `is_playable=False` 的角色。没有对应的 Agent 实例。其行为由 `NarrativeAgent` 描述或由 `RefereeAgent` 在处理后果时触发。
*   **游戏状态管理器 (Game State Manager)**:
    *   **职责**: 存储和管理核心游戏世界状态（角色实例、环境、物品、事件实例、进度、Flags 等，**不包含**完整的剧本对象和聊天记录）。提供状态的保存和加载接口。应用结构化后果。处理阶段检查与推进。
    *   **模式**: 单一事实来源 (Single Source of Truth)，数据库模式。确保状态更新的原子性。
*   **剧本管理器 (Scenario Manager)**:
    *   **职责**: 加载、存储和提供对当前游戏剧本（`Scenario` 对象）及其内部结构（角色模板、地点、物品、事件定义、故事结构等）的访问。
    *   **模式**: 内容管理系统 (CMS) / 剧本引擎。
*   **聊天记录管理器 (Chat History Manager)**: (新增模块)
    *   **职责**: 独立于 `GameState`，按回合 (`round_number`) 存储和检索所有游戏消息 (`Message`)。提供历史记录的保存和加载接口。
    *   **模式**: 历史记录存储。
*   **消息分发器 (Message Dispatcher)**:
    *   **职责**: 路由和分发消息给对应的 Agent，处理可见性过滤。**将已分发的消息记录到 `ChatHistoryManager`**。
    *   **模式**: 发布/订阅模式 (Publish/Subscribe)，消息队列。
*   **上下文构建器 (Context Builders)**:
    *   **职责**: 将结构化数据格式化为自然语言 或 LLM Prompt。
    *   **模式**: 数据转换层 (Data Transformation Layer)，适配器模式 (Adapter Pattern)。
*   **展现层 (Presentation Layer)**:
    *   **职责**: 用户界面，显示信息，接收输入。
    *   **模式**: MVC/MVP 中的 View 层。

## 3. 关键交互模式与数据流

*   **回合制循环 (阶段驱动)**: 由 `RoundManager` 驱动，按明确定义的顺序执行四个核心阶段。每个阶段的逻辑将被封装在独立的处理器中 (`src/engine/round_phases/`)。
    1.  **叙事阶段 (Narration Phase)**: 处理可选的开场 DM 叙事。(`narration_phase.py`)
    2.  **行动宣告阶段 (Action Declaration Phase)**: 收集所有 `PlayerAgent` 和 `CompanionAgent` 的行动意图 (`PlayerAction`)，不进行判定。(`action_declaration_phase.py`)
    3.  **判定阶段 (Judgement Phase)**:
        *   **步骤一：行动判定**: `RefereeAgent` 利用 `CharacterInstance` 中的属性/技能判定每个宣告行动的成功/失败及其直接**属性后果**。
        *   **步骤二：事件触发判定**: `RefereeAgent` 基于本回合所有行动的属性后果和当前游戏状态（含 flags），判断**活跃的 `ScenarioEvent`** 是否被触发，并确定结局。
        *   **输出**: 包含两部分：所有行动的属性后果列表 (`ActionResult`) 和触发的事件及结局列表。(`judgement_phase.py`)
    4.  **更新阶段 (Update Phase)**:
        *   **应用属性后果**: `GameStateManager` 应用所有 `ActionResult` 中的属性后果（包括对 `CharacterInstance` 属性/技能的修改）。
        *   **应用事件后果**: `GameStateManager` 根据触发事件的结局，应用其后果（**这是唯一设置 Flag 的地方**，也可能包含属性/技能修改）。
        *   **检查阶段推进**: `GameStateManager` 检查 `GameState.flags` 是否满足当前阶段的完成条件。
        *   广播状态变更消息。(`update_phase.py`)
*   **状态驱动**: Agent 的行动宣告、裁判的判定、以及状态更新都基于当前核心游戏状态 (`GameState`)。
*   **剧本访问**: 需要剧本静态信息（如地点描述、物品定义）的组件（如 Context Builders, GameStateManager）通过 `ScenarioManager` 获取，使用 `GameState.scenario_id` 作为索引。
*   **消息驱动**: 模块间通过 `MessageDispatcher` 进行通信。`MessageDispatcher` 将消息分发给相关 Agent，并调用 `ChatHistoryManager` 按回合记录消息。
*   **聊天记录访问**: 需要历史消息（如用于 LLM 上下文）的组件通过 `ChatHistoryManager` 按需获取指定回合范围的消息。
*   **LLM 集成**: 各 Agent 利用 LLM 进行生成、思考和判断，上下文由构建器提供（包含角色属性/技能信息，以及从 `ChatHistoryManager` 获取的相关历史消息）。
*   **结构化自由**: `ScenarioManager` 提供结构化剧本内容。`RefereeAgent` 判断事件触发，`GameStateManager` 检查阶段完成条件。
*   **游戏推进逻辑 (阶段化)**:
    *   **行动宣告阶段**: 收集意图。
    *   **判定阶段**: `RefereeAgent` 先利用角色属性/技能判定行动的属性后果，再判断事件触发。
    *   **更新阶段**: `GameStateManager` 应用属性后果（含属性/技能修改），然后应用事件后果（含 Flag 设置和可能的属性/技能修改），最后检查阶段推进。
    *   **叙事阶段**: `NarrativeAgent` (如果需要) 负责开场叙事。

## 4. 设计原则

*   **模块化与高内聚低耦合**: 各模块职责清晰，交互明确。
*   **单一职责原则**: 例如将 DM 拆分为叙事和裁判代理。
*   **数据驱动**: 游戏状态和剧本数据是核心。
*   **可扩展性**: 模块化设计便于未来添加新类型的代理、规则或交互方式。

*(此文件基于 docs/重要模块设计.md 生成)*
