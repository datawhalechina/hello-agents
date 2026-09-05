# MathModelAgent 架构设计文档

## 1. 项目概述

MathModelAgent 是一个基于多智能体协作的数学建模辅助系统，借鉴 FirstCoder 的任务边界和会话管理设计，实现 RAG 知识库、HIL 人机协作、多模型调度等功能。

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户界面层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ Jupyter     │  │ Streamlit   │  │ FastAPI     │          │
│  │ Notebook    │  │ Web界面     │  │ API         │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      业务逻辑层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ 问题分析    │  │ 模型推荐    │  │ 代码生成    │          │
│  │ 智能体      │  │ 智能体      │  │ 智能体      │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ 论文生成    │  │ 代码执行    │  │ 知识检索    │          │
│  │ 智能体      │  │ 模块        │  │ 模块        │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      基础设施层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ 任务边界    │  │ 会话管理    │  │ 上下文管理  │          │
│  │ 管理器      │  │ 器          │  │ 器          │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ 日志系统    │  │ 配置管理    │  │ 模板管理    │          │
│  │             │  │             │  │ 器          │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      数据存储层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ FAISS       │  │ 文件系统    │  │ 会话存储    │          │
│  │ 向量数据库  │  │             │  │             │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模块依赖关系

```
                    ┌─────────────┐
                    │   main.py   │
                    │  (入口)     │
                    └──────┬──────┘
                           │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ MathModel   │   │ TaskBoundary│   │ Session     │
│ Agent       │   │ Manager     │   │ Manager     │
└──────┬──────┘   └─────────────┘   └─────────────┘
       │
       ├─────────────────┬─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ RAG         │   │ Code        │   │ Template    │
│ KnowledgeBase│   │ Executor    │   │ Manager     │
└─────────────┘   └─────────────┘   └─────────────┘
```

## 3. 核心模块设计

### 3.1 任务边界管理 (TaskBoundaryManager)

**设计借鉴**：FirstCoder 的任务边界设计

**核心思想**：
- 程序侧生成 task hash，不依赖模型判断
- 每次用户请求建立可追踪边界
- 切换任务时按策略整理上下文

**类设计**：

```python
class TaskBoundaryManager:
    def __init__(self):
        self.tasks: Dict[str, TaskBoundary] = {}
        self.current_task: Optional[TaskBoundary] = None
        self.task_history: List[str] = []
    
    def create_task(self, user_message: str) -> TaskBoundary:
        """创建新任务，生成task hash"""
        task_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        task_hash = self._generate_task_hash(user_message, timestamp)
        # ...
    
    def is_new_task(self, user_message: str) -> bool:
        """判断是否是新任务"""
        # 使用消息相似度判断
        # ...
```

**状态机**：

```
CREATED → IN_PROGRESS → COMPLETED
    │           │
    │           ▼
    │        PAUSED → IN_PROGRESS
    │           │
    ▼           ▼
  ABORTED    FAILED
```

### 3.2 会话管理 (SessionManager)

**设计借鉴**：FirstCoder 的会话持久化设计

**核心思想**：
- 事件流模式保存会话
- 支持 resume/fork/rename
- 会话可导出导入

**事件类型**：

```python
class EventType(Enum):
    MESSAGE = "message"          # 用户/助手消息
    TOOL_CALL = "tool_call"      # 工具调用
    TOOL_RESULT = "tool_result"  # 工具结果
    APPROVAL = "approval"        # 用户审批
    TASK_BOUNDARY = "task_boundary"  # 任务边界
    SESSION_START = "session_start"  # 会话开始
    SESSION_END = "session_end"      # 会话结束
```

**会话操作**：

```python
class SessionManager:
    def create_session(self, project_name: str) -> Session:
        """创建新会话"""
    
    def resume_session(self, session_id: str) -> Session:
        """恢复会话"""
    
    def fork_session(self, session_id: str) -> Session:
        """分叉会话"""
    
    def rename_session(self, session_id: str, new_name: str):
        """重命名会话"""
```

### 3.3 上下文管理 (ContextManager)

**设计借鉴**：FirstCoder 的上下文压缩设计

**核心思想**：
- 稳定系统前缀始终保留
- 大工具输出归档，只保留预览
- retrieve_archive 有界读取

**压缩策略**：

```python
class ContextManager:
    def compact(self, keep_recent: int = 10):
        """压缩上下文"""
        if len(self.messages) > keep_recent:
            # 归档旧消息
            old_messages = self.messages[:-keep_recent]
            archive_id = self._archive(old_messages)
            
            # 只保留最近的消息
            self.messages = self.messages[-keep_recent:]
            
            # 在消息开头添加归档引用
            self.messages.insert(0, {
                "role": "system",
                "content": f"[已归档 {len(old_messages)} 条历史消息]"
            })
    
    def retrieve_archive(self, archive_id: str, max_length: int = 1000):
        """读取归档内容"""
        # 有界读取，防止一次性加载过多内容
        # ...
```

