# AgentScope 三国狼人杀案例

本目录包含第六章 AgentScope 框架的完整实战案例，展示了如何使用 AgentScope 构建一个融合中国古典文化元素的多智能体在线游戏。

## 📁 文件说明

- `main_cn.py` - 主要游戏逻辑和控制器
- `prompt_cn.py` - 中文提示词管理
- `game_roles.py` - 游戏角色定义和配置
- `structured_output_cn.py` - 结构化输出模型定义
- `utils_cn.py` - 游戏工具函数和辅助方法
- `README.md` - 本说明文档

## 🎮 案例特点

- **消息驱动架构**：展示 AgentScope 的核心消息传递机制
- **并发协作**：演示多智能体同时在线的实时交互
- **角色扮演**：每个智能体具备双重身份（游戏角色+三国人物）
- **结构化输出**：通过 Pydantic 模型约束智能体行为
- **容错机制**：单个智能体异常不影响整体游戏流程

## 🛠️ 环境准备

### 1. 安装依赖

```bash
pip install agentscope
pip install dashscope
pip install pydantic
```

### 2. 配置环境变量

设置阿里云 DashScope API Key：

```bash
# Linux/Mac
export DASHSCOPE_API_KEY="your-api-key-here"

# Windows PowerShell
$env:DASHSCOPE_API_KEY="your-api-key-here"

# Windows CMD
set DASHSCOPE_API_KEY=your-api-key-here
```

获取 API Key：https://bailian.console.aliyun.com/cn-beijing?tab=model#/api-key

### 3. 运行游戏

```bash
python main_cn.py
```

## 🎭 游戏角色说明

### 游戏角色
- **狼人**：夜晚击杀好人，白天隐藏身份
- **预言家**：每晚查验一名玩家身份
- **女巫**：拥有解药和毒药各一瓶
- **猎人**：被投票出局时可开枪带走一名玩家
- **村民**：通过推理和投票找出狼人

### 三国人物
- **刘备**：仁德宽厚，善于团结众人
- **关羽**：忠义刚烈，言辞直接
- **张飞**：性格豪爽，容易冲动
- **诸葛亮**：智慧超群，分析透彻
- **曹操**：雄才大略，善于权谋
- **司马懿**：深谋远虑，城府极深

## 🏗️ 架构设计

### 分层架构
```
游戏控制层 (ThreeKingdomsWerewolfGame)
    ├── 游戏状态管理
    ├── 流程控制
    └── 胜负判定

智能体交互层 (MsgHub)
    ├── 消息路由
    ├── 并发处理
    └── 状态同步

角色建模层 (DialogAgent)
    ├── 角色提示词
    ├── 结构化输出
    └── 行为约束
```

### 核心组件

**1. 消息中心 (MsgHub)**
```python
async with MsgHub(
    participants=self.werewolves,
    enable_auto_broadcast=True
) as hub:
    # 狼人夜晚讨论
    for wolf in self.werewolves:
        await wolf(structured_model=DiscussionModelCN)
```

**2. 结构化输出**
```python
class VoteModelCN(BaseModel):
    vote: str = Field(description="投票目标玩家姓名")
    reason: str = Field(description="投票理由")
    confidence: int = Field(ge=1, le=10, description="信心程度")
```

**3. 并发管道**
```python
vote_msgs = await fanout_pipeline(
    self.alive_players,
    msg=vote_announcement,
    structured_model=get_vote_model_cn(self.alive_players),
    enable_gather=False,
)
```

## 🎯 游戏流程

### 夜晚阶段
1. **狼人讨论**：狼人通过 MsgHub 协商击杀目标
2. **预言家查验**：预言家选择查验对象
3. **女巫行动**：女巫决定是否使用解药/毒药

### 白天阶段
1. **死亡公布**：公布夜晚死亡玩家
2. **自由讨论**：所有存活玩家参与讨论
3. **投票淘汰**：投票选择淘汰对象
4. **猎人技能**：被淘汰的猎人可开枪

## 🔧 自定义配置

### 修改游戏人数
```python
# 在 main_cn.py 中修改
await game.setup_game(player_count=8)  # 支持 6-12 人
```

### 添加新角色
```python
# 在 game_roles.py 中添加
ROLES["守护者"] = {
    "description": "守护者",
    "ability": "每晚可以守护一名玩家",
    "team": "好人阵营"
}
```

### 自定义提示词
```python
# 在 prompt_cn.py 中修改
def get_role_prompt(role: str, character: str) -> str:
    # 自定义角色提示词逻辑
    pass
```

## 🐛 常见问题

### Q: 游戏无法启动？
A: 检查以下几点：
- 确认 DASHSCOPE_API_KEY 环境变量已设置
- 验证 API Key 是否有效
- 检查网络连接是否正常

### Q: 智能体输出格式错误？
A: 可能原因：
- 模型理解能力限制
- 提示词设计不够清晰
- 结构化输出约束过于复杂

### Q: 游戏流程卡住？
A: 建议：
- 检查 MsgHub 的消息传递
- 验证并发管道的执行状态
- 查看控制台错误日志

## 📚 技术亮点

### 1. 消息驱动架构
- 智能体间完全通过消息交互
- 支持异步并发处理
- 天然的分布式能力

### 2. 结构化输出约束
- 游戏规则转化为代码约束
- 提升系统稳定性和可预测性
- 便于调试和监控

### 3. 双重角色建模
- 游戏角色 + 三国人物的创新设计
- 展现不同人格的策略差异
- 增强游戏的趣味性和真实感

## 🚀 扩展方向

- **增加游戏模式**：支持更多狼人杀变体
- **优化 AI 策略**：提升智能体的游戏水平
- **可视化界面**：开发 Web 或桌面客户端
- **实时观战**：支持人类玩家观战和互动
- **数据分析**：统计游戏数据和智能体表现

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request：
- 报告游戏 Bug 或异常
- 提出新功能建议
- 优化代码实现
- 完善文档说明

---

*本案例是 Hello-Agents 教程第六章的核心实战项目，展示了 AgentScope 框架在构建复杂多智能体应用方面的强大能力。*
