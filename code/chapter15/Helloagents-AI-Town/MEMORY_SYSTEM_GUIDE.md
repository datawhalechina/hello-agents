# 🧠 NPC记忆系统使用指南

## 📚 概述

赛博小镇的NPC现在拥有了**记忆系统**,能够记住与玩家的对话历史,并在后续对话中引用之前的内容,让NPC更加智能和真实!

---

## ✨ 核心功能

### 1. **工作记忆 (Working Memory)** - 短期记忆
- 📝 存储最近的10条对话
- ⏰ 2小时后自动过期
- 🚀 快速检索,用于当前对话上下文

### 2. **情景记忆 (Episodic Memory)** - 长期记忆
- 💾 持久化存储重要对话
- 🔍 支持语义检索 (基于Qdrant向量数据库)
- 📊 最多存储100条记忆
- 🧹 自动遗忘重要性低于0.3的记忆

### 3. **记忆隔离**
- 🔒 每个NPC拥有独立的记忆系统
- 🚫 NPC之间的记忆不会互相干扰
- 👤 每个玩家的对话独立存储

---

## 🎯 使用示例

### 示例1: 基本对话记忆

```
第一次对话:
玩家: "你好,你是做什么的?"
张三: "你好!我是Python工程师,主要负责多智能体系统开发。"

第二次对话 (5分钟后):
玩家: "还记得我刚才问你什么吗?"
张三: "当然记得!你问我是做什么的,我说我是Python工程师。最近在研究HelloAgents框架。"
```

### 示例2: 长期记忆

```
第一天:
玩家: "你最喜欢的编程语言是什么?"
张三: "我最喜欢Python,简洁优雅,生态丰富。"

第二天:
玩家: "我们之前聊过编程语言吗?"
张三: "聊过!我记得我说过我最喜欢Python,你对这个感兴趣吗?"
```

### 示例3: 记忆隔离

```
与张三对话:
玩家: "我最近在学习多智能体系统"
张三: "太好了!我正好在研究这个,有什么问题可以问我。"

与李四对话:
玩家: "我刚才和张三聊了什么?"
李四: "抱歉,我不知道你和张三聊了什么,我只负责产品方面的工作。"
```

---

## 🔧 技术实现

### 架构设计

```
NPCAgentManager
├── agents: Dict[str, SimpleAgent]          # NPC Agent
├── memories: Dict[str, MemoryManager]      # NPC记忆管理器
└── chat(npc_name, message, player_id)      # 对话接口
    ├── 1. 检索相关记忆
    ├── 2. 构建增强提示词
    ├── 3. 调用Agent生成回复
    └── 4. 保存对话到记忆
```

### 记忆存储结构

```
backend/memory_data/
├── 张三/
│   ├── sqlite_store.db          # SQLite数据库 (权威存储)
│   └── qdrant_collection/       # Qdrant向量索引 (语义检索)
├── 李四/
│   ├── sqlite_store.db
│   └── qdrant_collection/
└── 王五/
    ├── sqlite_store.db
    └── qdrant_collection/
```

### 记忆数据格式

```python
{
    "id": "memory_uuid",
    "content": "玩家说: 你好,你是做什么的?",
    "type": "working",  # working/episodic
    "importance": 0.5,  # 0-1之间
    "timestamp": "2024-01-15T10:30:00",
    "metadata": {
        "speaker": "player",
        "player_id": "player",
        "session_id": "player",
        "context": {
            "interaction_type": "dialogue",
            "npc_name": "张三"
        }
    }
}
```

---

## 🚀 API接口

### 1. 对话接口 (支持记忆)

```http
POST /chat
Content-Type: application/json

{
    "npc_name": "张三",
    "message": "你好,你是做什么的?"
}
```

**响应:**
```json
{
    "npc_name": "张三",
    "npc_title": "Python工程师",
    "message": "你好!我是Python工程师,主要负责多智能体系统开发。",
    "success": true
}
```

### 2. 获取NPC记忆

```http
GET /npcs/张三/memories?limit=10
```

**响应:**
```json
{
    "npc_name": "张三",
    "memories": [
        {
            "id": "uuid-1",
            "content": "玩家说: 你好,你是做什么的?",
            "type": "working",
            "importance": 0.5,
            "timestamp": "2024-01-15T10:30:00",
            "metadata": {...}
        },
        ...
    ],
    "total": 10
}
```

### 3. 清空NPC记忆 (测试用)

```http
DELETE /npcs/张三/memories?memory_type=working
```

**响应:**
```json
{
    "message": "已清空张三的记忆",
    "npc_name": "张三",
    "memory_type": "working"
}
```

---

## 🧪 测试方法

### 方法1: 使用测试脚本

```bash
cd backend
python test_memory.py
```

