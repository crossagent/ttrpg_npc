# 裁判代理与状态更新开发计划

本文档详细描述了裁判代理 (Referee Agent) 与游戏状态更新功能的分阶段开发计划。

## 背景

根据 V4 模块设计，我们需要实现一个裁判代理 (Referee Agent)，负责解析玩家和 NPC 的行动意图，根据游戏规则判断行动结果，并生成结构化的状态变更指令。这是实现游戏交互的核心组件。

## 总体目标

实现玩家行动的解析、裁判和相应的游戏状态更新功能，使玩家能够通过自然语言输入与游戏世界进行交互，并看到其行动对游戏状态的影响。

## 分阶段开发计划

### Phase 1: 裁判代理基础结构与简单动作解析

**目标:** 创建裁判代理的基本框架，实现最简单的动作解析逻辑。

**任务:**
1. 创建 `src/agents/referee_agent.py` 文件。
2. 定义 `RefereeAgent` 类。
3. 定义 `ActionOutcome` Pydantic 模型，包含以下字段：
   - `success: bool` - 行动是否成功
   - `narrative_hint: Optional[str]` - 给叙事代理的提示
   - `state_changes: Dict[str, Any]` - 需要应用的状态变更
4. 实现 `RefereeAgent.parse_and_judge_action(action_input: str, current_state: GameState) -> ActionOutcome` 方法的基本框架。
5. 在 `parse_and_judge_action` 中实现**最简单**的动作解析逻辑：
   - 例如，仅识别 "移动 [地点名称]" 或 "move [location_name]" 格式。
   - 如果匹配成功，返回一个包含 `success=True` 和 `state_changes={"character_location": "[地点名称]"}` 的 `ActionOutcome`。
   - 如果不匹配，返回 `success=False` 和空的 `state_changes`。

**验收标准:**
- `RefereeAgent` 类和 `ActionOutcome` 模型已创建。
- 调用 `referee_agent.parse_and_judge_action` 方法，输入 "移动 大厅" 时，能正确返回包含 `success=True` 和 `state_changes={"character_location": "大厅"}` 的结果。
- 输入无法识别的指令时，返回 `success=False`。

### Phase 2: 游戏引擎集成裁判代理

**目标:** 将裁判代理集成到游戏引擎中，使其能够处理玩家输入。

**任务:**
1. 在 `GameEngine` 中实例化或获取 `RefereeAgent`。
2. 修改 `GameEngine` 处理玩家输入的逻辑：在接收到玩家输入后，调用 `referee_agent.parse_and_judge_action` 方法，并将当前的 `GameState` 传入。
3. 将返回的 `ActionOutcome` 对象暂存或打印出来（用于调试）。

**验收标准:**
- 在游戏运行时，当玩家输入指令（如 "移动 大厅"），`GameEngine` 能够成功调用 `RefereeAgent` 并获取到 `ActionOutcome` 结果（可以通过日志或断点确认）。

### Phase 3: 基础游戏状态更新

**目标:** 根据裁判代理的结果更新游戏状态。

**任务:**
1. 确保 `GameStateManager` 提供了更新角色位置的方法，例如 `update_character_location(character_id: str, new_location: str)`。
2. 在 `GameEngine` 中，获取 `ActionOutcome` 后，检查 `state_changes` 字典。
3. 如果 `state_changes` 包含 `"character_location"`，则调用 `game_state_manager.update_character_location` 方法，使用正确的角色 ID 和新的地点名称更新 `GameState`。

**验收标准:**
- 当玩家输入 "移动 大厅" 并且 `RefereeAgent` 返回成功的 `ActionOutcome` 后，检查 `GameState` 中的玩家角色位置确实被更新为 "大厅"。

### Phase 4: 基础结果反馈

**目标:** 向玩家提供行动结果的反馈。

**任务:**
1. 在 `GameEngine` 处理完状态更新后，根据 `ActionOutcome` 的 `success` 状态和 `narrative_hint`（如果存在），构建一个简单的反馈消息字符串。
2. 使用 `MessageDispatcher` 将这个反馈消息发送给 `Presentation Layer` (控制台)。

**验收标准:**
- 当玩家输入 "移动 大厅" 并成功更新状态后，控制台能显示类似 "你成功移动到了 大厅。" 的反馈信息。
- 当玩家输入无法识别的指令时，控制台能显示类似 "无法理解你的行动。" 的反馈信息。

### Phase 5: 扩展动作解析能力

**目标:** 增强裁判代理的动作解析能力，支持更多类型的动作。

**任务:**
1. 扩展 `parse_and_judge_action` 方法，使用正则表达式或更复杂的解析逻辑，识别更多类型的动作：
   - 对话: "说 [内容]" 或 "对 [角色] 说 [内容]"
   - 观察: "查看 [物品/环境/角色]" 或 "观察 [物品/环境/角色]"
   - 使用物品: "使用 [物品]" 或 "使用 [物品] 对 [目标]"
