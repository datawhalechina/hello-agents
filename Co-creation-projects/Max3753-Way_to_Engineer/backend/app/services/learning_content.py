from typing import List, Dict, Optional
from ..models.learning import (
    LearningPath, LearningPathData, LearningModule, LearningLesson, ModuleStatus
)


def get_frontend_path() -> LearningPathData:
    return LearningPathData(
        path=LearningPath.FRONTEND,
        title="前端开发",
        description="从HTML/CSS基础到现代前端框架",
        icon="🎨",
        modules=[
            LearningModule(
                id="fe-html-css",
                title="HTML & CSS 基础",
                description="网页结构与样式入门",
                icon="📝",
                order=1,
                status=ModuleStatus.NOT_STARTED,
                lessons=[
                    LearningLesson(
                        id="fe-html-01",
                        title="HTML文档结构",
                        description="DOCTYPE、head、body标签",
                        type="theory",
                        duration_minutes=15
                    ),
                    LearningLesson(
                        id="fe-html-02",
                        title="常用HTML标签",
                        description="标题、段落、链接、图片、列表",
                        type="theory",
                        duration_minutes=20
                    ),
                    LearningLesson(
                        id="fe-css-01",
                        title="CSS选择器",
                        description="元素、类、ID、属性选择器",
                        type="theory",
                        duration_minutes=20
                    ),
                    LearningLesson(
                        id="fe-css-02",
                        title="盒模型与布局",
                        description="margin、padding、border、display",
                        type="practice",
                        duration_minutes=30
                    ),
                    LearningLesson(
                        id="fe-css-03",
                        title="Flexbox布局",
                        description="弹性盒子布局完全指南",
                        type="practice",
                        duration_minutes=40
                    ),
                ]
            ),
            LearningModule(
                id="fe-javascript",
                title="JavaScript 核心",
                description="JavaScript语言基础",
                icon="⚡",
                order=2,
                status=ModuleStatus.LOCKED,
                lessons=[
                    LearningLesson(
                        id="fe-js-01",
                        title="变量与数据类型",
                        description="let、const、基本类型与引用类型",
                        type="theory",
                        duration_minutes=25
                    ),
                    LearningLesson(
                        id="fe-js-02",
                        title="函数与作用域",
                        description="函数声明、箭头函数、闭包",
                        type="theory",
                        duration_minutes=30
                    ),
                    LearningLesson(
                        id="fe-js-03",
                        title="DOM操作",
                        description="查询、修改、创建DOM元素",
                        type="practice",
                        duration_minutes=40
                    ),
                    LearningLesson(
                        id="fe-js-04",
                        title="事件处理",
                        description="事件监听、事件委托、事件对象",
                        type="practice",
                        duration_minutes=35
                    ),
                ]
            ),
            LearningModule(
                id="fe-vue",
                title="Vue.js 框架",
                description="现代Vue 3开发",
                icon="💚",
                order=3,
                status=ModuleStatus.LOCKED,
                lessons=[
                    LearningLesson(
                        id="fe-vue-01",
                        title="Vue 3 基础",
                        description="模板语法、响应式数据、computed",
                        type="theory",
                        duration_minutes=30
                    ),
                    LearningLesson(
                        id="fe-vue-02",
                        title="组件系统",
                        description="组件创建、props、events、slots",
                        type="theory",
                        duration_minutes=35
                    ),
                    LearningLesson(
                        id="fe-vue-03",
                        title="组合式API",
                        description="setup、ref、reactive、生命周期",
                        type="practice",
                        duration_minutes=40
                    ),
                    LearningLesson(
                        id="fe-vue-04",
                        title="状态管理",
                        description="Pinia状态管理实践",
                        type="practice",
                        duration_minutes=30
                    ),
                ]
            ),
            LearningModule(
                id="fe-project",
                title="实战项目",
                description="构建完整的前端应用",
                icon="🚀",
                order=4,
                status=ModuleStatus.LOCKED,
                lessons=[
                    LearningLesson(
                        id="fe-proj-01",
                        title="项目规划",
                        description="需求分析、技术选型、架构设计",
                        type="theory",
                        duration_minutes=30
                    ),
                    LearningLesson(
                        id="fe-proj-02",
                        title="核心功能开发",
                        description="实现主要功能模块",
                        type="project",
                        duration_minutes=120
                    ),
                    LearningLesson(
                        id="fe-proj-03",
                        title="优化与部署",
                        description="性能优化、构建部署",
                        type="project",
                        duration_minutes=60
                    ),
                ]
            ),
        ]
    )


