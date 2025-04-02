## 当前任务

### 重构后果处理：分离属性与 Flag (Refactor Consequence Handling: Separate Attributes and Flags)

*   **目标**: 重构游戏引擎，严格区分行动的直接“属性后果”和由事件触发的“Flag 后果”，确保 Flag 只能通过 `ScenarioEvent` 的结局来设置。
*   **核心原则**:
    *   行动判定 (`judge_action`) 只产生属性后果。
    *   回合评估 (`determine_triggered_events_and_outcomes`) 只判断活跃 `ScenarioEvent` 是否触发。
    *   Flag 设置只能来源于被触发事件的后果 (`EventOutcome.consequences`)。
*   **主要步骤**:
    1.  **模型层**:
        *   `ConsequenceType` 添加 `UPDATE_FLAG`。
        *   `Consequence` 添加 `flag_name`, `flag_value`。
        *   `GameState` 添加 `flags: Dict[str, bool]`。
        *   `ActionResult` 确认只包含属性后果。
    2.  **`RefereeAgent`**:
        *   简化 `judge_action`，移除 Flag 判断逻辑。
        *   确认 `determine_triggered_events_and_outcomes` 输入简化 `ActionResult`，输出事件 ID 和结局 ID。
    3.  **`JudgementPhase`**:
        *   调整流程，先调用 `_resolve_direct_actions` 获取属性后果，再调用 `determine_triggered_events_and_outcomes` 获取触发事件。
        *   返回包含 `action_results` 和 `triggered_events` 的字典。
    4.  **`UpdatePhase`**:
        *   按顺序应用属性后果、事件后果（包括可能的 Flag 设置）。
        *   检查阶段完成条件。
*   **状态**: 待办 (To Do)

---

## 后续任务 (待办)

### 定义并实现角色属性与能力系统 (Define and Implement Character Attributes & Abilities System)

*   **目标**: 设计并实现一个更详细的角色属性（如力量、敏捷、智力、魅力等）和能力系统，以支持更丰富的行动判定和角色扮演。
*   **背景**: 当前 `CharacterStatus` 较为简化，缺少对核心属性和能力的明确定义。
*   **可能步骤**:
    1.  设计属性和能力的具体结构（可能在 `src/models/character_attributes.py` 或类似文件中）。
    2.  更新剧本角色模板 (`ScenarioCharacterInfo`) 以包含基础属性/能力定义。
    3.  升级角色状态模型 (`CharacterStatus` 或创建一个新的 `CharacterInstance` 模型) 以包含运行时属性值、能力状态等。
    4.  调整 `RefereeAgent` 的行动判定逻辑 (`judge_action`)，使其能够利用这些属性/能力进行更细致的判定。
    5.  更新上下文构建器 (`Context Builders`) 以向 LLM 提供角色属性/能力信息。
    6.  更新后果模型 (`Consequence`) 以支持修改这些新属性/能力。
*   **状态**: 待办 (To Do)
