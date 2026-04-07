# MemoryTool 功能指南

MemoryTool 是 HelloAgents 的记忆系统统一入口，提供完整的记忆管理能力。

## 初始化

```python
from hello_agents.tools import MemoryTool

memory_tool = MemoryTool(
    user_id="user123",                    # 用户ID（数据隔离）
    memory_types=["working", "episodic", "semantic", "perceptual"]  # 启用记忆类型
)
```

## 核心操作

### 1. add - 添加记忆

```python
memory_tool.run({
    "action": "add",
    "content": "用户喜欢Python编程",
    "memory_type": "semantic",      # working/episodic/semantic/perceptual
    "importance": 0.8,              # 重要程度 0.0~1.0
    "concept": "user_preference"    # 额外元数据
})
```

**四种记忆类型示例：**

| 类型 | 用途 | 示例 |
|------|------|------|
| `working` | 临时信息 | 当前对话上下文 |
| `episodic` | 事件记录 | 用户完成了某项任务 |
| `semantic` | 知识概念 | 用户的偏好、领域知识 |
| `perceptual` | 多模态数据 | 图片、音频的描述 |

### 2. search - 搜索记忆

```python
# 基础搜索
memory_tool.run({
    "action": "search",
    "query": "Python",
    "limit": 5
})

# 按类型搜索
memory_tool.run({
    "action": "search",
    "query": "学习记录",
    "memory_type": "episodic",      # 只搜情景记忆
    "min_importance": 0.7           # 重要性阈值
})
```

### 3. forget - 遗忘记忆

```python
memory_tool.run({
    "action": "forget",
    "strategy": "importance_based", # 策略类型
    "threshold": 0.3                # 遗忘阈值
})
```

**遗忘策略：**

| 策略 | 说明 |
|------|------|
| `importance_based` | 遗忘低重要性记忆 |
| `time_based` | 遗忘过期记忆 |
| `capacity_based` | 容量不足时遗忘 |

### 4. consolidate - 记忆整合

将短期记忆转为长期记忆：

```python
memory_tool.run({
    "action": "consolidate",
    "from_type": "working",         # 从工作记忆
    "to_type": "episodic",          # 整合到情景记忆
    "importance_threshold": 0.6     # 整合阈值
})
```

### 5. 其他操作

```python
# 获取记忆摘要
memory_tool.run({"action": "summary", "limit": 10})

# 获取统计信息
memory_tool.run({"action": "stats"})

# 更新记忆
memory_tool.run({
    "action": "update",
    "memory_id": "xxx",
    "content": "更新后的内容"
})

# 删除记忆
memory_tool.run({"action": "remove", "memory_id": "xxx"})

# 清空所有记忆
memory_tool.run({"action": "clear_all"})
```

## 使用流程图

```
添加记忆(add) → 搜索记忆(search) → [可选]遗忘(forget)/整合(consolidate)
```

## 关键参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `memory_type` | str | 记忆类型：working/episodic/semantic/perceptual |
| `importance` | float | 重要程度，影响检索排序和遗忘策略 |
| `limit` | int | 返回结果数量限制 |
| `session_id` | str | 会话ID，用于关联同一对话的记忆 |

---

*详见 MemoryType.md 了解四种记忆类型的详细区别和检索策略*
