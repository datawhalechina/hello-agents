# MathModelAgent API 文档

## 1. 概述

MathModelAgent 提供 RESTful API 接口，支持代码执行、论文生成、知识检索等功能。

**基础信息**：
- 基础URL：`http://localhost:8000`
- API版本：`v1`
- 数据格式：`JSON`

## 2. 认证

当前版本无需认证，后续可添加 API Key 认证。

## 3. API 端点

### 3.1 代码执行

#### POST /api/code/execute

执行 Python 代码。

**请求体**：

```json
{
    "code": "print('Hello, World!')",
    "context": {
        "variable1": "value1"
    }
}
```

**响应**：

```json
{
    "success": true,
    "stdout": "Hello, World!\n",
    "stderr": "",
    "figure": null,
    "variables": {}
}
```

**错误响应**：

```json
{
    "detail": "代码执行失败: ..."
}
```

#### POST /api/code/execute-with-fix

执行代码并在失败时尝试自动修复。

**请求体**：同 `/api/code/execute`

**响应**：同 `/api/code/execute`

### 3.2 论文生成

#### GET /api/templates

列出所有可用模板。

**响应**：

```json
[
    {
        "name": "cumcm",
        "variables": ["title", "author", "abstract", ...],
        "content_length": 2048
    },
    {
        "name": "mcm_icm",
        "variables": ["title", "team_number", "abstract", ...],
        "content_length": 1856
    }
]
```

#### GET /api/templates/{template_name}

获取模板详情。

**路径参数**：
- `template_name`：模板名称

**响应**：

```json
{
    "name": "cumcm",
    "variables": ["title", "author", "abstract", ...],
    "content_length": 2048
}
```

#### POST /api/paper/generate

生成论文。

**请求体**：

```json
{
    "template_name": "cumcm",
    "context": {
        "title": "数学建模论文",
        "author": "20260001",
        "abstract": "本文研究了...",
        "keywords": "关键词1；关键词2"
    },
    "output_path": "outputs/paper.tex"
}
```

**响应**：

```json
{
    "success": true,
    "output_path": "outputs/paper.tex",
    "message": "论文生成成功"
}
```

### 3.3 知识库

#### GET /api/knowledge

列出知识库中的文档。

**响应**：

```json
[
    {
        "filename": "linear_programming.md",
        "title": "线性规划",
        "size": 1024
    }
]
```

#### POST /api/knowledge/search

搜索知识库。

**请求体**：

```json
{
    "query": "线性规划",
    "top_k": 3
}
```

**响应**：

```json
{
    "results": [
        {
            "content": "线性规划是...",
            "score": 0.95,
            "filename": "linear_programming.md"
        }
    ]
}
```

### 3.4 任务管理

#### GET /api/tasks

列出所有任务。

**响应**：

```json
[
    {
        "task_id": "abc123",
        "task_hash": "def456",
        "user_message": "分析数学建模问题",
        "status": "completed",
        "created_at": "2026-08-23T10:00:00"
    }
]
```

#### GET /api/tasks/{task_id}

获取任务详情。

**路径参数**：
- `task_id`：任务ID

**响应**：

```json
{
    "task_id": "abc123",
    "task_hash": "def456",
    "user_message": "分析数学建模问题",
    "status": "completed",
    "created_at": "2026-08-23T10:00:00",
    "metadata": {
        "result": {...}
    }
}
```

### 3.5 会话管理

#### GET /api/sessions

列出所有会话。

**响应**：

```json
[
    {
        "session_id": "sess123",
        "name": "数学建模会话",
        "project_name": "MathModelAgent",
        "created_at": "2026-08-23T10:00:00",
        "updated_at": "2026-08-23T10:30:00",
        "event_count": 10
    }
]
```

#### POST /api/sessions

创建新会话。

**请求体**：

```json
{
    "project_name": "MathModelAgent",
    "name": "新会话"
}
```

**响应**：

```json
{
    "session_id": "sess456",
    "name": "新会话",
    "project_name": "MathModelAgent",
    "created_at": "2026-08-23T11:00:00"
}
```

#### POST /api/sessions/{session_id}/resume

恢复会话。

**路径参数**：
- `session_id`：会话ID

**响应**：

```json
{
    "session_id": "sess123",
    "name": "数学建模会话",
    "resumed": true
}
```

#### POST /api/sessions/{session_id}/fork

分叉会话。

**路径参数**：
- `session_id`：会话ID

**请求体**：

```json
{
    "name": "分叉会话"
}
```

**响应**：

```json
{
    "session_id": "sess789",
    "name": "分叉会话",
    "forked_from": "sess123"
}
```

## 4. WebSocket 接口

### WS /ws

WebSocket 连接端点，支持实时通信。

**消息格式**：

```json
{
    "type": "execute",
    "code": "print('Hello')"
}
```

**响应格式**：

```json
{
    "type": "execution_result",
    "data": {
        "success": true,
        "stdout": "Hello\n",
        "stderr": ""
    }
}
```

## 5. 错误码

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 6. 示例代码

### Python 示例

```python
import requests

# 执行代码
response = requests.post(
    "http://localhost:8000/api/code/execute",
    json={
        "code": "print('Hello, World!')"
    }
)
result = response.json()
print(result["stdout"])  # Hello, World!

# 生成论文
response = requests.post(
    "http://localhost:8000/api/paper/generate",
    json={
        "template_name": "cumcm",
        "context": {
            "title": "数学建模论文",
            "author": "20260001"
        },
        "output_path": "outputs/paper.tex"
    }
)
result = response.json()
print(result["message"])  # 论文生成成功
```

### JavaScript 示例

```javascript
// 执行代码
const response = await fetch('http://localhost:8000/api/code/execute', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        code: "print('Hello, World!')"
    })
});
const result = await response.json();
console.log(result.stdout);  // Hello, World!
```

### cURL 示例

```bash
# 执行代码
curl -X POST http://localhost:8000/api/code/execute \
    -H "Content-Type: application/json" \
    -d '{"code": "print(\"Hello, World!\")"}'

# 列出模板
curl http://localhost:8000/api/templates
```
