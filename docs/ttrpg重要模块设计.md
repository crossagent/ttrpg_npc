一）回合切换模块
模块用途：
管理整个游戏进程，每回合均由DM尝试推进剧情作为开始。
每回合只包含DM推进与玩家响应两个步骤。
回合内Agent的三种可能行为：
对话：玩家主动参与发言，推动互动但不改变状态。
行动：玩家主动决定做出具体行动，如探索、攻击、干扰他人，DM本回合内立即处理并更新状态。
无视：玩家不作任何回应或互动。

而DM推动的时候
首先查看上回合的玩家回应或者互动，如果出现
一、触发了特殊的事件
二、玩家执行的行动
则继续推演故事。否则，DM不做任何行动。


（二）剧本模块
剧本模块用途：
存储整个游戏的核心剧情架构、预设事件与关键节点、以及角色的身份、目标和秘密。
DM依靠剧本来推动剧情，玩家则根据自己的个人剧本进行决策。

{
  "story_info": {
    "背景": "文明崩溃后的废土世界，资源争夺激烈。",
    "货轮秘密": "军方实验项目，含有危险辐射和基因药物。"
  },
  "角色信息": {
    "马克斯": {
      "公开身份": "机械师",
      "秘密目标": "获取核心控制地区局势"
    },
    "莱拉": {
      "公开身份": "猎人",
      "秘密目标": "获取特殊弹药抵抗威胁"
    },
    "霍克": {
      "公开身份": "退役军人",
      "秘密目标": "销毁军方证据隐藏过去"
    },
    "艾琳娜": {
      "公开身份": "医生",
      "秘密目标": "获取医疗物资救治家人"
    }
  },
  "剧本事件": [
    {
      "事件ID": "evt_001",
      "描述": "霍克企图销毁资料室文件",
      "触发条件": "博弈阶段",
      "可感知玩家": ["莱拉", "马克斯"],
      "可能结局": ["文件保存，霍克暴露", "文件销毁，霍克秘密安全"]
    }
  ]
}

（三）GameState模块
GameState模块用途：
存储并更新游戏中的实时状态，包括人物状态、物资、环境信息及剧情进展。
每次行动后的状态都会立刻更新。

{
  "角色状态": {
    "霍克": {"暴露": true, "当前状态": "受监视"},
    "莱拉": {"物品": ["军方文件"], "位置": "资料室"},
    "马克斯": {"位置": "资料室"},
    "艾琳娜": {"物品": ["医疗物资"], "辐射影响": "中等"}
  },
  "环境状态": {
    "辐射指数": "高",
    "货轮警报": "已启动"
  },
  "已完成事件": [
    {"事件ID": "evt_001", "结局": "文件保存，霍克暴露"}
  ]
}


（四）上下文模块
上下文模块用途：
管理公开信息如何被每个玩家感知。
将聊天室的公开聊天记录作为玩家长期的个人上下文，存储玩家的视角信息，并用于后续决策。

聊天记录副本:
{
  "消息记录": [
    {
    "消息ID": "msg_001",
    "类型": "对话",
    "发送者": "艾琳娜",
    "内容": "我找到医疗物资了，但这里辐射真的很强！",
    "时间戳": "2025-03-18T14:31:45Z",
    "可见性": ["所有人"]
    },
    {
    "消息ID": "msg_002",
    "类型": "行动",
    "发送者": "艾琳娜",
    "内容": "我要尝试收集这些医疗物资。",
    "时间戳": "2025-03-18T14:32:00Z",
    "可见性": ["所有人"],
    "触发判定": "judge_001"
    },
    {
    "消息ID": "msg_003",
    "类型": "系统",
    "发送者": "系统",
    "内容": "艾琳娜正在尝试收集医疗物资，需要进行医疗技能检定(难度:中等)...",
    "时间戳": "2025-03-18T14:32:05Z",
    "可见性": ["所有人"],
    "关联判定": "judge_001"
    },
    {
    "消息ID": "msg_004",
    "类型": "骰子",
    "发送者": "骰子系统",
    "内容": "艾琳娜投掷了一个D20骰子! 结果: 15",
    "时间戳": "2025-03-18T14:32:08Z",
    "可见性": ["所有人"],
    "关联判定": "judge_001",
    "骰子数据": {
        "类型": "D20",
        "结果": 15
    }
    },
    {
    "消息ID": "msg_005",
    "类型": "系统",
    "发送者": "系统",
    "内容": "艾琳娜的医疗技能加值+3，最终结果为18，高于难度15。检定成功!",
    "时间戳": "2025-03-18T14:32:10Z",
    "可见性": ["所有人"],
    "关联判定": "judge_001"
    },
    {
    "消息ID": "msg_006",
    "类型": "DM",
    "发送者": "DM",
    "内容": "艾琳娜熟练地收集了医疗物资，她的手法精准而高效。",
    "时间戳": "2025-03-18T14:32:12Z",
    "可见性": ["所有人"],
    "关联判定": "judge_001"
    },
    {
    "消息ID": "msg_007",
    "类型": "私密",
    "发送者": "DM",
    "内容": "你成功收集了三组医疗物资(基础医疗包x2,抗辐射药物x1)，但在过程中受到了轻微辐射(+5%)",
    "时间戳": "2025-03-18T14:32:15Z",
    "可见性": ["艾琳娜"],
    "关联判定": "judge_001"
    },
    {
    "消息ID": "msg_008",
    "类型": "对话",
    "发送者": "霍克",
    "内容": "艾琳娜，你那边情况如何？需要帮忙吗？",
    "时间戳": "2025-03-18T14:32:30Z",
    "可见性": ["所有人"]
    }]
  "当前游戏状态": {
    "回合": 3,
    "进行中事件": "evt_001",
    "环境状态": {"辐射指数": "高"}
  }
}

