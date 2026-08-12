```code_plan
## 项目概述
本项目旨在构建一个**高内聚、低耦合**的 Python Flask 待办事项（Todo）管理 API。基于评审反馈，我们修正了架构描述与实际目录的一致性，移除了未实现的“Repository”术语，明确采用 **Controller-Service-Model** 分层架构。核心目标在满足 CRUD 功能的基础上，强化安全性（HTTP 安全头、速率限制）、标准化错误响应格式，并优化测试环境配置以解决内存数据库与迁移工具的兼容性问题。系统支持多环境配置，确保从开发到生产的平滑过渡。

## 技术栈
- 语言：Python 3.9+
- 框架：Flask (Web 框架)
- 数据库：SQLite (开发/测试), PostgreSQL (生产推荐)
- ORM：SQLAlchemy 2.0+
- 迁移工具：Alembic (仅用于生产环境持久化版本控制，测试环境使用 db.create_all)
- 数据校验：Pydantic V2 (请求/响应模型分离)
- 安全与跨域：Flask-CORS, Flask-Talisman (安全头), Flask-Limiter (速率限制)
- 日志系统：Python Standard `logging` (含敏感字段脱敏)
- 测试框架：Pytest + Flask Test Client
- 其他：python-dotenv (环境变量加载)

## 目录结构
```
todo_api/
├── alembic/                 # Alembic 迁移脚本目录 (生产环境使用)
│   ├── versions/
│   └── env.py
├── app/
│   ├── __init__.py          # 应用工厂、日志配置、CORS/Talisman/Limiter 初始化
│   ├── config.py            # 配置类 (读取环境变量，区分 DEBUG/PRODUCTION)
│   ├── models.py            # SQLAlchemy 数据库模型 (含索引)
│   ├── schemas.py           # Pydantic 请求/响应模型 (严格分离 Input/Output)
│   ├── services/            # 业务逻辑层 (直接操作 ORM Session)
│   │   ├── __init__.py
│   │   └── todo_service.py  # Todo 核心业务逻辑
│   ├── routes/              # 路由层 (参数解析、权限检查、响应包装)
│   │   ├── __init__.py
│   │   └── todos.py         # Todo API 接口
│   ├── utils/               # 工具函数
│   │   ├── __init__.py
│   │   └── exceptions.py    # 自定义异常定义及统一错误响应格式化
│   └── extensions.py        # 扩展实例 (db, migrate, cors, limiter, talisman)
├── tests/                   # 测试目录
│   ├── conftest.py          # 测试夹具 (Fixture)，配置内存数据库 (不使用 Alembic)
│   └── test_todos.py        # 集成测试用例 (覆盖边界与并发)
├── .env                     # 本地环境变量 (不提交 Git)
├── .env.example             # 环境变量模板
├── requirements.txt         # 依赖列表
├── run.py                   # 程序入口
└── README.md                # 项目文档
```

## 实现步骤
1. **项目初始化与安全配置**
   - 实现要点：创建虚拟环境；安装依赖（含 `flask-limiter`, `flask-talisman`）；编写 `.env.example`。在 `config.py` 中增加 `DEBUG` 开关，生产环境强制关闭 Debug 模式。
   - 文件路径：`requirements.txt`, `config.py`, `.env.example`
   - 预期输出：基础工程结构搭建完成，启动时自动加载安全配置，无硬编码敏感信息。

2. **数据库设计与迁移策略**
   - 实现要点：定义 `Todo` 模型，为 `completed`, `created_at`, `due_date` 添加 `index=True`。初始化 Alembic。**注意**：仅在 `production` 模式下运行 Alembic 迁移，测试环境将跳过此步。
   - 文件路径：`app/models.py`, `alembic/versions/`
   - 预期输出：数据库表结构已建立，具备自动迁移能力，查询性能得到优化。

3. **数据校验模型构建 (Pydantic)**
   - 实现要点：在 `schemas.py` 中严格区分 `CreateTodoSchema` (输入) 和 `TodoResponseSchema` (输出)。设置字段长度限制（如 title max 255 chars），防止注入攻击。
   - 文件路径：`app/schemas.py`
   - 预期输出：非法输入（如类型错误、超长字符串）在到达路由前被拦截，返回标准 422 错误。

4. **业务逻辑层开发 (Service Layer)**
   - 实现要点：将核心逻辑剥离至 `app/services/todo_service.py`。服务层接收 DTO 对象，操作模型，返回纯数据或抛出业务异常。Service 层直接管理 SQLAlchemy Session，无需引入 Repository 层以减少复杂度。
   - 文件路径：`app/services/todo_service.py`
   - 预期输出：路由层保持简洁，业务逻辑可独立复用和测试。

5. **API 路由开发与筛选逻辑细化**
   - 实现要点：
     - 启用 CORS 及安全头 (Talisman)。
     - **状态筛选**：解析 `GET /todos?status={all|completed|incomplete}` 参数，映射为 SQLAlchemy `filter` 条件。
     - 实施速率限制：对 `/todos` 接口添加 `@limiter.limit("100 per minute")`。
     - 遵循 HTTP 状态码：GET(200), POST(201), PUT(200), DELETE(204), 错误 (4xx/5xx)。
   - 文件路径：`app/routes/todos.py`, `app/__init__.py`
   - 预期输出：符合 RESTful 标准的接口，前端可直接根据状态码处理逻辑，且具备防刷机制。

6. **全局异常处理、日志与统一响应**
   - 实现要点：
     - 定义自定义异常类（`ValidationError`, `ResourceNotFoundException`）。
     - **统一错误格式**：所有异常捕获后返回 `{"error": {"code": "ERR_CODE", "message": "Human readable msg"}}`。
     - **日志脱敏**：配置 `logging` 模块，禁止记录包含密码、Token 等敏感字段的日志内容。
     - 生产环境隐藏堆栈细节。
   - 文件路径：`app/utils/exceptions.py`, `app/__init__.py`
   - 预期输出：系统运行稳定，关键操作有日志记录，线上错误信息不泄露敏感数据，前端可解析统一错误结构。

7. **测试体系构建与环境隔离**
   - 实现要点：
     - **测试 DB 策略**：在 `conftest.py` 中使用 `sqlite:///:memory:`，调用 `db.create_all()` 创建表结构，**避免运行 Alembic 迁移脚本**。
     - 编写集成测试覆盖 CRUD、分页、**状态筛选**、边界情况（空标题、未来日期）。
     - 确保测试结束后清理临时数据（事务回滚或清空表）。
   - 文件路径：`tests/conftest.py`, `tests/test_todos.py`
   - 预期输出：自动化测试通过，CI/CD 流程可集成，保证重构不影响现有功能。

