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
        *   **CompanionAgent**: 代表由 AI 驱动的陪玩角色（非玩家控制，但有独立思考和行动能力）。对应未被玩家选择但 `is_playable=True` 的角色。模拟 NPC 思考（感知-思考-行动循环），自主生成行动。**能够响应 `RefereeAgent` 的请求模拟投骰结果 (例如通过 `simulate_dice_roll` 方法)**。由 `AgentManager` 在初始化时创建。（注意：此类由原 `PlayerAgent` 重命名而来）。
        *   **NarrativeAgent (叙事代理)**: 负责生成环境描述、剧情叙述、普通 NPC 的对话和行为描述（原 DM 叙事部分）。不直接代表某个角色。由 `AgentManager` 在初始化时创建。
        *   **RefereeAgent (裁判代理)**:
            *   **核心职责**: 判定 Agent 行动的成功/失败、直接后果（如属性变化），以及基于当前状态和行动后果判断 `ScenarioEvent` 是否触发及结局。**不直接设置 Flag**，Flag 只能由事件后果设置。
            *   **检定机制**:
                *   新增 `assess_check_necessity` 方法：在判定前评估行动是否需要进行检定（基于风险、后果严重性等，通过LLM 推断）。
                *   若需要检定，负责确定检定的属性，并向相关 Agent 请求投骰：
                    *   对 `PlayerAgent`: 通过 `GameEngine` 和 `InputHandler` 请求玩家输入投骰结果。
                    *   对 `CompanionAgent`: 调用其 `simulate_dice_roll` 方法获取模拟结果。
                *   将获取的投骰结果整合到最终判定的上下文中（由 `RefereeContextBuilder` 处理）。
            *   由 `AgentManager` 在初始化时创建。
        *   **普通 NPC**: 对应剧本中 `is_playable=False` 的角色。没有对应的 Agent 实例。其行为由 `NarrativeAgent` 描述或由 `RefereeAgent` 在处理后果时触发。
*   **游戏状态管理器 (Game State Manager)**:
    *   **职责**: 存储和管理核心游戏的**机制状态**和**全局信息**（角色属性、技能、健康、位置、物品、事件实例、进度、Flags 等），作为当前世界的“快照”。是规则判断和应用**硬性后果**的基础。**负责即时应用**经过校验的后果到游戏状态。提供状态的保存和加载接口（包括回合快照）。处理阶段检查与推进。
    *   **模式**: 单一事实来源 (Single Source of Truth)，数据库模式。
    *   **后果处理**: `GameStateManager` 负责通过调用注册的 **后果处理器 (Consequence Handlers)** 来应用状态变更。
        *   **核心机制**: 通过 `GameStateManager` 分发给相应的 `Consequence Handler` 来完成，确保了处理逻辑的一致性。
    *   **后果模型**: 后果使用 Pydantic 的 **Discriminated Unions** (`AnyConsequence` in `src/models/consequence_models.py`) 进行建模。每种 `ConsequenceType` 对应一个具体的模型（如 `AddItemConsequence`），只包含该类型必需的字段，由 `type` 字段区分。这提供了类型安全和精确的数据结构。
    *   **注意**: `GameState` 模型包含临时的回合作用域字段（如 `current_round_actions`, `current_round_applied_consequences`, `current_round_triggered_events`），用于回合结束快照。这些字段在新回合开始时清空。
*   **后果处理器 (Consequence Handlers)**:
    *   **位置**: `src/engine/consequence_handlers/`
    *   **职责**: 实现具体的后果应用逻辑和记录逻辑。每个 Handler 继承自 `BaseConsequenceHandler` 并处理一种 `ConsequenceType`。
    *   **接口**: `apply` 方法接收 `AnyConsequence` 类型的参数，Handler 内部可以直接访问对应具体后果类型的字段。
    *   **模式**: 策略模式 (Strategy Pattern)。通过注册表 (`HANDLER_REGISTRY` in `__init__.py`) 进行分发。
*   **剧本管理器 (Scenario Manager)**:
    *   **职责**: 加载、存储和提供对当前游戏剧本（`Scenario` 对象）及其内部结构（角色模板、地点、物品、事件定义、故事结构等）的访问。
    *   **模式**: 内容管理系统 (CMS) / 剧本引擎。
*   **聊天记录管理器 (Chat History Manager)**: (新增模块)
    *   **职责**: 独立于 `GameState`，按回合 (`round_number`) 存储和检索所有游戏**交互历史**（对话、行动消息 `Message`）。提供必要的**上下文信息**，并处理**信息可见性**逻辑。是 Agent 理解对话流、进行关系评估和生成符合情境反应的关键。提供历史记录的保存和加载接口。
    *   **模式**: 历史记录存储，上下文提供者。
