# Active Context: 完成 DM 叙事角色描述修复，准备优化其他 Agent Prompts

## 当前工作焦点: 修改 CompanionAgent 行动宣告逻辑，引入两阶段思考

*   **背景**: 完成了 DM 叙事优化及相关修复。当前焦点是改进 Agent 行为，特别是 `CompanionAgent`。
*   **当前任务**: 重构 `CompanionAgent` 的行动宣告逻辑，实现两阶段思考模式：
    1.  **快速判断 (Fast Check)**:
        *   检查 `CharacterInstance.short_term_goals` 是否存在。
        *   若存在，使用 **轻量级 LLM 调用** 进行可行性判断。
        *   **关键限制**: 此 LLM 调用**仅能访问** Agent 的 `short_term_goals` 和近期聊天记录 (`ChatHistoryManager`)，**不能访问**完整的 `GameState`，以模拟基于角色主观感知的快速直觉。
        *   Prompt 需引导 LLM 简单回答“可行”或“不可行”。
        *   若无目标或 LLM 判断不可行，则宣告 `WaitAction`。
    2.  **深度思考 / 行动选择 (Deep Thinking / Action Selection)**:
        *   若快速判断失败并宣告 `WaitAction`，则**触发** Agent 内部的深度思考/计划生成逻辑，为下一回合更新 `short_term_goals`。
        *   若快速判断成功，则继续执行现有的行动选择逻辑（选择 `DialogueAction`, `MoveAction` 等）。
*   **对话生成优化**:
    *   修改 `DialogueAction` 模型 (`src/models/action_models.py`)，增加 `minor_action: Optional[str]` 字段。
    *   修改 `CompanionAgent` 生成对话的 Prompt，要求直接输出对话内容，并鼓励根据情境填充 `minor_action`（如“叹气”），禁止输出模拟性描述（如“走向...”）。
*   **目标**: 使 `CompanionAgent` 的决策更符合角色心智模型，区分快速反应和深度规划，并使对话更自然生动。

## 近期变更

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
*   **修复 DM 叙事角色描述问题**:
    *   修改了 `scenarios/default.json`，调整了可玩角色数量，并确保剧本阶段定义只包含相关 NPC。添加了新 NPC `char_006` (老王) 用于测试。修复了 `char_003` 的 `is_playable` 状态错误。
    *   修改了 `src/context/context_utils.py` (`format_current_stage_characters`)，确保其包含玩家、伙伴和阶段 NPC，并移除了输出中的角色类型标签。
    *   修改了 `src/context/dm_context_builder.py` (`build_narrative_user_prompt`)，优化了 Prompt 指令，明确了对角色列表和背景人物的处理规则。

## 下一步计划 (CompanionAgent 两阶段思考实现)

1.  **更新 Memory Bank**: (当前步骤) 更新 `activeContext.md` 和 `progress.md` 以反映新的任务计划。
2.  **修改 `DialogueAction` 模型**: 在 `src/models/action_models.py` 中为 `DialogueAction` 添加 `minor_action: Optional[str]` 字段。
3.  **修改 `CompanionAgent`**:
    *   在 `src/agents/companion_agent.py` 中实现两阶段思考逻辑：
        *   实现快速判断（检查目标 + LLM 可行性判断，限制上下文）。
        *   实现失败时的 `WaitAction` 返回和深度思考触发。
        *   实现成功时的行动选择流程衔接。
    *   修改对话生成部分：
        *   更新 Prompt 以生成直接对话和 `minor_action`。
        *   更新代码以解析和填充新的 `DialogueAction` 字段。
4.  **审阅 `RefereeAgent`**: (后续任务) 检查其 Prompt 和数据源。
5.  **检查数据源**: (穿插进行) 确认 `Context Builders` 提供正确数据。

## 待解决/考虑事项

*   如何量化评估 Agent Prompt 优化的效果？可能需要设计特定的测试场景。
*   在优化 Prompt 时，如何在提高智能表现和控制 LLM 成本/延迟之间取得平衡？

## 架构理解深化 (保持不变)

*   **明确职责**: 进一步明确了 `GameState` (核心机制状态、全局信息、世界快照) 与 `ChatHistoryManager` (交互历史、上下文、信息可见性) 的不同职责和重要性。`GameState` 是硬性规则和后果的基础，而 `ChatHistoryManager` 为 Agent 理解对话流、进行关系评估和生成符合情境的反应提供关键上下文。保持此分离对实现智能交互至关重要。
*   **叙事焦点传递**: 确定了通过分析 `GameState` 回合记录，由 `dm_context_builder` 提取具体文本，再传递给 DM Agent 的模式，以提高叙事准确性。