DM视角看到的信息
{
  "DM": {
    "消息状态": {
      "msg_001": {"状态": "已读", "时间戳": "2025-03-18T14:31:46Z"},
      "msg_002": {"状态": "已读", "时间戳": "2025-03-18T14:32:01Z"},
      "msg_003": {"状态": "已读", "时间戳": "2025-03-18T14:32:06Z"},
      "msg_004": {"状态": "已读", "时间戳": "2025-03-18T14:32:09Z"},
      "msg_005": {"状态": "已读", "时间戳": "2025-03-18T14:32:11Z"},
      "msg_006": {"状态": "已读", "时间戳": "2025-03-18T14:32:13Z"},
      "msg_007": {"状态": "已读", "时间戳": "2025-03-18T14:32:16Z"},
      "msg_008": {"状态": "已读", "时间戳": "2025-03-18T14:32:31Z"}
    },
    "游戏状态": {
      "角色": {
        "艾琳娜": {
          "位置": "医疗舱",
          "物品": ["基础医疗包x2", "抗辐射药物x1"],
          "辐射水平": "15%"
        },
        "马克斯": {
          "位置": "资料室",
          "物品": []
        },
        "霍克": {
          "位置": "控制室",
          "物品": ["手电筒", "密码卡"]
        }
      },
      "场景": {
        "医疗舱": {"状态": "被搜索过", "辐射水平": "高"},
        "资料室": {"状态": "未搜索", "辐射水平": "低"},
        "控制室": {"状态": "部分搜索", "辐射水平": "中"}
      }
    }
  }
}

玩家的聊天记录副本:
// 艾琳娜的聊天记录
{
  "角色": "艾琳娜",
  "消息状态": {
    "msg_001": {"状态": "已读", "时间戳": "2025-03-18T14:31:46Z"},
    "msg_002": {"状态": "已读", "时间戳": "2025-03-18T14:32:01Z"},
    "msg_003": {"状态": "已读", "时间戳": "2025-03-18T14:32:06Z"},
    "msg_004": {"状态": "已读", "时间戳": "2025-03-18T14:32:09Z"},
    "msg_005": {"状态": "已读", "时间戳": "2025-03-18T14:32:11Z"},
    "msg_006": {"状态": "已读", "时间戳": "2025-03-18T14:32:13Z"},
    "msg_007": {"状态": "已读", "时间戳": "2025-03-18T14:32:16Z"},
    "msg_008": {"状态": "未读", "时间戳": null}
  },
  "个人状态": {
    "位置": "医疗舱",
    "物品": ["基础医疗包x2", "抗辐射药物x1"],
    "辐射水平": "15%",
    "知晓信息": ["医疗舱辐射严重", "成功收集医疗物资"]
  }
}

// 马克斯的聊天记录
{
  "角色": "马克斯",
  "消息状态": {
    "msg_001": {"状态": "已读", "时间戳": "2025-03-18T14:31:50Z"},
    "msg_002": {"状态": "已读", "时间戳": "2025-03-18T14:32:02Z"},
    "msg_003": {"状态": "已读", "时间戳": "2025-03-18T14:32:07Z"},
    "msg_004": {"状态": "已读", "时间戳": "2025-03-18T14:32:10Z"},
    "msg_005": {"状态": "已读", "时间戳": "2025-03-18T14:32:12Z"},
    "msg_006": {"状态": "已读", "时间戳": "2025-03-18T14:32:14Z"},
    "msg_008": {"状态": "未读", "时间戳": null}
    // 注意：没有msg_007，因为那是私密消息，只对艾琳娜可见
  },
  "个人状态": {
    "位置": "资料室",
    "物品": [],
    "知晓信息": ["艾琳娜成功收集了医疗物资"]
  }
}

消息分发流程:

DM发送消息时，系统检查"可感知玩家"列表
只将消息添加到符合条件的玩家的聊天记录副本中
玩家发送的消息默认添加到所有人的聊天记录中，除非特别指定