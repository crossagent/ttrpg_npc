# Active Context: 定义并实现角色属性与能力系统 (整合至 CharacterInstance)

## 当前任务焦点

设计并实现一个更详细的角色属性（如力量、敏捷、智力、魅力等）和能力系统，并将其整合到 `CharacterInstance` 模型中，以支持更丰富的行动判定和角色扮演。

*   **背景**: 当前 `CharacterStatus` 较为简化，缺少对核心属性和能力的明确定义。之前的任务（分离属性与 Flag 后果）已经完成。
*   **核心思路**: 将角色的运行时状态（包括基础信息、属性、能力、物品、位置等）统一整合到 `src/models/game_state_models.py` 中的 `CharacterInstance` 模型中，取代或大幅修改现有的 `CharacterStatus`。
*   **目标**:
    *   创建 Pydantic 模型来表示角色属性 (`AttributeSet`) 和技能/能力 (`SkillSet`)。
    *   更新剧本角色模板 (`ScenarioCharacterInfo`) 以包含基础属性/能力定义。
    *   **重构 `CharacterInstance` 模型**，使其包含运行时属性值、技能值、健康、位置、物品等所有运行时状态。
    *   更新 `GameState` 以使用新的 `CharacterInstance` 结构（可能移除 `character_states`）。
    *   更新后果模型 (`Consequence`) 以支持修改 `CharacterInstance` 中的新属性/能力。
    *   更新剧本 (`default.json`) 以包含基础属性/能力。
    *   增强 `RefereeAgent` 的判定逻辑 (`judge_action`) 和相关 Prompt，以利用 `CharacterInstance` 中的新信息。
    *   更新 `GameStateManager` 的 `apply_consequences` 方法以处理对 `CharacterInstance` 中属性/能力的修改。

## 主要步骤 (修订计划)

1.  **设计属性/能力结构**:
    *   在 `src/models/` 下创建新文件（例如 `character_attributes.py` 或直接在 `game_state_models.py` 中定义）。
    *   定义 `AttributeSet` (包含力量、敏捷等基础值和当前值) 和 `SkillSet` (包含技能名称和等级/值) 的 Pydantic 模型。
2.  **更新模型**:
    *   修改 `src/models/scenario_models.py` 中的 `ScenarioCharacterInfo`，添加 `base_attributes: AttributeSet` 和 `base_skills: SkillSet` 字段。
    *   **重构 `src/models/game_state_models.py` 中的 `CharacterInstance`**:
        *   移除 `status: CharacterStatus` 字段。
        *   直接添加 `location: str`, `health: int`, `items: List[ItemInstance]`, `known_information: List[str]`, `attributes: AttributeSet`, `skills: SkillSet` 等字段。
    *   **更新 `src/models/game_state_models.py` 中的 `GameState`**: 确认 `characters: Dict[str, CharacterInstance]` 使用更新后的 `CharacterInstance`。考虑是否移除 `character_states` 字典。
    *   修改 `src/models/consequence_models.py` 中的 `Consequence` 和 `ConsequenceType`，添加修改 `CharacterInstance` 中属性/技能的类型和字段（例如 `UPDATE_CHARACTER_ATTRIBUTE`, `UPDATE_CHARACTER_SKILL`）。
3.  **更新剧本**:
    *   修改 `scenarios/default.json` 中的角色定义，包含新的 `base_attributes` 和 `base_skills`。
4.  **更新判定逻辑**:
    *   修改 `src/agents/referee_agent.py` 中的 `judge_action`，使其从 `CharacterInstance` 读取属性/技能进行判定。
    *   修改 `src/context/referee_context_builder.py` 中的 Prompt 构建函数，从 `CharacterInstance` 提取信息。
5.  **更新状态应用**:
    *   修改 `src/engine/game_state_manager.py` 中的 `apply_consequences` 方法，使其能够处理对 `CharacterInstance` 中属性/技能的修改。

## 后续步骤

1.  开始实施上述步骤，首先从设计和修改模型层 (`character_attributes.py`, `scenario_models.py`, `game_state_models.py`, `consequence_models.py`) 开始。
2.  根据需要调整 `systemPatterns.md`。
