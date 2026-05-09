"""任务依赖管理系统"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime
from collections import defaultdict, deque

from hello_agents.tools.base import Tool, ToolParameter, tool_action


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    task_id: str
    name: str
    description: str = None
    status: TaskStatus = TaskStatus.PENDING
    depends_on: List[str] = field(default_factory=list)
    task_type: str = "general"
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    result: Any = field(default=None, repr=False)
    error: str = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "depends_on": self.depends_on,
            "task_type": self.task_type,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "result": str(self.result) if self.result else None,
            "error": self.error,
        }


class DAGBuilder:
    """DAG构建器"""

    def __init__(self):
        self.graph: Dict[str, List[str]] = defaultdict(list)
        self.in_degree: Dict[str, int] = defaultdict(int)

    def add_edge(self, from_task: str, to_task: str):
        self.graph[from_task].append(to_task)
        self.in_degree[to_task] += 1
        if to_task not in self.graph:
            self.graph[to_task] = []
        if from_task not in self.in_degree:
            self.in_degree[from_task] = 0

    def has_cycle(self) -> bool:
        all_nodes = set(self.graph.keys())
        for targets in self.graph.values():
            all_nodes.update(targets)

        visited = set()
        rec_stack = set()

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in self.graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for node in all_nodes:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def topological_sort(self) -> List[str]:
        if self.has_cycle():
            raise ValueError("存在循环依赖，无法进行拓扑排序")

        all_nodes = set(self.graph.keys())
        for targets in self.graph.values():
            all_nodes.update(targets)

        in_degree = defaultdict(int)
        for node in all_nodes:
            in_degree[node] = self.in_degree.get(node, 0)

        queue = deque([node for node in all_nodes if in_degree[node] == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in self.graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def get_ready_tasks(self, completed: set) -> List[str]:
        ready = []
        for task_id in self.graph:
            if task_id in completed:
                continue

            deps = []
            for src, targets in self.graph.items():
                if task_id in targets:
                    deps.append(src)

            if all(d in completed for d in deps):
                ready.append(task_id)
        return ready


class NoteToolIntegration:
    """NoteTool集成模块"""

    def __init__(self, note_tool):
        self.note_tool = note_tool

    def create_task_note(self, task: Task) -> str:
        content = f"""
## 任务信息
- 名称: {task.name}
- 描述: {task.description or "无"}
- 类型: {task.task_type}
- 依赖: {", ".join(task.depends_on) if task.depends_on else "无"}

