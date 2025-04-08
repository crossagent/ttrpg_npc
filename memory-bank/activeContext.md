# Active Context: 完成 DM 叙事角色描述修复，准备优化其他 Agent Prompts

## 当前工作焦点: 优化其他 Agent 的 Prompt 和数据源

*   **背景**: 上一个任务“优化 DM 叙事准确性”已完成，并且后续修复了由此引发的角色描述问题（如 DM 输出中出现 `[玩家]` 标签，以及对背景人物描述不当可能导致的“自创角色”感觉）。
*   **当前任务**: 在 DM 叙事上下文和 Prompt 得到改进后，现在需要将注意力转向其他核心 Agent，特别是 `CompanionAgent` 和 `RefereeAgent`。目标是审视它们当前的 Prompt 设计和所依赖的数据源（上下文），进行必要的优化，以确保它们的行为（思考、行动生成、判定）与更新后的系统架构和数据流保持一致，并尽可能提高其智能表现。
*   **关键考虑**:
    *   **CompanionAgent**: 如何更好地利用 `GameState` 中的 NPC 核心要素（目标、态度、记忆、状态）和 `ChatHistoryManager` 提供的对话历史来生成更符合角色个性和当前情境的思考与行动？Prompt 是否需要调整以引导其进行更深度的“感知-思考-行动”循环？
    *   **RefereeAgent**: 当前的判定 Prompt 是否足够清晰和鲁棒？在处理行动后果和事件触发时，是否能有效利用 `GameState` 和 `Scenario` 信息？特别是对于后续计划中的“基于 LLM 的关系评估”，需要思考如何设计 Prompt 和数据流。
    *   **数据源一致性**: 确保所有 Agent 使用的上下文信息来源（`GameState`, `ChatHistoryManager`, `ScenarioManager`）是一致且准确的。

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

## 下一步计划 (Agent Prompts 优化)

1.  **审阅 `CompanionAgent`**:
    *   检查其 `think` 或类似方法的 Prompt，评估其对 NPC 核心要素和聊天记录的利用程度。
    *   识别可优化点，例如改进思考逻辑引导、增强情境感知等。
    *   (如有必要) 提出具体的 Prompt 修改建议。
2.  **审阅 `RefereeAgent`**:
    *   检查其 `judge_action` 或相关判定方法的 Prompt。
    *   评估其规则理解、后果生成和事件触发判断的准确性。
    *   思考如何为后续的“关系评估”功能设计 Prompt 框架。
    *   (如有必要) 提出具体的 Prompt 修改建议。
3.  **检查数据源**: 确认 `Context Builders` 为这些 Agent 提供了所需且准确的数据。
4.  **更新 Memory Bank**: 根据审阅和优化结果，更新相关文档。

## 待解决/考虑事项

*   如何量化评估 Agent Prompt 优化的效果？可能需要设计特定的测试场景。
*   在优化 Prompt 时，如何在提高智能表现和控制 LLM 成本/延迟之间取得平衡？

## 架构理解深化 (保持不变)

*   **明确职责**: 进一步明确了 `GameState` (核心机制状态、全局信息、世界快照) 与 `ChatHistoryManager` (交互历史、上下文、信息可见性) 的不同职责和重要性。`GameState` 是硬性规则和后果的基础，而 `ChatHistoryManager` 为 Agent 理解对话流、进行关系评估和生成符合情境的反应提供关键上下文。保持此分离对实现智能交互至关重要。
*   **叙事焦点传递**: 确定了通过分析 `GameState` 回合记录，由 `dm_context_builder` 提取具体文本，再传递给 DM Agent 的模式，以提高叙事准确性。