2. 为每种动作类型实现相应的处理逻辑，生成适当的 `ActionOutcome`。

**验收标准:**
- 裁判代理能够识别并处理至少三种不同类型的动作（如移动、对话、观察）。
- 每种动作类型都能生成适当的 `state_changes` 和 `narrative_hint`。

### Phase 6: 实现基础规则判定

**目标:** 为裁判代理添加基础的规则判定能力。

**任务:**
1. 在 `RefereeAgent` 中实现简单的规则判定逻辑，例如：
   - 检查移动目标是否是有效的相邻位置
   - 检查使用物品是否在角色的物品栏中
   - 检查交互目标是否在当前位置
2. 根据判定结果，设置 `ActionOutcome` 的 `success` 字段和相应的 `narrative_hint`。

**验收标准:**
- 当玩家尝试移动到不存在或不可达的位置时，裁判代理返回 `success=False` 和适当的失败原因。
- 当玩家尝试使用不在物品栏中的物品时，裁判代理返回 `success=False` 和适当的失败原因。

### Phase 7: 扩展游戏状态更新

**目标:** 扩展游戏状态管理器，支持更多类型的状态更新。

**任务:**
1. 在 `GameStateManager` 中实现更多的状态更新方法，例如：
   - `add_item_to_inventory(character_id: str, item_id: str, quantity: int = 1)`
   - `remove_item_from_inventory(character_id: str, item_id: str, quantity: int = 1)`
   - `update_character_attribute(character_id: str, attribute: str, value: Any)`
   - `update_location_state(location_id: str, state_key: str, state_value: Any)`
2. 在 `GameEngine` 中，根据 `ActionOutcome.state_changes` 的内容，调用相应的状态更新方法。

**验收标准:**
- 游戏状态管理器能够处理至少三种不同类型的状态更新（如位置、物品、属性）。
- 当裁判代理返回包含这些状态变更的 `ActionOutcome` 时，游戏引擎能够正确地更新游戏状态。

### Phase 8: 集成叙事代理

**目标:** 将裁判代理的结果与叙事代理集成，生成更丰富的叙事描述。

**任务:**
1. 确保 `ActionOutcome` 的 `narrative_hint` 字段包含足够的信息，供叙事代理生成描述。
2. 在 `GameEngine` 中，将 `ActionOutcome` 传递给叙事代理，生成更丰富的叙事描述。
3. 使用 `MessageDispatcher` 将叙事描述发送给 `Presentation Layer`。

**验收标准:**
- 当玩家执行行动后，系统能够生成比简单反馈更丰富的叙事描述。
- 叙事描述反映了行动的结果和对游戏世界的影响。

### Phase 9: LLM 增强的动作解析 (可选)

**目标:** 使用 LLM 增强裁判代理的动作解析能力，处理更自然的语言输入。

**任务:**
1. 设计一个 LLM Prompt，用于将玩家的自然语言输入解析为结构化的动作意图。
2. 在 `RefereeAgent` 中实现 LLM 调用逻辑，将玩家输入和当前游戏状态作为上下文。
3. 解析 LLM 的输出，提取动作类型、参数和目标。
4. 根据解析结果，生成 `ActionOutcome`。

**验收标准:**
- 裁判代理能够处理更自然、更多样的语言输入，如 "我想去大厅看看有什么" 或 "告诉莱拉我找到了医疗物资"。
- 解析结果准确反映了玩家的意图。

### Phase 10: NPC 行动解析与裁判

**目标:** 扩展裁判代理，处理 NPC 的行动意图。

**任务:**
1. 修改 `RefereeAgent` 的接口，支持处理 NPC 的行动意图（可能是结构化的，而非自然语言）。
2. 实现 NPC 行动的规则判定逻辑。
3. 确保 `GameEngine` 在 NPC 行动阶段调用裁判代理处理 NPC 的行动意图。

**验收标准:**
- 裁判代理能够处理 NPC 的行动意图，并生成适当的 `ActionOutcome`。
- 游戏引擎能够根据 `ActionOutcome` 更新游戏状态，并生成相应的叙事描述。

## 后续迭代方向

1. **高级规则判定:** 实现更复杂的规则判定，如技能检定、战斗系统、资源管理等。
2. **动态规则:** 允许游戏规则根据游戏状态、场景或特殊条件动态变化。
3. **多步骤行动:** 支持需要多个步骤完成的复杂行动。
4. **行动历史与上下文:** 考虑玩家的行动历史和当前上下文，提供更智能的行动解析和判定。
5. **自定义规则系统:** 提供一个框架，允许游戏设计者定义自己的规则系统和判定逻辑。