def get_backend_path() -> LearningPathData:
    return LearningPathData(
        path=LearningPath.BACKEND,
        title="后端开发",
        description="Python后端开发与API设计",
        icon="⚙️",
        modules=[
            LearningModule(
                id="be-python",
                title="Python 基础",
                description="Python语言核心",
                icon="🐍",
                order=1,
                status=ModuleStatus.NOT_STARTED,
                lessons=[
                    LearningLesson(
                        id="be-py-01",
                        title="Python语法基础",
                        description="变量、类型、运算符",
                        type="theory",
                        duration_minutes=20
                    ),
                    LearningLesson(
                        id="be-py-02",
                        title="控制流与函数",
                        description="条件、循环、函数定义",
                        type="theory",
                        duration_minutes=25
                    ),
                    LearningLesson(
                        id="be-py-03",
                        title="面向对象编程",
                        description="类、继承、多态",
                        type="theory",
                        duration_minutes=30
                    ),
                    LearningLesson(
                        id="be-py-04",
                        title="异常处理与文件操作",
                        description="try/except、文件读写",
                        type="practice",
                        duration_minutes=25
                    ),
                ]
            ),
            LearningModule(
                id="be-api",
                title="REST API 设计",
                description="FastAPI构建RESTful服务",
                icon="🔌",
                order=2,
                status=ModuleStatus.LOCKED,
                lessons=[
                    LearningLesson(
                        id="be-api-01",
                        title="HTTP协议基础",
                        description="请求方法、状态码、头部",
                        type="theory",
                        duration_minutes=20
                    ),
                    LearningLesson(
                        id="be-api-02",
                        title="FastAPI入门",
                        description="路由、请求、响应",
                        type="theory",
                        duration_minutes=30
                    ),
                    LearningLesson(
                        id="be-api-03",
                        title="数据验证",
                        description="Pydantic模型、请求验证",
                        type="practice",
                        duration_minutes=35
                    ),
                    LearningLesson(
                        id="be-api-04",
                        title="数据库集成",
                        description="SQLAlchemy、数据库操作",
                        type="practice",
                        duration_minutes=45
                    ),
                ]
            ),
            LearningModule(
                id="be-system",
                title="系统设计",
                description="架构设计与最佳实践",
                icon="🏗️",
                order=3,
                status=ModuleStatus.LOCKED,
                lessons=[
                    LearningLesson(
                        id="be-sys-01",
                        title="设计模式",
                        description="常用设计模式与应用场景",
                        type="theory",
                        duration_minutes=40
                    ),
                    LearningLesson(
                        id="be-sys-02",
                        title="性能优化",
                        description="缓存、异步、并发",
                        type="theory",
                        duration_minutes=35
                    ),
                    LearningLesson(
                        id="be-sys-03",
                        title="安全实践",
                        description="认证、授权、数据安全",
                        type="practice",
                        duration_minutes=30
                    ),
                ]
            ),
            LearningModule(
                id="be-project",
                title="实战项目",
                description="构建完整的后端服务",
                icon="🚀",
                order=4,
                status=ModuleStatus.LOCKED,
                lessons=[
                    LearningLesson(
                        id="be-proj-01",
                        title="项目架构",
                        description="目录结构、配置管理",
                        type="theory",
                        duration_minutes=25
                    ),
                    LearningLesson(
                        id="be-proj-02",
                        title="核心功能实现",
                        description="业务逻辑开发",
                        type="project",
                        duration_minutes=120
                    ),
                    LearningLesson(
                        id="be-proj-03",
                        title="测试与部署",
                        description="单元测试、集成测试、部署",
                        type="project",
                        duration_minutes=60
                    ),
                ]
            ),
        ]
    )