## 执行状态
当前状态: {task.status.value}
"""
        return self.note_tool.run(
            {
                "action": "create",
                "title": f"任务: {task.name}",
                "content": content,
                "note_type": "task_state",
                "tags": task.tags + ["task", task.task_id],
            }
        )

    def update_task_note(
        self, task_id: str, status: TaskStatus, error: str = None
    ) -> str:
        note = self._find_task_note(task_id)
        if not note:
            return f"未找到任务笔记: {task_id}"

        content = note.get("content", "")
        new_status = f"\n- 更新状态: {status.value}"
        if error:
            new_status += f"\n- 错误信息: {error}"

        return self.note_tool.run(
            {"action": "update", "note_id": note["id"], "content": content + new_status}
        )

    def create_blocker_note(self, task_id: str, reason: str) -> str:
        return self.note_tool.run(
            {
                "action": "create",
                "title": f"阻塞项: {task_id}",
                "content": f"任务 {task_id} 被阻塞\n\n原因: {reason}",
                "note_type": "blocker",
                "tags": ["blocker", task_id],
            }
        )

    def record_conclusion(self, task_id: str, result: Any) -> str:
        return self.note_tool.run(
            {
                "action": "create",
                "title": f"任务结论: {task_id}",
                "content": f"任务 {task_id} 执行结果:\n\n{result}",
                "note_type": "conclusion",
                "tags": ["conclusion", task_id],
            }
        )

    def _find_task_note(self, task_id: str) -> Optional[Dict]:
        _ = self.note_tool.run({"action": "search", "query": task_id, "limit": 10})
        return None


class TaskDepManager:
    """任务依赖管理器

    为Agent提供任务依赖管理能力，支持：
    - 注册任务并定义依赖关系
    - 自动检测循环依赖
    - 拓扑排序计算执行顺序
    - 自动调度任务执行
    - 与NoteTool集成（可选）

    使用示例：
    ```python
    manager = TaskDepManager(note_tool=note_tool)

    # 注册任务
    manager.register_task("task_1", "数据准备")
    manager.register_task("task_2", "模型训练", depends_on=["task_1"])
    manager.register_task("task_3", "模型评估", depends_on=["task_2"])

    # 获取执行顺序
    order = manager.get_execution_order()

    # 执行所有任务
    results = manager.execute_all(executor=lambda t: f"执行{t.name}")
    ```
    """

    def __init__(self, note_tool=None):
        self.tasks: Dict[str, Task] = {}
        self.dag = DAGBuilder()
        self.note_integration = NoteToolIntegration(note_tool) if note_tool else None

    @tool_action("task_register", "注册新任务")
    def register_task(
        self,
        task_id: str,
        name: str,
        description: str = None,
        depends_on: List[str] = None,
        task_type: str = "general",
        tags: List[str] = None,
    ) -> str:
        """注册新任务

        Args:
            task_id: 任务唯一标识
            name: 任务名称
            description: 任务描述
            depends_on: 依赖的任务ID列表
            task_type: 任务类型
            tags: 标签列表

        Returns:
            注册结果
        """
        if task_id in self.tasks:
            return f"❌ 任务已存在: {task_id}"

        if depends_on:
            for dep in depends_on:
                if dep not in self.tasks:
                    return f"❌ 依赖任务不存在: {dep}"

        task = Task(
            task_id=task_id,
            name=name,
            description=description,
            depends_on=depends_on or [],
            task_type=task_type,
            tags=tags or [],
        )

        if depends_on:
            for dep in depends_on:
                self.dag.add_edge(dep, task_id)

        self.tasks[task_id] = task

        if self.dag.has_cycle():
            del self.tasks[task_id]
            for dep in task.depends_on:
                self.dag.graph[dep].remove(task_id)
                self.dag.in_degree[task_id] -= 1
            return "❌ 添加依赖后存在循环依赖"

        if self.note_integration:
            self.note_integration.create_task_note(task)

        return f"✅ 任务注册成功: {task_id}"

    @tool_action("task_add_dep", "为任务添加依赖")
    def add_dependency(self, task_id: str, depends_on: List[str]) -> str:
        """为任务添加依赖

        Args:
            task_id: 任务ID
            depends_on: 新的依赖列表

        Returns:
            添加结果
        """
        if task_id not in self.tasks:
            return f"❌ 任务不存在: {task_id}"

        for dep in depends_on:
            if dep not in self.tasks:
                return f"❌ 依赖任务不存在: {dep}"
            self.dag.add_edge(dep, task_id)
            self.tasks[task_id].depends_on.append(dep)

        if self.dag.has_cycle():
            for dep in depends_on:
                self.dag.graph[dep].remove(task_id)
                self.dag.in_degree[task_id] -= 1
                self.tasks[task_id].depends_on.remove(dep)
            return "❌ 添加依赖后存在循环依赖"

        self.tasks[task_id].updated_at = datetime.now().isoformat()
        return f"✅ 添加依赖成功: {task_id} depends on {depends_on}"

    @tool_action("task_remove_dep", "移除任务依赖")
    def remove_dependency(self, task_id: str, depends_on: List[str]) -> str:
        """移除任务依赖

        Args:
            task_id: 任务ID
            depends_on: 要移除的依赖列表

        Returns:
            移除结果
        """
        if task_id not in self.tasks:
            return f"❌ 任务不存在: {task_id}"

        for dep in depends_on:
            if dep in self.tasks[task_id].depends_on:
                self.tasks[task_id].depends_on.remove(dep)
                if dep in self.dag.graph:
                    self.dag.graph[dep].remove(task_id)
                    self.dag.in_degree[task_id] -= 1

        self.tasks[task_id].updated_at = datetime.now().isoformat()
        return f"✅ 移除依赖成功: {task_id}"

    @tool_action("task_get_order", "获取任务执行顺序")
    def get_execution_order(self) -> str:
        """获取拓扑排序后的执行顺序

        Returns:
            执行顺序列表
        """
        try:
            order = self.dag.topological_sort()
            return "📋 执行顺序:\n" + "\n".join(
                f"{i + 1}. {t}" for i, t in enumerate(order)
            )
        except ValueError as e:
            return f"❌ {e}"

    @tool_action("task_get_ready", "获取可执行任务")
    def get_ready_tasks(self) -> str:
        """获取当前可执行的任务（所有依赖都已完成）

        Returns:
            可执行任务列表
        """
        completed = {
            tid for tid, t in self.tasks.items() if t.status == TaskStatus.COMPLETED
        }
        ready = self.dag.get_ready_tasks(completed)

        pending = [tid for tid in ready if self.tasks[tid].status == TaskStatus.PENDING]

        if not pending:
            return "📝 暂无可执行任务"

        result = "🚀 可执行任务:\n"
        for task_id in pending:
            task = self.tasks[task_id]
            result += f"- {task_id}: {task.name}\n"

        return result

    @tool_action("task_execute", "执行单个任务")
    def execute_task(self, task_id: str, executor: Callable[[Task], Any] = None) -> str:
        """执行单个任务

        Args:
            task_id: 任务ID
            executor: 执行器函数

        Returns:
            执行结果
        """
        if task_id not in self.tasks:
            return f"❌ 任务不存在: {task_id}"

        task = self.tasks[task_id]

        if task.status not in [TaskStatus.PENDING, TaskStatus.FAILED]:
            return f"❌ 任务状态不允许执行: {task.status.value}"

        for dep in task.depends_on:
            if self.tasks[dep].status != TaskStatus.COMPLETED:
                return f"❌ 依赖任务未完成: {dep}"

        task.status = TaskStatus.RUNNING
        task.updated_at = datetime.now().isoformat()

        if self.note_integration:
            self.note_integration.update_task_note(task_id, TaskStatus.RUNNING)

        try:
            if executor:
                result = executor(task)
            else:
                result = f"执行任务: {task.name}"

            task.status = TaskStatus.COMPLETED
            task.result = result
            task.updated_at = datetime.now().isoformat()

            if self.note_integration:
                self.note_integration.update_task_note(task_id, TaskStatus.COMPLETED)
                self.note_integration.record_conclusion(task_id, result)

            return f"✅ 任务执行成功: {task_id} -> {result}"

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.updated_at = datetime.now().isoformat()

            if self.note_integration:
                self.note_integration.update_task_note(
                    task_id, TaskStatus.FAILED, str(e)
                )

            return f"❌ 任务执行失败: {task_id} -> {e}"

    @tool_action("task_execute_all", "执行所有任务")
    def execute_all(self, executor: Callable[[Task], Any] = None) -> str:
        """执行所有任务

        Args:
            executor: 执行器函数

        Returns:
            执行结果摘要
        """
        results = {"completed": [], "failed": [], "skipped": []}

        while True:
            ready_tasks = self.get_ready_tasks_internal()
            if not ready_tasks:
                break

            for task_id in ready_tasks:
                self.execute_task_internal(task_id, executor)
                if self.tasks[task_id].status == TaskStatus.COMPLETED:
                    results["completed"].append(task_id)
                elif self.tasks[task_id].status == TaskStatus.FAILED:
                    results["failed"].append(task_id)

        return f"""📊 执行完成:
✅ 成功: {len(results["completed"])}
❌ 失败: {len(results["failed"])}"""

    def get_ready_tasks_internal(self) -> List[str]:
        completed = {
            tid for tid, t in self.tasks.items() if t.status == TaskStatus.COMPLETED
        }
        ready = []
        for task_id, task in self.tasks.items():
            if task_id in completed:
                continue
            if task.status != TaskStatus.PENDING:
                continue

            deps = []
            for src, targets in self.dag.graph.items():
                if task_id in targets:
                    deps.append(src)

            if all(d in completed for d in deps):
                ready.append(task_id)
        return ready

    def execute_task_internal(
        self, task_id: str, executor: Callable[[Task], Any] = None
    ) -> str:
        if task_id not in self.tasks:
            return f"❌ 任务不存在: {task_id}"

        task = self.tasks[task_id]

        if task.status not in [TaskStatus.PENDING, TaskStatus.FAILED]:
            return f"❌ 任务状态不允许执行: {task.status.value}"

        for dep in task.depends_on:
            if self.tasks[dep].status != TaskStatus.COMPLETED:
                return f"❌ 依赖任务未完成: {dep}"

        task.status = TaskStatus.RUNNING
        task.updated_at = datetime.now().isoformat()

        if self.note_integration:
            self.note_integration.update_task_note(task_id, TaskStatus.RUNNING)

        try:
            if executor:
                result = executor(task)
            else:
                result = f"执行任务: {task.name}"

            task.status = TaskStatus.COMPLETED
            task.result = result
            task.updated_at = datetime.now().isoformat()

            if self.note_integration:
                self.note_integration.update_task_note(task_id, TaskStatus.COMPLETED)
                self.note_integration.record_conclusion(task_id, result)

            return f"✅ 任务执行成功: {task_id}"

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.updated_at = datetime.now().isoformat()

            if self.note_integration:
                self.note_integration.update_task_note(
                    task_id, TaskStatus.FAILED, str(e)
                )

            return f"❌ 任务执行失败: {task_id}"

    @tool_action("task_status", "获取任务状态")
    def get_task_status(self, task_id: str) -> str:
        """获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态信息
        """
        if task_id not in self.tasks:
            return f"❌ 任务不存在: {task_id}"

        task = self.tasks[task_id]
        return f"""📊 任务状态: {task_id}