*   **消息分发器 (Message Dispatcher)**:
    *   **职责**: 路由和分发消息给对应的 Agent，处理可见性过滤。**将已分发的消息记录到 `ChatHistoryManager`**。
    *   **模式**: 发布/订阅模式 (Publish/Subscribe)，消息队列。
*   **上下文构建器 (Context Builders)**:
    *   **职责**: 将结构化的 `GameState`、`ChatHistory` 和 `Scenario` 数据格式化为自然语言或 LLM Prompt，供 Agent 使用。**核心职责之一是为 `NarrativeAgent` 准备叙事焦点信息。**
    *   **模式**: 数据转换层 (Data Transformation Layer)，适配器模式 (Adapter Pattern)。
    *   **DM 上下文构建 (`dm_context_builder.py`)**:
        *   访问 `GameState` 中的 `current_round_applied_consequences` 和 `current_round_triggered_events`。
        *   分析这些记录，识别关键变化（如首次地点进入、事件触发、关键 Flag 更新）。
        *   根据识别出的变化，从 `GameState` 或 `Scenario` 数据中**提取**对应的描述性文本或摘要。
        *   将提取出的文本填充到传递给 `NarrativeAgent` 的 `narrative_focus_points` 字段中。
*   **展现层 (Presentation Layer)**:
    *   **职责**: 用户界面，显示信息，接收输入。
    *   **模式**: MVC/MVP 中的 View 层。

## 3. 关键交互模式与数据流

*   **回合制循环 (阶段驱动)**: 由 `RoundManager` 驱动，按明确定义的顺序执行核心阶段。每个阶段的逻辑将被封装在独立的处理器中 (`src/engine/round_phases/`)。
    1.  **叙事阶段 (Narration Phase)**: 处理可选的开场 DM 叙事，可能基于上一回合的 `GameState` 快照进行总结。(`narration_phase.py`)
    2.  **行动宣告阶段 (Action Declaration Phase)**: 收集所有 `PlayerAgent` 和 `CompanionAgent` 的行动意图 (`PlayerAction`)，并将这些行动记录到当前 *实时* `GameState` 的临时字段 `current_round_actions` 中。(`action_declaration_phase.py`)
    3.  **判定与应用阶段 (Judgement & Application Phase)**: (原 Judgement Phase 扩展)
        *   **检定必要性评估 (Check Necessity Assessment)**: (新增步骤) 对于每个宣告的行动 (`PlayerAction`)，`RefereeAgent` 首先调用 `assess_check_necessity` 方法判断是否需要进行检定。
        *   **跳过检定**: 如果不需要检定，则可能直接判定成功或产生叙述性后果，跳过后续投骰和详细判定。
        *   **执行检定与判定 (Check Execution & Judgement)**: 如果需要检定：
            *   `RefereeAgent` 确定检定的属性。
            *   `RefereeAgent` 请求投骰 (向 `PlayerAgent` 通过 `InputHandler` 或向 `CompanionAgent` 直接调用)。
            *   `RefereeAgent` 接收投骰结果。
            *   `RefereeAgent` 结合投骰结果、角色能力、难度等因素，判定行动的最终成功/失败和直接后果（如属性变化）。同时，基于当前状态和行动后果判断 `ScenarioEvent` 是否触发及结局。
        *   **校验**: 对判定的后果和事件进行合法性校验（结构校验、逻辑校验）。
        *   **即时应用**: 对于通过校验的后果和事件，**立即** 调用 `GameStateManager.apply_consequences()` 方法。该方法会查找并调用相应的 **后果处理器 (Consequence Handler)** 来修改 *实时* `GameState`。
        *   **记录已应用变更**: **后果处理器 (Consequence Handler)** 在成功应用后果后，负责创建 `AppliedConsequenceRecord` 并添加到 *实时* `GameState` 的 `current_round_applied_consequences` 列表中。`JudgementPhase` 负责记录触发的事件 (`TriggeredEventRecord`) 到 `current_round_triggered_events`。(`judgement_phase.py`)
    4.  **回合结束处理 (End of Round Processing)**: (由 `RoundManager` 或 `GameEngine` 触发)
        *   **创建快照**: 对当前的 *实时* `GameState`（包含最终状态和 `current_round_...` 列表）进行**深拷贝**，生成该回合的结束状态快照。
        *   **存储快照**: 将快照与回合号关联并存储（例如，存储在内存中的字典或持久化）。
        *   **准备下一回合**: 清空 *实时* `GameState` 中的 `current_round_...` 临时字段。
