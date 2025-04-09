# Active Context: 实现行动检定与投骰机制

## 当前工作焦点: 实现行动检定与投骰机制

*   **背景**: 之前 `CompanionAgent` 会因为没有短期目标或目标不可行而陷入无限等待的循环。
*   **已完成任务**: 修复了 `CompanionAgent` 的行动宣告逻辑，完整实现了两阶段思考模式：
    1.  **快速判断 (Fast Check)**: (已有逻辑)
        *   检查 `CharacterInstance.short_term_goals` 是否存在。
        *   若存在，使用轻量级 LLM 调用 (`_check_plan_feasibility`) 进行可行性判断。
        *   若无目标或 LLM 判断不可行，则宣告 `WaitAction`。
    2.  **深度思考 / 目标生成 (Deep Thinking / Goal Generation)**: (新增逻辑)
        *   **触发**: 当快速判断失败并决定执行 `WaitAction` 时触发。
        *   **实现**: 在 `CompanionAgent` 中添加了 `_trigger_deep_thinking` 方法。
        *   **功能**: 调用 LLM（使用新增的 `build_goal_generation_...` prompts）生成新的 `short_term_goals`。
        *   **应用**: 生成的目标通过 `UpdateCharacterAttributeConsequence` **立即应用**到 `GameState`，供**下一回合**的快速判断使用。
    3.  **行动选择 (Action Selection)**: (已有逻辑)
        *   若快速判断成功，则继续执行现有的行动选择逻辑（调用 LLM 使用 `build_decision_...` prompts 生成具体 `DialogueAction`, `MoveAction` 等）。
*   **目标**: 解决了 `CompanionAgent` 无限等待的问题，使其在需要时能够主动规划下一步目标。
*   **实现游戏状态自动存档与加载**: (刚刚完成)
    *   **目标**: 方便调试，允许从任意回合的状态继续游戏。
    *   **实现**:
        *   在 `src/models/game_state_models.py` 中定义了 `GameRecord` 模型，用于存储单局游戏的所有回合快照 (`GameState`) 和聊天记录 (`List[Message]`) 到单个 JSON 文件。
        *   修改了 `src/engine/game_state_manager.py`：
            *   `save_state` 方法现在接收 `GameState` 快照和记录文件路径，读取现有 `GameRecord`（如果存在），添加/更新快照，然后写回整个 `GameRecord`。
            *   `load_state` 方法现在接收记录文件路径和目标回合数，读取 `GameRecord`，提取指定回合的 `GameState` 快照并设置为当前状态。
        *   修改了 `src/engine/chat_history_manager.py`：
            *   添加 `save_history` 方法，接收记录文件路径、回合数和当前回合消息列表，读取现有 `GameRecord`，添加/更新聊天记录，然后写回整个 `GameRecord`。
            *   添加 `load_history` 方法，接收记录文件路径和目标回合数，读取 `GameRecord`，加载到目标回合为止的所有聊天记录以初始化管理器。
        *   修改了 `src/engine/game_engine.py`：
            *   在 `run_game` 方法的回合循环结束后，调用 `game_state_manager.save_state` 和 `chat_history_manager.save_history` 将当前回合的状态和聊天记录保存到 `game_records/record_YYMMDD_HHMMSS.json` 文件。
            *   添加了 `start_from_loaded_state` 方法，用于接收预加载的管理器和状态，并从指定回合开始游戏循环。
            *   重构了 `run_game`，将核心循环提取到 `_run_game_loop` 方法。
        *   修改了 `src/scripts/cli_runner.py`：
            *   添加了 `--load-record <path>` 和 `--load-round <number>` 命令行参数。
            *   在检测到加载参数时，初始化必要的管理器，调用 `load_state` 和 `load_history`，然后调用 `engine.start_from_loaded_state` 启动游戏。

## 近期变更 (先前)

*   修改了 `src/models/game_state_models.py`：移除 `scenario`, `chat_history`, `item_states` 等字段，添加 `scenario_id`。清理冗余模型。
*   创建了 `src/engine/chat_history_manager.py`。
*   修改了 `src/engine/game_state_manager.py`：移除对 `game_state.scenario` 的访问，添加 `save_state`/`load_state`。
*   修改了 `src/context/context_utils.py`：添加 `scenario_manager` 参数，更新剧本访问逻辑。
*   修改了 `src/context/player_context_builder.py`：添加 `scenario_manager` 参数，更新剧本访问逻辑。
*   修改了 `src/agents/player_agent.py`：添加 `scenario_manager` 依赖，更新剧本访问逻辑。
*   修改了 `src/communication/message_dispatcher.py`：添加 `chat_history_manager` 和 `game_state_manager` 依赖，更新消息记录和历史获取逻辑。
*   修改了 `src/engine/game_engine.py`：实例化 `ChatHistoryManager` 并正确注入依赖。
*   **修改了 `src/models/game_state_models.py`**: 为 `CharacterInstance` 添加了 `relationship_player`, `attitude_description`, `long_term_goal`, `short_term_goals`, `key_memories`, `status` 字段，以支持 NPC 核心要素（态度、目标、记忆、状态）。
*   **修复了 `src/agents/companion_agent.py`**: 将 `get_messages_for_round` 调用修正为 `get_messages`。
*   **修复了 `src/engine/consequence_handlers/base_handler.py`**: 在 `_create_record` 中添加了 `source_description` 和 `applied_consequence` 字段，以解决 `ValidationError`。
*   **更新了 `src/context/referee_context_builder.py`**: 修改了 `build_action_resolve_system_prompt`，指导 LLM 为角色属性/技能生成正确的后果类型 (`UPDATE_CHARACTER_ATTRIBUTE` / `UPDATE_CHARACTER_SKILL`)。
*   **更新了 `memory-bank/systemPatterns.md`**: 明确了 `GameStateManager` 和 `ChatHistoryManager` 的职责差异。
*   **更新了 `src/context/referee_context_builder.py`**: 再次修改 `build_action_resolve_system_prompt`，添加明确指令要求 LLM 必须使用有效的实体 ID。
*   **重构后果处理模型**:
    *   修改了 `src/models/consequence_models.py`，使用 Pydantic Discriminated Unions 定义了 `AnyConsequence`，为每种后果类型创建了精确的模型。
    *   修改了 `src/engine/consequence_handlers/base_handler.py`，更新 `apply` 和 `_create_record` 方法以接受 `AnyConsequence`。
    *   修改了 `src/engine/consequence_handlers/` 目录下的所有具体 Handler 实现，使其适应新的模型和基类接口。
    *   修改了 `src/agents/referee_agent.py` 中解析 LLM 返回后果的部分，使用 `AnyConsequence.model_validate`。
