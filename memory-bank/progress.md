# Progress: TTRPG NPC 模拟引擎

## 已完成

*   **V4 架构设计**: 定义了新的 Agent 职责 (Narrative, Referee, Player, Companion) 和四阶段回合流程。
*   **核心 Agent 骨架**: 创建了 `NarrativeAgent`, `RefereeAgent`, `PlayerAgent`, `CompanionAgent` 的基本类结构。
*   **回合阶段处理器骨架**: 创建了 `NarrationPhase`, `ActionDeclarationPhase`, `JudgementPhase`, `UpdatePhase` 的基本类结构。
*   **CharacterInstance 模型**: 将角色的运行时状态（属性、技能、健康、位置、物品、知识）整合到 `CharacterInstance` 中，并更新了 `GameState`。
*   **GameState 重构**:
    *   将 `GameState` 模型变得更轻量，移除了 `scenario` 和 `chat_history`，替换为 `scenario_id`。
    *   引入了独立的 `ChatHistoryManager` 按回合管理聊天记录。
    *   更新了相关模块 (`GameStateManager`, `Context Builders`, `PlayerAgent`, `MessageDispatcher`, `GameEngine`) 以适应新的结构和依赖关系。
    *   为 `GameStateManager` 添加了 `save_state` 和 `load_state` 方法用于核心状态的序列化。
*   **核心实现策略确立**: 明确了采用“硬机制与软描述分层”的策略，当前阶段优先利用软描述和 LLM 上下文能力实现动态交互 (详见 `systemPatterns.md`)。
*   **开发焦点明确**: 确定当前开发核心是围绕 NPC 的三大要素：目标 (Goals)、态度 (Attitude)、记忆 (Memory)。
*   **`CharacterInstance` 扩展**: 在 `CharacterInstance` 模型中添加了 `relationship_player`, `attitude_description`, `long_term_goal`, `short_term_goals`, `key_memories`, `status` 字段，为实现 NPC 核心要素奠定基础。
*   **实施即时状态更新架构**:
    *   在 `GameState` 中添加了回合内记录字段 (`current_round_actions`, `current_round_applied_consequences`, `current_round_triggered_events`)。
    *   在 `consequence_models` 中定义了 `AppliedConsequenceRecord` 和 `TriggeredEventRecord`。
    *   在 `GameStateManager` 中添加了内存快照管理 (`create_snapshot`, `store_snapshot`, `get_snapshot`)。
    *   修改了 `ActionDeclarationPhase` 以记录宣告的行动。
    *   修改了 `JudgementPhase` 以应用后果并记录触发的事件。
    *   修改了 `NarrationPhase` 以使用上一回合的快照生成叙事。
    *   修改了 `RoundManager` 以在回合开始时清空记录，在回合结束时存储快照。
    *   移除了 `UpdatePhase`。
*   **修复日志 Bug**:
    *   修复了 `CompanionAgent` 中调用 `ChatHistoryManager` 获取历史消息的 `AttributeError`。
    *   修复了 `BaseConsequenceHandler` 中创建 `AppliedConsequenceRecord` 时缺少必需字段 (`source_description`, `applied_consequence`) 导致的 `ValidationError`。
    *   更新了 `RefereeAgent` 的系统 Prompt，指导其为角色属性/技能生成正确的后果类型，并要求使用有效的实体 ID。
*   **明确架构职责**: 在 `systemPatterns.md` 和 `activeContext.md` 中明确了 `GameStateManager` (机制状态) 和 `ChatHistoryManager` (交互历史、上下文、可见性) 的职责差异。
*   **重构活跃回合判断**: 移除了 `GameState.last_active_round` 字段，并更新 `NarrationPhase` 以通过检查历史回合快照中的活动记录来判断活跃度。(已测试通过)
*   **优化 `NarrationPhase` 活跃度判断逻辑**: 修改了 `src/engine/round_phases/narration_phase.py`，使其只在上一回合有非对话/非等待类型的行动，或者有后果/事件记录时，才认为该回合是活跃的，从而避免在只有对话但没有实质性进展的回合后触发不必要的 DM 叙事。
*   **优化 DM 叙事准确性**:
    *   确认 `CharacterInstance` 中已存在 `visited_locations` 字段。
    *   修改了 `dm_context_builder.py`，使其分析回合内后果和事件，提取关键描述填充到 `narrative_focus_points`。
    *   修改了 `dm_context_builder.py` 生成的 User Prompt，指示 DM Agent 利用 `narrative_focus_points` 聚焦关键变化。
*   **修复 DM 叙事角色描述问题**:
    *   修改了 `src/context/context_utils.py` 中的 `format_current_stage_characters` 函数，使其总是包含玩家和伙伴角色，并结合剧本阶段定义的 NPC，同时移除了会导致问题的角色类型标签输出。
    *   修改了 `src/context/dm_context_builder.py` 中的 `build_narrative_user_prompt` 函数，优化了 Prompt 指令，明确告知 DM 如何处理提供的角色列表和未列出的背景人物（使用通用代称，禁止虚构名字），避免了指令中的标签被直接输出。
