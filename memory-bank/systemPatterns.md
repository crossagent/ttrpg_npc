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
        *   **RefereeAgent (裁判代理)**: 负责解析所有 Agent（包括 `PlayerAgent` 选择的行动和 `CompanionAgent` 生成的行动）的意图、判定规则、判断事件触发、生成结构化状态变更指令（原 DM 规则部分）。不直接代表某个角色。由 `AgentManager` 在初始化时创建。
        *   **普通 NPC**: 对应剧本中 `is_playable=False` 的角色。没有对应的 Agent 实例。其行为由 `NarrativeAgent` 描述或由 `RefereeAgent` 在处理后果时触发。
*   **游戏状态管理器 (Game State Manager)**:
    *   **职责**: 存储和管理游戏世界状态（角色、环境、物品、事件进展等），应用结构化后果，并处理游戏阶段的检查与推进。
    *   **模式**: 单一事实来源 (Single Source of Truth)，数据库模式。确保状态更新的原子性。
*   **剧本管理器 (Scenario Manager)**:
    *   **职责**: 管理结构化剧本内容（主线、支线、事件、场景、NPC 背景/目标）。实现“结构化的自由叙事”。
    *   **模式**: 内容管理系统 (CMS) / 剧本引擎。包含阶段推进 (`completion_criteria`) 和事件后果 (`consequence`) 的结构化定义。
*   **消息分发器 (Message Dispatcher)**:
    *   **职责**: 路由和分发消息，处理可见性过滤，连接逻辑层与展现层，管理消息历史。
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
        *   **事件优先**: `RefereeAgent` 首先检查宣告的行动是否触发剧本中的**重大事件**。
        *   若触发事件，则确定事件结局，该结局优先。
        *   若未触发事件，则 `RefereeAgent` 判定行动的**直接结果** (成功/失败/直接后果)。
        *   输出为事件结局信息**或**行动结果列表。(`judgement_phase.py`)
    4.  **更新阶段 (Update Phase)**:
        *   根据判定阶段的输出，提取所有相关后果 (Consequence)。
        *   `GameStateManager` 应用后果，更新游戏状态。
        *   `GameStateManager` 检查并尝试推进剧本阶段。
        *   广播状态变更消息。(`update_phase.py`)
*   **状态驱动**: Agent 的行动宣告、裁判的判定（包括事件触发和行动结果）、以及状态更新都基于当前游戏状态 (`GameState`)。
*   **消息驱动**: 模块间通过消息分发器进行通信，广播行动宣告、判定结果、状态更新等信息。
*   **LLM 集成**: `NarrativeAgent` (叙事阶段)、`PlayerAgent`/`CompanionAgent` (行动宣告阶段)、`RefereeAgent` (判定阶段) 利用 LLM 进行生成、思考和判断，上下文由构建器提供。
*   **结构化自由**: 剧本管理器提供事件及其触发条件/结局/后果。判定阶段优先检查事件触发，确保关键剧情节点的影响力，同时允许在非关键时刻进行常规的行动判定。
*   **游戏推进逻辑 (阶段化)**:
    *   **行动宣告阶段**: 收集意图。
    *   **判定阶段**: `RefereeAgent` 负责核心判定逻辑（事件优先）。
    *   **更新阶段**: `GameStateManager` 负责应用后果和推进剧本阶段。
    *   **叙事阶段**: `NarrativeAgent` (如果需要) 负责开场叙事。

## 4. 设计原则

*   **模块化与高内聚低耦合**: 各模块职责清晰，交互明确。
*   **单一职责原则**: 例如将 DM 拆分为叙事和裁判代理。
*   **数据驱动**: 游戏状态和剧本数据是核心。
*   **可扩展性**: 模块化设计便于未来添加新类型的代理、规则或交互方式。

*(此文件基于 docs/重要模块设计.md 生成)*