### 3.4 代码执行 (CodeExecutor)

**设计思想**：
- 安全执行用户代码
- 支持自动修复
- 限制危险操作

**安全机制**：

```python
class SafeCodeExecutor(CodeExecutor):
    DANGEROUS_BUILTINS = ['eval', 'exec', 'compile', '__import__', 'open']
    DANGEROUS_MODULES = ['os', 'sys', 'subprocess', 'shutil']
    
    def _check_code_safety(self, code: str) -> Tuple[bool, str]:
        """检查代码安全性"""
        # 检查危险函数
        for func in self.DANGEROUS_BUILTINS:
            if func in code:
                return False, f"包含危险函数: {func}"
        
        # 检查危险模块
        for module in self.DANGEROUS_MODULES:
            if f"import {module}" in code:
                return False, f"导入受限模块: {module}"
        
        return True, ""
```

### 3.5 RAG 知识库 (RAGKnowledgeBase)

**技术栈**：
- LangChain：文档加载、文本分割、向量存储
- FAISS：向量检索
- sentence-transformers：文本向量化

**检索流程**：

```
用户查询 → Embedding → FAISS检索 → 返回相关文档
```

**优化方向**：
- 引入 Rerank 模型重排序
- 调整 chunk size 优化检索粒度
- 使用混合检索（向量 + 关键词）

## 4. 数据流设计

### 4.1 用户请求处理流程

```
用户输入
    │
    ▼
┌─────────────┐
│ 任务边界    │ ← 判断是否新任务
│ 检查        │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 上下文      │ ← 加载会话历史
│ 加载        │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 智能体      │ ← 调用LLM
│ 推理        │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 工具调用    │ ← 执行代码/检索知识
│             │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 结果处理    │ ← 归档/压缩
│             │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 会话保存    │ ← 事件流持久化
│             │
└──────┬──────┘
       │
       ▼
用户输出
```

### 4.2 代码执行流程

```
代码生成
    │
    ▼
┌─────────────┐
│ 安全检查    │ ← 检查危险操作
│             │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 代码执行    │ ← 执行Python代码
│             │
└──────┬──────┘
       │
       ├─── 成功 ──→ 返回结果
       │
       ▼
┌─────────────┐
│ 错误处理    │ ← 尝试自动修复
│             │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 重试执行    │ ← 最多3次
│             │
└──────┬──────┘
       │
       ▼
返回结果
```

## 5. 技术选型

| 组件 | 技术选型 | 选择理由 |
|------|---------|---------|
| 智能体框架 | HelloAgents | 教程要求，学习成本低 |
| RAG框架 | LangChain | 社区活跃，工具链完整 |
| 向量数据库 | FAISS | 轻量级，易于部署 |
| Web框架 | FastAPI | 异步支持，自动文档 |
| 前端框架 | Streamlit | 快速开发，Python原生 |
| 论文模板 | LaTeX | 学术标准，格式规范 |
| 日志系统 | Python logging | 标准库，无额外依赖 |

## 6. 扩展性设计

### 6.1 模型扩展

```python
class ModelScheduler:
    def register_model(self, name: str, model_class: type):
        """注册新模型"""
        self.models[name] = model_class
```

### 6.2 工具扩展

```python
class ToolRegistry:
    def register_tool(self, tool: Tool):
        """注册新工具"""
        self.tools[tool.name] = tool
```

### 6.3 模板扩展

```python
class TemplateManager:
    def add_template(self, name: str, template_path: str):
        """添加新模板"""
        self.templates[name] = self._load_template(template_path)
```

## 7. 部署架构

### 7.1 单机部署

```
┌─────────────────────────────────────┐
│           单机环境                   │
│  ┌─────────┐  ┌─────────┐          │
│  │ Streamlit│  │ FastAPI │          │
│  │ :8501    │  │ :8000   │          │
│  └─────────┘  └─────────┘          │
│           │           │             │
│           └─────┬─────┘             │
│                 │                   │
│           ┌─────▼─────┐             │
│           │ MathModel │             │
│           │ Agent     │             │
│           └───────────┘             │
└─────────────────────────────────────┘
```

### 7.2 Docker 部署

```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
  
  frontend:
    build: ./frontend
    ports:
      - "8501:8501"
    depends_on:
      - backend
```

## 8. 性能优化

### 8.1 缓存策略

- LLM 结果缓存
- 知识库检索缓存
- 模板渲染缓存

### 8.2 并发处理

- 异步 IO 处理并发请求
- 批量处理多个任务
- 线程池处理 CPU 密集任务

### 8.3 内存优化

- 使用生成器处理大数据
- 及时释放不需要的资源
- 上下文压缩减少内存占用