*   **状态驱动**: Agent 的行动宣告、裁判的判定都基于当前的 *实时* `GameState`。状态变更是即时生效的。
*   **剧本访问**: 需要剧本静态信息（如地点描述、物品定义）的组件（如 Context Builders, GameStateManager）通过 `ScenarioManager` 获取，使用 `GameState.scenario_id` 作为索引。
*   **消息驱动**: 模块间通过 `MessageDispatcher` 进行通信。`MessageDispatcher` 将消息分发给相关 Agent，并调用 `ChatHistoryManager` 按回合记录消息。
*   **聊天记录访问**: 需要历史消息（如用于 LLM 上下文）的组件通过 `ChatHistoryManager` 按需获取指定回合范围的消息。
*   **LLM 集成**: 各 Agent 利用 LLM 进行生成、思考和判断。上下文由构建器提供，包含角色属性/技能、从 `ChatHistoryManager` 获取的相关历史消息，以及（对 `NarrativeAgent`）由 `dm_context_builder` 提取的 `narrative_focus_points`。
*   **结构化自由**: `ScenarioManager` 提供结构化剧本内容。`RefereeAgent` 判断事件触发，`GameStateManager` 检查阶段完成条件。
*   **游戏推进逻辑 (即时应用)**:
    *   **叙事阶段**: `NarrativeAgent` 基于上一回合的 `GameState` 快照和由 `dm_context_builder` 准备的 `narrative_focus_points` 进行总结叙事。
    *   **行动宣告阶段**: 收集意图 (`PlayerAction`) 并记录到当前 `GameState` 的 `current_round_actions`。
    *   **判定与应用阶段**: `RefereeAgent` 评估检定必要性 -> (可选) 请求并获取投骰结果 -> `RefereeAgent` 判定后果和事件 -> 校验 -> **立即**调用 `GameStateManager.apply_consequences()` -> `GameStateManager` 分发给对应的 **后果处理器 (Handler)** 应用到当前 `GameState` 并记录 `AppliedConsequenceRecord` -> `JudgementPhase` 记录 `TriggeredEventRecord`。
    *   **回合结束**: 创建当前 `GameState` 快照并存储，清空临时记录字段。

## 4. 设计原则

*   **模块化与高内聚低耦合**: 各模块职责清晰，交互明确。
*   **单一职责原则**: 例如将 DM 拆分为叙事和裁判代理。
*   **数据驱动**: 游戏状态和剧本数据是核心。
*   **可扩展性**: 模块化设计便于未来添加新类型的代理、规则或交互方式。

## 5. 核心实现策略：硬机制与软描述分层

为了平衡游戏核心规则的稳定性和 LLM 驱动的动态交互的灵活性，系统采用分层实现策略：

*   **硬机制 (Hard Mechanisms):**
    *   **范围:** 负责游戏的基础规则、结构、核心叙事进展、关卡谜题解决、战斗系统（如果引入）、核心资源管理和关键状态转换。确保游戏的可玩性、一致性和长期目标的达成。
    *   **实现:** 主要通过明确的数据结构（如 `GameState.flags`, `CharacterInstance` 的数值属性）、预定义的逻辑（如 `RefereeAgent` 中的判定规则、`ScenarioEvent` 的触发条件和后果）、以及精确的状态管理（`GameStateManager`）来实现。
    *   **特点:** 可靠、可预测、易于调试，构成游戏体验的骨架。

*   **软描述 (Soft Descriptions):**
    *   **范围:** 负责营造沉浸感、塑造角色个性、驱动 NPC 的日常行为和非关键决策、体现人际关系的微妙之处、生成丰富的环境描述和对玩家行动的非机械性反应。让世界和角色感觉“活”起来。
    *   **实现:** 主要依赖 LLM 的自然语言理解和生成能力。通过精心设计的 Prompts、由 `Context Builders` 提供的包含近期事件和宏观状态（如 `CharacterInstance.status` 字段）的高质量上下文，引导 `CompanionAgent` 和 `NarrativeAgent` 生成符合情境的行为、对话和描述。
    *   **特点:** 灵活、动态、能产生意想不到的细节和交互，构成游戏体验的血肉。
    *   **当前阶段侧重:** 在 Demo 和早期开发阶段，将更侧重利用软描述和 LLM 上下文理解能力来快速实现动态交互，对于非核心、非关键的状态变化（如 NPC 的短期情绪、临时警觉等），优先使用宏观状态字段 (`CharacterInstance.status`) 和上下文传递，而非立即创建复杂的硬编码 Flag 和检测逻辑。

*   **协同工作:** 硬机制提供稳定的框架和规则边界，软描述在此框架内填充生动的细节和动态的交互。例如，硬机制判定行动成功并更新核心状态，软描述则负责将这个结果生动地演绎出来，并影响 NPC 的后续（非关键）行为和对话。

*(此文件基于 docs/重要模块设计.md 生成，并补充了核心实现策略)*