## 关键设计
- **架构一致性 (Controller-Service-Model)**：修正了原计划中提及“Repository”但无对应目录的问题。Service 层直接封装 ORM 操作，既保证了业务逻辑清晰，又避免了过度设计带来的维护成本。
- **防御性安全设计**：集成 `Flask-Talisman` 强制设置 CSP、HSTS 等安全头；使用 `Flask-Limiter` 防止 API 滥用；统一错误响应格式，避免前端因解析不一致导致崩溃。
- **测试环境解耦**：针对 SQLite 内存数据库无法运行 Alembic 的痛点，测试环境采用 `db.create_all()` 直接建表，生产环境保留 Alembic 迁移，兼顾了开发效率与部署规范。
- **输入输出严格分离**：Pydantic 模型明确区分 Request 和 Response，防止内部模型字段意外暴露给客户端，提升数据安全性。

## 注意事项
- **架构复杂度权衡**：本计划采用了企业级实践（Pydantic, Alembic, 分层），对于“简单 Todo"需求属于适度超前。若项目周期极短，可考虑移除 Alembic 和 Pydantic，简化为原生字典验证。
- **数据库迁移风险**：在生产环境执行 `alembic upgrade head` 前必须备份数据库，避免迁移脚本导致数据丢失。
- **并发写入限制**：尽管开启了 SQLite WAL 模式，但在高并发场景下仍建议迁移至 PostgreSQL，并在应用层增加乐观锁机制（如版本号字段）。
- **敏感信息保护**：`.env` 文件必须加入 `.gitignore`，确保密钥不会上传至代码仓库；日志配置需定期审查是否记录了敏感数据。
- **输入长度限制**：务必在 Pydantic 模型中限制文本字段长度，防止恶意长字符串攻击或数据库字段溢出。
- **测试数据污染**：测试套件应确保每个测试用例之间数据完全隔离，推荐使用 `transactional` 模式或每次测试后清空数据库。
```