*   **移除了 `GameState.last_active_round`**: 不再显式跟踪最后一个活跃回合。
*   **更新了 `NarrationPhase` 活跃度判断**: 现在通过检查历史回合快照中的实际活动记录（行动、后果、事件）来判断是否需要触发叙事。
*   **优化了 `NarrationPhase` 活跃度判断逻辑**: 修改了 `src/engine/round_phases/narration_phase.py`，使其只在上一回合有非对话/非等待类型的行动，或者有后果/事件记录时，才认为该回合是活跃的，从而避免在只有对话但没有实质性进展的回合后触发不必要的 DM 叙事。
*   **修复 DM 叙事角色描述问题**: (近期完成)
    *   修改了 `scenarios/default.json`，调整了可玩角色数量，并确保剧本阶段定义只包含相关 NPC。添加了新 NPC `char_006` (老王) 用于测试。修复了 `char_003` 的 `is_playable` 状态错误。
    *   修改了 `src/context/context_utils.py` (`format_current_stage_characters`)，确保其包含玩家、伙伴和阶段 NPC，并移除了输出中的角色类型标签。
    *   修改了 `src/context/dm_context_builder.py` (`build_narrative_user_prompt`)，优化了 Prompt 指令，明确了对角色列表和背景人物的处理规则。
*   **实现 CompanionAgent 两阶段思考**: (刚刚完成)
    *   在 `src/agents/companion_agent.py` 中添加了 `_trigger_deep_thinking` 方法，用于在决定等待时生成下一回合的短期目标。
    *   在 `src/context/player_context_builder.py` 中添加了相应的 Prompt 构建函数 (`build_goal_generation_system_prompt`, `build_goal_generation_user_prompt`) 并修复了导入错误。

## 下一步计划 (实现行动检定与投骰机制)

1.  **更新 Memory Bank 文档**: (当前正在进行)
    *   更新 `systemPatterns.md` 以反映新的判定流程和 Agent 职责。(已完成)
    *   更新 `activeContext.md` (本文件) 以反映新的工作焦点和计划。(当前步骤)
    *   更新 `progress.md` 以添加新的开发任务。
2.  **实现检定必要性评估**:
    *   在 `src/agents/referee_agent.py` 中添加 `assess_check_necessity(action, game_state)` 方法，使用 LLM 推断是否需要检定，并确定检定属性。
3.  **实现投骰交互**:
    *   在 `src/agents/companion_agent.py` 中添加 `simulate_dice_roll(dice_type)` 方法。
    *   扩展 `src/io/input_handler.py` (`UserInputHandler` 和 `CliInputHandler`)，添加 `get_dice_roll_input` 方法来处理玩家投骰输入。
4.  **修改判定阶段逻辑**:
    *   在 `src/engine/round_phases/judgement_phase.py` 中，在处理每个 `PlayerAction` 时，调用 `RefereeAgent.assess_check_necessity`。
    *   根据评估结果，决定是跳过检定还是继续执行检定流程。
    *   如果需要检定，调用相应的方法获取投骰结果 (从 `InputHandler` 或 `CompanionAgent`)。
5.  **整合投骰结果进行判定**:
    *   修改 `src/context/referee_context_builder.py` 中的 `build_action_resolve_system_prompt`，将投骰结果、检定属性和角色能力纳入上下文。
    *   修改 `src/agents/referee_agent.py` 中的判定逻辑，使其能够利用包含投骰结果的新上下文进行最终判定。
6.  **测试**: 运行游戏，测试不同场景下的检定触发、投骰交互和判定结果。
7.  **(后续)** 测试游戏存档与加载功能。
8.  **(后续)** 测试 CompanionAgent 修复。
9.  **(后续)** 对话生成优化。
10. **(后续)** 审阅 `RefereeAgent` Prompt 和数据源。
11. **(后续)** 检查数据源。

## 待解决/考虑事项

*   如何量化评估 Agent Prompt 优化的效果？可能需要设计特定的测试场景。
*   在优化 Prompt 时，如何在提高智能表现和控制 LLM 成本/延迟之间取得平衡？

## 架构理解深化 (保持不变)

*   **明确职责**: 进一步明确了 `GameState` (核心机制状态、全局信息、世界快照) 与 `ChatHistoryManager` (交互历史、上下文、信息可见性) 的不同职责和重要性。`GameState` 是硬性规则和后果的基础，而 `ChatHistoryManager` 为 Agent 理解对话流、进行关系评估和生成符合情境的反应提供关键上下文。保持此分离对实现智能交互至关重要。
*   **叙事焦点传递**: 确定了通过分析 `GameState` 回合记录，由 `dm_context_builder` 提取具体文本，再传递给 DM Agent 的模式，以提高叙事准确性。
