"""
A2A ↔ AutoGen 桥接实现

功能：
- 将 A2A 消息转换为 AutoGen 格式
- 将 AutoGen 消息转换为 A2A 格式
- 支持 A2A Agent 与 AutoGen Team 通信

使用示例:
    bridge = A2AAutoGenBridge()
    autogen_msg = bridge.a2a_to_autogen({"type": "task", "task": "开发一个Web应用"})
    a2a_result = bridge.autogen_to_a2a("代码已完成", {"task_id": "123"})
"""

from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
import uuid
import threading
import asyncio


class BridgeMode(str, Enum):
    """桥接模式"""

    A2A_TO_AUTOGEN = "a2a_to_autogen"
    AUTOGEN_TO_A2A = "autogen_to_a2a"
    BIDIRECTIONAL = "bidirectional"


class MessageType(str, Enum):
    """桥接支持的消息类型"""

    TASK = "task"
    NEGOTIATION = "negotiation"
    VOTING = "voting"
    QUERY = "query"


@dataclass
class MessageMapping:
    """消息映射规则"""

    a2a_type: str
    autogen_content: str
    transform_func: Optional[Callable] = None


@dataclass
class TaskContext:
    """任务上下文"""

    task_id: str
    a2a_message: Dict[str, Any]
    autogen_message: Dict[str, Any]
    status: str = "pending"
    result: Optional[str] = None
    error: Optional[str] = None