**测试内容:**
- ✅ 基本对话记忆
- ✅ 长期记忆检索
- ✅ 记忆隔离
- ✅ 相关性检索

### 方法2: 使用API测试

1. 启动后端服务:
```bash
cd backend
python main.py
```

2. 访问API文档: http://localhost:8000/docs

3. 测试对话接口:
   - 发送第一条消息: "你好,你是做什么的?"
   - 发送第二条消息: "还记得我刚才问你什么吗?"
   - 查看记忆列表: GET /npcs/张三/memories

### 方法3: 在Godot中测试

1. 启动后端服务
2. 运行Godot游戏
3. 与NPC对话多次
4. 观察NPC是否能记住之前的对话

---

## 📊 记忆系统配置

### 配置参数 (agents.py)

```python
memory_config = MemoryConfig(
    storage_path=f"./memory_data/{npc_name}",  # 存储路径
    working_memory_capacity=10,                # 工作记忆容量
    working_memory_tokens=2000,                # 工作记忆token限制
    max_capacity=100,                          # 记忆总容量
    importance_threshold=0.3,                  # 重要性阈值
    decay_factor=0.95                          # 时间衰减系数
)
```

### 调整建议

| 参数 | 默认值 | 建议范围 | 说明 |
|------|--------|----------|------|
| working_memory_capacity | 10 | 5-20 | 工作记忆容量,越大越占内存 |
| working_memory_tokens | 2000 | 1000-4000 | Token限制,影响上下文长度 |
| max_capacity | 100 | 50-500 | 记忆总容量,越大越占磁盘 |
| importance_threshold | 0.3 | 0.1-0.5 | 重要性阈值,越高越偏向保留重要记忆 |
| decay_factor | 0.95 | 0.8-0.99 | 时间衰减系数,越低越强调近期记忆 |

---

## 🎓 教学价值

### 学习要点

1. **MemoryManager的使用**
   - 如何初始化记忆管理器
   - 如何配置不同类型的记忆
   - 如何添加和检索记忆

2. **记忆检索策略**
   - 工作记忆: 快速检索最近对话
   - 情景记忆: 语义检索相关历史
   - 混合检索: 结合时间和相关性

3. **记忆存储机制**
   - SQLite: 权威数据存储
   - Qdrant: 向量语义检索
   - 双存储保证数据一致性

4. **记忆遗忘机制**
   - 基于重要性的自动遗忘
   - 基于时间的TTL过期
   - 容量限制的优先级淘汰

---

## 🔍 调试技巧

### 1. 查看记忆日志

```python
# 在agents.py的chat方法中
print(f"🧠 {npc_name}检索到{len(relevant_memories)}条相关记忆")
print(f"💾 对话已保存到{npc_name}的记忆中")
```

### 2. 检查记忆文件

```bash
# 查看SQLite数据库
cd backend/memory_data/张三
sqlite3 sqlite_store.db
> SELECT * FROM memories;
```

### 3. 清空记忆重新测试

```python
# 使用API清空记忆
DELETE /npcs/张三/memories

# 或者直接删除文件
rm -rf backend/memory_data/张三
```

---

## ❓ 常见问题

### Q1: NPC为什么记不住对话?

**可能原因:**
- 记忆系统未正确初始化
- 存储路径权限问题
- 记忆被遗忘机制清除

**解决方法:**
- 检查日志中是否有"记忆系统已初始化"
- 检查memory_data目录是否存在
- 降低importance_threshold参数

### Q2: 记忆检索不准确?

**可能原因:**
- 查询语句与记忆内容相似度低
- 记忆重要性太低被过滤

**解决方法:**
- 降低min_importance参数
- 增加检索limit数量
- 使用更具体的查询语句

### Q3: 记忆占用空间太大?

**解决方法:**
- 降低max_capacity
- 提高importance_threshold
- 定期清理旧记忆

---

## 🎉 下一步

现在记忆系统已经完成,接下来我们将实现:

1. ✅ **好感度系统** - NPC与玩家的关系管理
2. ✅ **情感分析** - 使用LLM分析对话情感
3. ✅ **关系等级** - 陌生、熟悉、友好、亲密、挚友

---

## 📝 总结

✅ NPC记忆系统已成功集成到赛博小镇!

**核心特性:**
- 🧠 短期记忆 (工作记忆)
- 💾 长期记忆 (情景记忆)
- 🔍 语义检索
- 🔒 记忆隔离
- 🧹 自动遗忘

**教学价值:**
- HelloAgents Memory系统的实战应用
- 多智能体记忆管理
- 向量数据库的使用
- 记忆检索策略

**下一步:**
- 实现好感度系统
- 集成情感分析
- 完善NPC交互体验

---