def get_fullstack_path() -> LearningPathData:
    return LearningPathData(
        path=LearningPath.FULLSTACK,
        title="全栈开发",
        description="前端+后端全栈技能",
        icon="🌐",
        modules=[
            LearningModule(
                id="fs-web-basics",
                title="Web基础",
                description="HTML/CSS/JS核心",
                icon="🌍",
                order=1,
                status=ModuleStatus.NOT_STARTED,
                lessons=[
                    LearningLesson(
                        id="fs-web-01",
                        title="HTML/CSS基础",
                        description="网页结构与样式",
                        type="theory",
                        duration_minutes=25
                    ),
                    LearningLesson(
                        id="fs-web-02",
                        title="JavaScript基础",
                        description="JS核心概念",
                        type="theory",
                        duration_minutes=30
                    ),
                    LearningLesson(
                        id="fs-web-03",
                        title="DOM与事件",
                        description="页面交互实现",
                        type="practice",
                        duration_minutes=35
                    ),
                ]
            ),
            LearningModule(
                id="fs-frontend",
                title="前端框架",
                description="Vue.js开发",
                icon="💚",
                order=2,
                status=ModuleStatus.LOCKED,
                lessons=[
                    LearningLesson(
                        id="fs-fe-01",
                        title="Vue 3基础",
                        description="组件、响应式、生命周期",
                        type="theory",
                        duration_minutes=30
                    ),
                    LearningLesson(
                        id="fs-fe-02",
                        title="路由与状态",
                        description="Vue Router、Pinia",
                        type="practice",
                        duration_minutes=40
                    ),
                ]
            ),
            LearningModule(
                id="fs-backend",
                title="后端开发",
                description="Python + FastAPI",
                icon="⚙️",
                order=3,
                status=ModuleStatus.LOCKED,
                lessons=[
                    LearningLesson(
                        id="fs-be-01",
                        title="Python基础",
                        description="语法、OOP、异常处理",
                        type="theory",
                        duration_minutes=30
                    ),
                    LearningLesson(
                        id="fs-be-02",
                        title="FastAPI开发",
                        description="路由、验证、数据库",
                        type="practice",
                        duration_minutes=45
                    ),
                ]
            ),
            LearningModule(
                id="fs-fullstack",
                title="全栈实战",
                description="构建完整应用",
                icon="🚀",
                order=4,
                status=ModuleStatus.LOCKED,
                lessons=[
                    LearningLesson(
                        id="fs-fs-01",
                        title="前后端联调",
                        description="API对接、数据流",
                        type="practice",
                        duration_minutes=60
                    ),
                    LearningLesson(
                        id="fs-fs-02",
                        title="部署上线",
                        description="构建、部署、监控",
                        type="project",
                        duration_minutes=60
                    ),
                ]
            ),
        ]
    )


def _inject_lesson_content(path_data: LearningPathData):
    """为路径中的所有课程注入Markdown内容"""
    from .lesson_content import get_lesson_content
    for module in path_data.modules:
        for lesson in module.lessons:
            if not lesson.content_markdown:
                lesson.content_markdown = get_lesson_content(
                    lesson.id, lesson.title, lesson.type, lesson.description
                )


def get_learning_path(path: LearningPath) -> LearningPathData:
    if path == LearningPath.FRONTEND:
        data = get_frontend_path()
    elif path == LearningPath.BACKEND:
        data = get_backend_path()
    else:
        data = get_fullstack_path()
    _inject_lesson_content(data)
    return data


def get_all_paths() -> List[LearningPathData]:
    paths = [
        get_frontend_path(),
        get_backend_path(),
        get_fullstack_path()
    ]
    for p in paths:
        _inject_lesson_content(p)
    return paths


def find_next_lesson(path_type: str, current_lesson_id: str, completed_lessons: List[str]) -> Optional[Dict]:
    """根据当前课程，找到路径中下一个未完成的课程
    
    Args:
        path_type: 路径类型 ('frontend' / 'backend' / 'fullstack')
        current_lesson_id: 当前课程的 lesson_id
        completed_lessons: 已完成的 lesson_id 列表
    
    Returns:
        下一个课程的 {title, description, id} 或 None
    """
    try:
        path_enum = LearningPath(path_type)
        path_data = get_learning_path(path_enum)
    except Exception:
        return None

    # 扁平化所有课程（保持顺序）
    all_lessons: List[Dict] = []
    for module in path_data.modules:
        for lesson in module.lessons:
            all_lessons.append({
                "id": lesson.id,
                "title": lesson.title,
                "description": lesson.description,
                "module_title": module.title,
                "module_id": module.id,
            })

    # 找到当前课程在列表中的位置
    current_idx = None
    for i, l in enumerate(all_lessons):
        if l["id"] == current_lesson_id:
            current_idx = i
            break

    if current_idx is None:
        return None

    # 从当前课程之后找第一个未完成的
    for i in range(current_idx + 1, len(all_lessons)):
        if all_lessons[i]["id"] not in completed_lessons:
            return all_lessons[i]

    return None