名称: {task.name}
状态: {task.status.value}
类型: {task.task_type}
依赖: {", ".join(task.depends_on) if task.depends_on else "无"}
创建时间: {task.created_at}
更新时间: {task.updated_at}"""

    @tool_action("task_list", "列出所有任务")
    def list_tasks(self) -> str:
        """列出所有任务

        Returns:
            任务列表
        """
        if not self.tasks:
            return "📝 暂无任务"

        result = f"📋 任务列表（共 {len(self.tasks)} 个）\n\n"
        for task_id, task in self.tasks.items():
            status_icon = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.RUNNING: "🔄",
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
                TaskStatus.CANCELLED: "🚫",
            }.get(task.status, "⏳")

            result += f"{status_icon} {task_id}: {task.name}\n"
            result += f"   状态: {task.status.value}\n"
            if task.depends_on:
                result += f"   依赖: {', '.join(task.depends_on)}\n"
            result += "\n"

        return result

    @tool_action("task_cancel", "取消任务")
    def cancel_task(self, task_id: str) -> str:
        """取消任务

        Args:
            task_id: 任务ID

        Returns:
            取消结果
        """
        if task_id not in self.tasks:
            return f"❌ 任务不存在: {task_id}"

        task = self.tasks[task_id]
        if task.status == TaskStatus.COMPLETED:
            return f"❌ 已完成任务无法取消: {task_id}"

        task.status = TaskStatus.CANCELLED
        task.updated_at = datetime.now().isoformat()

        return f"✅ 任务已取消: {task_id}"

    def visualize(self) -> str:
        """生成DOT格式的依赖图"""
        lines = ["digraph tasks {", "  rankdir=LR;"]

        for task_id, task in self.tasks.items():
            color = {
                TaskStatus.PENDING: "gray",
                TaskStatus.RUNNING: "blue",
                TaskStatus.COMPLETED: "green",
                TaskStatus.FAILED: "red",
            }.get(task.status, "gray")
            lines.append(f'  {task_id} [label="{task.name}", color={color}];')

        for task_id, task in self.tasks.items():
            for parent in task.depends_on:
                lines.append(f"  {parent} -> {task_id};")

        lines.append("}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tasks": {tid: t.to_dict() for tid, t in self.tasks.items()},
            "execution_order": self.dag.topological_sort(),
        }


class TaskDepTool(Tool):
    """任务依赖管理工具

    为Agent提供完整的任务依赖管理能力：
    - 创建和管理任务及其依赖关系
    - 自动检测循环依赖
    - 拓扑排序获取执行顺序
    - 任务执行状态跟踪
    - 与NoteTool集成

    使用示例：
    ```python
    tool = TaskDepTool(note_tool=note_tool)

    tool.run({
        "action": "register",
        "task_id": "task_1",
        "name": "数据准备",
        "depends_on": []
    })
    ```
    """

    def __init__(self, note_tool=None, expandable: bool = True):
        super().__init__(
            name="task_dep",
            description="任务依赖管理工具 - 管理任务依赖关系，自动调度执行顺序，支持循环检测",
            expandable=expandable,
        )
        self.manager = TaskDepManager(note_tool=note_tool)

    def run(self, parameters: Dict[str, Any]) -> str:
        if not self.validate_parameters(parameters):
            return "❌ 参数验证失败"

        action = parameters.get("action")

        if action == "register":
            return self.manager.register_task(
                task_id=parameters.get("task_id"),
                name=parameters.get("name"),
                description=parameters.get("description"),
                depends_on=parameters.get("depends_on"),
                task_type=parameters.get("task_type", "general"),
                tags=parameters.get("tags"),
            )
        elif action == "add_dep":
            return self.manager.add_dependency(
                task_id=parameters.get("task_id"),
                depends_on=parameters.get("depends_on", []),
            )
        elif action == "remove_dep":
            return self.manager.remove_dependency(
                task_id=parameters.get("task_id"),
                depends_on=parameters.get("depends_on", []),
            )
        elif action == "get_order":
            return self.manager.get_execution_order()
        elif action == "get_ready":
            return self.manager.get_ready_tasks()
        elif action == "execute":
            return self.manager.execute_task(task_id=parameters.get("task_id"))
        elif action == "execute_all":
            return self.manager.execute_all()
        elif action == "status":
            return self.manager.get_task_status(task_id=parameters.get("task_id"))
        elif action == "list":
            return self.manager.list_tasks()
        elif action == "cancel":
            return self.manager.cancel_task(task_id=parameters.get("task_id"))
        elif action == "visualize":
            return self.manager.visualize()
        else:
            return f"❌ 不支持的操作: {action}"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description=(
                    "操作类型: register(注册), add_dep(添加依赖), remove_dep(移除依赖), "
                    "get_order(执行顺序), get_ready(可执行任务), execute(执行单个), "
                    "execute_all(执行全部), status(状态), list(列表), cancel(取消), visualize(可视化)"
                ),
                required=True,
            ),
            ToolParameter(
                name="task_id",
                type="string",
                description="任务ID（register/execute/status/cancel时必需）",
                required=False,
            ),
            ToolParameter(
                name="name",
                type="string",
                description="任务名称（register时必需）",
                required=False,
            ),
            ToolParameter(
                name="description",
                type="string",
                description="任务描述",
                required=False,
            ),
            ToolParameter(
                name="depends_on",
                type="array",
                description="依赖的任务ID列表",
                required=False,
            ),
            ToolParameter(
                name="task_type",
                type="string",
                description="任务类型（默认: general）",
                required=False,
                default="general",
            ),
            ToolParameter(
                name="tags", type="array", description="标签列表", required=False
            ),
        ]
