## 当前任务

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
*   **状态**: 进行中 (In Progress)
