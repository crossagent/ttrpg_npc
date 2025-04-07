# Active Context: 优化 DM 叙事准确性

## 当前工作焦点: 改进 DM Agent 上下文构建以聚焦关键变化

*   **问题**: 当前 DM Agent (叙事 Agent) 在生成叙事时，未能严格基于 `GameState` 的事实，有时会忽略关键变化或虚构情节，即使 Prompt 中已包含相关指令和聊天记录。根本原因在于 LLM 可能难以准确判断哪些信息是需要重点描述的“新变化”，并容易被聊天记录带偏。
*   **解决方案 (最终修订版 v2)**: 不引入新的 Consequence 类型，而是增强 `dm_context_builder` 的能力，使其在构建 DM 上下文时，主动分析 `GameState` 中记录的**本回合**关键变化 (`current_round_applied_consequences` 和 `current_round_triggered_events`)，并从中提取具体的描述性文本或摘要，直接提供给 DM Agent。
*   **核心改动**:
    1.  **增强 `dm_context_builder.py`**:
        *   访问 `game_state.current_round_applied_consequences` 和 `game_state.current_round_triggered_events`。
        *   分析这些记录，识别关键变化类型（如首次地点进入、事件触发、关键 Flag 更新）。
        *   根据识别出的变化，从 `GameState` 或场景配置中**提取**对应的描述性文本或摘要（例如，新地点的描述、事件/结局的摘要）。
        *   将提取出的文本填充到传递给 DM Agent 的新字段 `narrative_focus_points: List[str]` 中。
    2.  **调整 `agents/dm_agent.py` 的 Prompt**:
        *   明确指示 DM Agent 基于 `GameState` 摘要进行叙事。
        *   要求 DM Agent **将 `narrative_focus_points` 列表中的具体文本片段自然地融入**叙事，以突出关键变化。
        *   继续强调“GameState 是客观事实的唯一来源”，并避免重复静态信息和虚构事实。
    3.  **确保 `GameState` 包含必要信息**:
        *   需要有追踪角色已访问地点的机制 (如 `visited_locations`)。
        *   确保地点、事件、章节等数据结构包含可供提取的描述或摘要。

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

## 下一步计划 (DM 叙事优化)

1.  **实现 `GameState` 地点追踪**: (如果尚未实现) 在 `GameState` 或 `CharacterInstance` 中添加 `visited_locations: Set[str]` 字段及相关更新逻辑。
2.  **修改 `dm_context_builder.py`**:
    *   实现分析 `current_round_applied_consequences` 和 `current_round_triggered_events` 的逻辑。
    *   实现根据后果/事件记录提取对应描述/摘要的逻辑（需要访问 `GameState` 和场景数据）。
    *   实现填充 `narrative_focus_points` 字段。
3.  **修改 `agents/dm_agent.py`**: 更新 System Prompt 以利用 `narrative_focus_points`。
4.  **测试**: 运行游戏，观察 DM 叙事是否更准确地聚焦于关键变化，并减少虚构。
5.  **更新 Memory Bank**: 更新 `progress.md` 和 `systemPatterns.md`。

## 待解决/考虑事项

*   需要确认 `GameState`、场景配置 (`Scenario`) 中是否已包含足够详细的地点描述、事件/结局摘要等信息供 `dm_context_builder` 提取。如果不足，需要补充。
*   `dm_context_builder` 提取逻辑的健壮性，如何处理找不到描述或摘要的情况。

## 架构理解深化 (保持不变)

*   **明确职责**: 进一步明确了 `GameState` (核心机制状态、全局信息、世界快照) 与 `ChatHistoryManager` (交互历史、上下文、信息可见性) 的不同职责和重要性。`GameState` 是硬性规则和后果的基础，而 `ChatHistoryManager` 为 Agent 理解对话流、进行关系评估和生成符合情境的反应提供关键上下文。保持此分离对实现智能交互至关重要。
*   **叙事焦点传递**: 确定了通过分析 `GameState` 回合记录，由 `dm_context_builder` 提取具体文本，再传递给 DM Agent 的模式，以提高叙事准确性。