class A2AAutoGenBridge:
    """A2A ↔ AutoGen 桥接器"""

    def __init__(self, mode: BridgeMode = BridgeMode.BIDIRECTIONAL):
        self.mode = mode
        self.message_mappings: Dict[str, MessageMapping] = {}
        self.task_registry: Dict[str, TaskContext] = {}
        self.lock = threading.Lock()

        self._register_default_mappings()

    def _register_default_mappings(self):
        """注册默认映射规则"""
        self.register_mapping(
            MessageMapping(a2a_type="task", autogen_content="execute_task")
        )
        self.register_mapping(
            MessageMapping(a2a_type="negotiation", autogen_content="negotiate")
        )
        self.register_mapping(MessageMapping(a2a_type="voting", autogen_content="vote"))
        self.register_mapping(MessageMapping(a2a_type="query", autogen_content="query"))

    def register_mapping(self, mapping: MessageMapping):
        """注册消息映射"""
        self.message_mappings[mapping.a2a_type] = mapping

    def a2a_to_autogen(self, a2a_message: Dict[str, Any]) -> Dict[str, Any]:
        """
        将 A2A 消息转换为 AutoGen 格式

        Args:
            a2a_message: A2A 协议消息，包含 type, task, task_id 等字段

        Returns:
            AutoGen 格式的消息，包含 content, metadata 等字段
        """
        msg_type = a2a_message.get("type", "task")
        task_id = a2a_message.get("task_id", str(uuid.uuid4()))

        if msg_type in self.message_mappings:
            mapping = self.message_mappings[msg_type]
            content = mapping.autogen_content
        else:
            content = a2a_message.get("task", a2a_message.get("text", ""))

        result = {
            "content": content,
            "metadata": {
                "original_type": msg_type,
                "task_id": task_id,
                "source": "a2a_bridge",
            },
        }

        if "parameters" in a2a_message:
            result["parameters"] = a2a_message["parameters"]

        if msg_type == "negotiation":
            result["content"] = (
                f"协商议题: {a2a_message.get('issue', '')}\n各方立场: {a2a_message.get('positions', {})}"
            )
        elif msg_type == "voting":
            result["content"] = (
                f"投票议题: {a2a_message.get('issue', '')}\n投票选项: {a2a_message.get('options', [])}\n投票: {a2a_message.get('votes', {})}"
            )

        return result

    def autogen_to_a2a(
        self,
        autogen_message: Union[str, Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        将 AutoGen 消息转换为 A2A 格式

        Args:
            autogen_message: AutoGen 的响应消息
            metadata: 包含原始任务元数据的字典

        Returns:
            A2A 格式的消息，包含 type, task_id, result 等字段
        """
        if isinstance(autogen_message, dict):
            content = autogen_message.get("content", str(autogen_message))
        else:
            content = str(autogen_message)

        task_id = (
            metadata.get("task_id", str(uuid.uuid4()))
            if metadata
            else str(uuid.uuid4())
        )
        original_type = metadata.get("original_type", "task") if metadata else "task"

        if original_type in ["negotiation", "voting"]:
            result_type = original_type + "_result"
        else:
            result_type = "task_result"

        return {
            "task_id": task_id,
            "type": result_type,
            "result": content,
            "status": "success",
            "source": "autogen",
        }

    def forward_to_autogen(
        self, a2a_message: Dict[str, Any], autogen_executor: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        将 A2A 消息转发给 AutoGen 执行

        Args:
            a2a_message: A2A 消息
            autogen_executor: AutoGen 团队的执行函数

        Returns:
            执行结果（已转换为 A2A 格式）
        """
        autogen_msg = self.a2a_to_autogen(a2a_message)
        task_id = autogen_msg["metadata"]["task_id"]

        context = TaskContext(
            task_id=task_id,
            a2a_message=a2a_message,
            autogen_message=autogen_msg,
            status="running",
        )

        with self.lock:
            self.task_registry[task_id] = context

        try:
            if autogen_executor:
                result = autogen_executor(autogen_msg["content"])
            else:
                result = "No executor configured"

            context.status = "completed"
            context.result = result

            return self.autogen_to_a2a(result, autogen_msg["metadata"])

        except Exception as e:
            context.status = "failed"
            context.error = str(e)

            return {
                "task_id": task_id,
                "type": "task_result",
                "result": f"Error: {str(e)}",
                "status": "error",
            }

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """查询任务状态"""
        with self.lock:
            context = self.task_registry.get(task_id)
            if context:
                return {
                    "task_id": context.task_id,
                    "status": context.status,
                    "result": context.result,
                    "error": context.error,
                }
        return None

    def list_tasks(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        with self.lock:
            return [
                {
                    "task_id": ctx.task_id,
                    "status": ctx.status,
                    "original_type": ctx.autogen_message.get("metadata", {}).get(
                        "original_type"
                    ),
                }
                for ctx in self.task_registry.values()
            ]


class AsyncA2AAutoGenBridge:
    """异步版本的桥接器"""

    def __init__(self, bridge: A2AAutoGenBridge):
        self.bridge = bridge

    async def forward_async(
        self, a2a_message: Dict[str, Any], autogen_team_executor: Callable
    ) -> Dict[str, Any]:
        """异步转发消息"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.bridge.forward_to_autogen, a2a_message, autogen_team_executor
        )


class A2AAutoGenGateway:
    """A2A ↔ AutoGen HTTP 网关"""

    def __init__(
        self,
        bridge: Optional[A2AAutoGenBridge] = None,
        autogen_team_factory: Optional[Callable] = None,
    ):
        self.bridge = bridge or A2AAutoGenBridge()
        self.autogen_team_factory = autogen_team_factory

    def run(self, host: str = "0.0.0.0", port: int = 5000):
        """启动网关服务"""
        try:
            from flask import Flask, request, jsonify
        except ImportError:
            raise ImportError("Requires Flask: pip install flask")

        app = Flask("A2A-AutoGen-Gateway")

        @app.route("/forward", methods=["POST"])
        def forward():
            """转发 A2A 消息到 AutoGen"""
            data = request.get_json() or {}

            if self.autogen_team_factory:
                team = self.autogen_team_factory()
                result = self.bridge.forward_to_autogen(data, team.execute)
            else:
                result = self.bridge.forward_to_autogen(
                    data, lambda x: f"Executed: {x}"
                )

            return jsonify(result)

        @app.route("/status/<task_id>", methods=["GET"])
        def get_status(task_id):
            """查询任务状态"""
            status = self.bridge.get_task_status(task_id)
            if status:
                return jsonify(status)
            return jsonify({"error": "Task not found"}), 404

        @app.route("/tasks", methods=["GET"])
        def list_tasks():
            """列出所有任务"""
            return jsonify({"tasks": self.bridge.list_tasks()})

        @app.route("/health", methods=["GET"])
        def health():
            return jsonify(
                {
                    "status": "healthy",
                    "bridge": "A2A-AutoGen",
                    "mode": self.bridge.mode.value,
                }
            )

        print(f"🚀 A2A ↔ AutoGen Gateway starting on {host}:{port}")
        print("📋 Endpoints:")
        print("   POST /forward - 转发 A2A 消息")
        print("   GET  /status/<task_id> - 查询状态")
        print("   GET  /tasks - 列出任务")
        print("   GET  /health - 健康检查")

        app.run(host=host, port=port, debug=False)


def create_sample_autogen_team():
    """Create sample AutoGen team executor"""

    class SampleTeam:
        def execute(self, task_content: str = "") -> str:
            responses = {
                "execute_task": "Task executed successfully",
                "negotiate": "Negotiation complete, consensus reached",
                "vote": "Voting complete, option A wins",
            }
            return responses.get(task_content, f"Executed: {task_content}")

    return SampleTeam()


if __name__ == "__main__":
    import sys
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("=" * 60)
    print("A2A <-> AutoGen Bridge Demo")
    print("=" * 60)

    bridge = A2AAutoGenBridge()

    test_cases = [
        {
            "name": "Normal Task",
            "message": {
                "type": "task",
                "task_id": "task-001",
                "task": "Develop a Bitcoin price display web app",
            },
        },
        {
            "name": "Negotiation Request",
            "message": {
                "type": "negotiation",
                "task_id": "task-002",
                "issue": "paper score",
                "positions": {"researcher": "85", "reviewer": "72"},
            },
        },
        {
            "name": "Voting Request",
            "message": {
                "type": "voting",
                "task_id": "task-003",
                "issue": "choose topic",
                "options": ["AI Medical", "AI Education"],
                "votes": {"researcher": "AI Medical", "writer": "AI Education"},
            },
        },
    ]

    for case in test_cases:
        print(f"\n[{case['name']}]")
        print(f"Input: {case['message']}")

        autogen_msg = bridge.a2a_to_autogen(case["message"])
        print(f"Convert(A2A->AutoGen): {autogen_msg['content'][:50]}...")

        result = bridge.autogen_to_a2a("AutoGen team executed", autogen_msg["metadata"])
        print(f"Convert(AutoGen->A2A): {result['task_id']}")

    print("\n" + "=" * 60)
    print("Test Forward")

    team_executor = create_sample_autogen_team()
    result = bridge.forward_to_autogen(test_cases[0]["message"], team_executor.execute)
    print(f"Forward result: {result}")

    print(f"\nTask status: {bridge.get_task_status(result['task_id'])}")
