# TTRPG NPC

一个基于AutoGen框架的TTRPG NPC系统，用于创建和管理基于轮次的角色扮演游戏。

## 项目结构

```
src/
  ├── agents/         # 代理定义
  ├── chat/           # 聊天管理
  ├── config/         # 配置文件
  ├── engine/         # 游戏引擎
  ├── models/         # 数据模型
  └── scripts/        # 运行脚本
```

## 安装

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/ttrpg_npc.git
cd ttrpg_npc
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

## 运行示例游戏

这个示例游戏包含一个只会数数的Agent，每回合数字会比上一回合大1，最多进行5个回合。

```bash
python -m src.scripts.cli_runner
```

## 功能特点

- 基于AutoGen框架的多代理系统
- 回合制游戏流程
- 可扩展的代理架构
- 使用Pydantic进行数据验证

## 自定义游戏

要创建自己的游戏，您可以：

1. 修改`src/models/gameSchema.py`中的游戏状态模型
2. 在`src/engine/game_engine.py`中自定义代理初始化
3. 调整`src/engine/round_manager.py`中的回合执行逻辑

## 依赖项

- autogen-agentchat>=0.2.0
- autogen-ext[openai]>=0.2.0
- autogen-core>=0.2.0
- pydantic>=2.0.0