*   **实现 CompanionAgent 两阶段思考逻辑**:
    *   在 `src/agents/companion_agent.py` 中添加了 `_trigger_deep_thinking` 方法，用于在决定等待时生成下一回合的短期目标。
    *   在 `src/context/player_context_builder.py` 中添加了相应的 Prompt 构建函数 (`build_goal_generation_system_prompt`, `build_goal_generation_user_prompt`) 并修复了导入错误。
*   **实现游戏状态自动存档与加载**:
    *   定义了 `GameRecord` 模型 (`src/models/game_state_models.py`) 用于存储回合快照和聊天记录到单个 JSON 文件。
    *   修改了 `GameStateManager` 和 `ChatHistoryManager` 的 `save_state`/`load_state` 和 `save_history`/`load_history` 方法以使用 `GameRecord`。
    *   在 `GameEngine` 的回合结束时集成了自动保存逻辑。
    *   修改了 `GameEngine` 和 `cli_runner.py` 以支持通过命令行参数 (`--load-record`, `--load-round`) 加载指定回合的状态和历史记录并继续游戏。

## 进行中 / 下一步 (按优先级)

1.  **实现行动检定与投骰机制**: (当前最高优先级)
    *   **更新 Memory Bank 文档**: (已完成)
    *   **实现检定必要性评估**: 在 `RefereeAgent` 中添加 `assess_check_necessity` 方法。
    *   **实现投骰交互**: 在 `CompanionAgent` 中添加 `simulate_dice_roll`；扩展 `InputHandler` 添加 `get_dice_roll_input`。
    *   **修改判定阶段逻辑**: 在 `JudgementPhase` 中集成检定流程。
    *   **整合投骰结果进行判定**: 修改 `RefereeContextBuilder` 和 `RefereeAgent` 的判定逻辑。
    *   **测试**: 运行游戏进行测试。
2.  **测试游戏存档与加载功能**: (已完成)
    *   运行新游戏，检查 `game_records/` 目录下是否正确生成 `.json` 存档文件。
    *   使用 `--load-record` 和 `--load-round` 参数启动游戏，验证是否能从指定回合正确恢复状态和聊天记录，并继续游戏。
3.  **测试 CompanionAgent 修复**: (优先级调整) 运行游戏，观察 `CompanionAgent` 是否能在等待后生成新目标并继续行动。
4.  **对话生成优化**: (优先级调整)
    *   修改 `DialogueAction` 模型 (`src/models/action_models.py`)，增加 `minor_action: Optional[str]` 字段。
    *   修改 `CompanionAgent` 生成对话的 Prompt (`build_decision_system_prompt`)，要求直接输出对话内容，并鼓励根据情境填充 `minor_action`。
    *   更新 `CompanionAgent` 代码以解析和填充新的 `DialogueAction` 字段。
5.  **更新测试用例**: (优先级调整) 修改或添加测试用例以覆盖新的逻辑和修复。
6.  **实现未完成的 Handler**: (优先级调整)
    *   实现 `TriggerEventHandler`。
    *   将它们添加到 `HANDLER_REGISTRY`。
7.  **更新数据模型 (Models):** (优先级调整)
    *   在 `CharacterTemplate` (`src/models/scenario_models.py`) 和 `CharacterInstance` (`src/models/game_state_models.py`) 中添加用于描述 NPC 内在设定的字段，例如 `values: List[str]`, `likes: List[str]`, `dislikes: List[str]`。
8.  **实现基于 LLM 的关系评估 (RefereeAgent):** (优先级调整)
    *   设计并实现 `RefereeAgent` 中的逻辑：调用 LLM 来解读玩家行动/对话与目标 NPC 内在设定 (`values`, `likes`, `dislikes` 等) 的匹配/冲突程度。
    *   定义 LLM 的输入（玩家行为、情境、NPC 设定、当前关系值）和结构化输出（例如 `RelationshipImpactAssessment` 模型，包含影响类型、强度、原因、建议变化值）。
    *   设计引导 LLM 进行评估的 Prompt。
    *   确定 `RefereeAgent` 如何结合 LLM 的建议和基础规则来最终决定 `relationship_player` 的变化量（可能生成 `CHANGE_RELATIONSHIP` 后果）。
9.  **细化 `Context Builders` 逻辑:** (优先级调整)
    *   实现从 `ChatHistoryManager` 智能提取/总结关键近期互动信息（记忆）的策略。
    *   确保能将 NPC 的目标、态度（关系值、内在设定）、状态 (`status`) 和关键记忆有效整合进给 Agent 的 Prompt。
10. **(已完成)** 实现完整的保存/加载流程。
11. **(稍后)** 检查并清理可能冗余的 `src/models/record_models.py`。

## 已知问题 / 待办

*   需要实现玩家输入处理 (`InputHandler`)。
*   需要完善 `MessageDispatcher` 的消息过滤逻辑。
*   需要添加更全面的错误处理和日志记录。
*   需要设计具体的剧本内容 (`Scenario`) 来测试和展示新机制。
