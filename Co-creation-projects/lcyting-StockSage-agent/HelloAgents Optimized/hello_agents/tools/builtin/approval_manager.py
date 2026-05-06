"""ApprovalManager - 人机协作审批管理器

为高风险操作提供审批流程管理能力。

核心功能：
- 审批请求队列管理
- 同步/异步通知机制
- 审批决策记录与审计
- 超时自动处理

使用场景：
- SecureTerminalTool 的审批流程
- 其他需要人工审批的工具
- 企业级操作审计
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
import json
import os


class RiskLevel(Enum):
    """操作风险等级"""

    LOW = "low"  # 低风险：直接执行
    MEDIUM = "medium"  # 中风险：执行前确认
    HIGH = "high"  # 高风险：必须审批
    CRITICAL = "critical"  # 极高风险：强制审批 + 二次确认


class ApprovalStatus(Enum):
    """审批状态"""

    PENDING = "pending"  # 等待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已拒绝
    TIMEOUT = "timeout"  # 超时
    CANCELLED = "cancelled"  # 已取消


@dataclass
class ApprovalRequest:
    """审批请求"""

    id: str
    agent_id: str
    command: str
    risk_level: RiskLevel
    status: ApprovalStatus
    context: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    risk_summary: str = ""
    approved_by: Optional[str] = None
    rejected_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    timeout_seconds: int = 300

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "command": self.command,
            "risk_level": self.risk_level.value,
            "status": self.status.value,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "risk_summary": self.risk_summary,
            "approved_by": self.approved_by,
            "rejected_by": self.rejected_by,
            "rejection_reason": self.rejection_reason,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ApprovalRequest:
        """从字典创建"""
        return cls(
            id=data["id"],
            agent_id=data["agent_id"],
            command=data["command"],
            risk_level=RiskLevel(data["risk_level"]),
            status=ApprovalStatus(data["status"]),
            context=data["context"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            risk_summary=data.get("risk_summary", ""),
            approved_by=data.get("approved_by"),
            rejected_by=data.get("rejected_by"),
            rejection_reason=data.get("rejection_reason"),
            timeout_seconds=data.get("timeout_seconds", 300),
        )


@dataclass
class AuditLog:
    """审计日志条目"""

    timestamp: datetime
    event_type: str
    request_id: Optional[str]
    details: Dict[str, Any]


class ApprovalManager:
    """人机协作审批管理器

    功能：
    - 管理审批请求队列
    - 提供审批/拒绝/超时处理
    - 记录完整审计日志
    - 支持同步/异步通知回调

    用法示例：
    ```python
    # 基础使用
    manager = ApprovalManager()

    # 添加通知回调
    def on_request(request):
        print(f"需要审批: {request.command}")

    manager.add_callback(on_request)

    # 请求审批
    request_id = manager.request_approval(
        agent_id="agent_1",
        command="rm -rf /",
        risk_level=RiskLevel.CRITICAL,
        context={"workspace": "/tmp"}
    )

    # 用户审批
    manager.approve(request_id, approver="admin")

    # 查看审计日志
    logs = manager.get_audit_logs()
    ```
    """

    def __init__(
        self,
        default_timeout: int = 300,
        audit_log_path: Optional[str] = None,
        auto_approve_low_risk: bool = False,
    ):
        """初始化审批管理器

        Args:
            default_timeout: 默认超时时间（秒），默认5分钟
            audit_log_path: 审计日志文件路径，None则不保存到文件
            auto_approve_low_risk: 是否自动批准低风险操作（默认False）
        """
        self.default_timeout = default_timeout
        self.auto_approve_low_risk = auto_approve_low_risk
        self.audit_log_path = audit_log_path

        self._requests: Dict[str, ApprovalRequest] = {}
        self._callbacks: List[Callable[[ApprovalRequest], None]] = []
        self._lock = threading.RLock()
        self._audit_logs: List[AuditLog] = []

        self._execution_results: Dict[str, Any] = {}

    def add_callback(self, callback: Callable[[ApprovalRequest], None]) -> None:
        """添加审批请求通知回调

        Args:
            callback: 回调函数，接收 ApprovalRequest 参数
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[ApprovalRequest], None]) -> None:
        """移除回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def request_approval(
        self,
        agent_id: str,
        command: str,
        risk_level: RiskLevel,
        context: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> str:
        """发起审批请求

        Args:
            agent_id: 发起请求的智能体ID
            command: 待执行的命令
            risk_level: 风险等级
            context: 额外的上下文信息
            timeout_seconds: 超时时间（秒），None使用默认值

        Returns:
            str: 审批请求ID
        """
        request_id = str(uuid.uuid4())[:8]

        timeout = timeout_seconds or self.default_timeout

        request = ApprovalRequest(
            id=request_id,
            agent_id=agent_id,
            command=command,
            risk_level=risk_level,
            status=ApprovalStatus.PENDING,
            context=context or {},
            created_at=datetime.now(),
            updated_at=datetime.now(),
            timeout_seconds=timeout,
        )

        request.risk_summary = self._build_risk_summary(command, risk_level)

        with self._lock:
            self._requests[request_id] = request

        self._log_event(
            "approval_requested",
            request_id,
            {
                "agent_id": agent_id,
                "command": command,
                "risk_level": risk_level.value,
            },
        )

        for callback in self._callbacks:
            try:
                callback(request)
            except Exception as e:
                print(f"[WARNING] 回调执行失败: {e}")

        return request_id

    def approve(
        self,
        request_id: str,
        approver: str = "unknown",
    ) -> bool:
        """批准请求

        Args:
            request_id: 审批请求ID
            approver: 审批人ID

        Returns:
            bool: 是否成功
        """
        with self._lock:
            if request_id not in self._requests:
                return False

            request = self._requests[request_id]
            if request.status != ApprovalStatus.PENDING:
                return False

            request.status = ApprovalStatus.APPROVED
            request.approved_by = approver
            request.updated_at = datetime.now()

        self._log_event("approval_approved", request_id, {"approver": approver})

        return True

    def reject(
        self,
        request_id: str,
        reason: str,
        rejector: str = "unknown",
    ) -> bool:
        """拒绝请求

        Args:
            request_id: 审批请求ID
            reason: 拒绝原因
            rejector: 拒绝人ID

        Returns:
            bool: 是否成功
        """
        with self._lock:
            if request_id not in self._requests:
                return False

            request = self._requests[request_id]
            if request.status != ApprovalStatus.PENDING:
                return False

            request.status = ApprovalStatus.REJECTED
            request.rejected_by = rejector
            request.rejection_reason = reason
            request.updated_at = datetime.now()

        self._log_event(
            "approval_rejected", request_id, {"rejector": rejector, "reason": reason}
        )

        return True

    def cancel(self, request_id: str) -> bool:
        """取消请求

        Args:
            request_id: 审批请求ID

        Returns:
            bool: 是否成功
        """
        with self._lock:
            if request_id not in self._requests:
                return False

            request = self._requests[request_id]
            if request.status != ApprovalStatus.PENDING:
                return False

            request.status = ApprovalStatus.CANCELLED
            request.updated_at = datetime.now()

        self._log_event("approval_cancelled", request_id, {})

        return True

    def get_status(self, request_id: str) -> Optional[ApprovalRequest]:
        """获取审批状态

        Args:
            request_id: 审批请求ID

        Returns:
            Optional[ApprovalRequest]: 审批请求，None表示不存在
        """
        with self._lock:
            return self._requests.get(request_id)

    def get_status_by_agent(
        self, agent_id: str, status_filter: Optional[ApprovalStatus] = None
    ) -> List[ApprovalRequest]:
        """获取指定智能体的审批请求

        Args:
            agent_id: 智能体ID
            status_filter: 状态过滤器，None表示所有状态

        Returns:
            List[ApprovalRequest]: 审批请求列表
        """
        with self._lock:
            requests = [
                req for req in self._requests.values() if req.agent_id == agent_id
            ]

            if status_filter:
                requests = [req for req in requests if req.status == status_filter]

            return sorted(requests, key=lambda x: x.created_at, reverse=True)

    def list_pending(self) -> List[ApprovalRequest]:
        """列出所有待审批请求"""
        with self._lock:
            return [
                req
                for req in self._requests.values()
                if req.status == ApprovalStatus.PENDING
            ]

    def check_timeout(self) -> List[str]:
        """检查超时的请求并标记

        Returns:
            List[str]: 已超时的请求ID列表
        """
        now = datetime.now()
        timed_out_ids = []

        with self._lock:
            for request_id, request in self._requests.items():
                if request.status != ApprovalStatus.PENDING:
                    continue

                elapsed = (now - request.created_at).total_seconds()
                if elapsed > request.timeout_seconds:
                    request.status = ApprovalStatus.TIMEOUT
                    request.updated_at = now
                    timed_out_ids.append(request_id)

                    self._log_event(
                        "approval_timeout", request_id, {"elapsed_seconds": elapsed}
                    )

        return timed_out_ids

    def set_execution_result(self, request_id: str, result: Any) -> None:
        """设置执行结果（由工具调用后设置）

        Args:
            request_id: 审批请求ID
            result: 执行结果
        """
        with self._lock:
            self._execution_results[request_id] = {
                "result": result,
                "executed_at": datetime.now(),
            }

    def get_execution_result(self, request_id: str) -> Optional[Any]:
        """获取执行结果

        Args:
            request_id: 审批请求ID

        Returns:
            Optional[Any]: 执行结果
        """
        with self._lock:
            return self._execution_results.get(request_id)

    def _build_risk_summary(self, command: str, risk_level: RiskLevel) -> str:
        """构建风险摘要"""
        command_lower = command.lower()

        dangerous_patterns = [
            (r"rm?\s+-rf?\s+[\/\.\*]", "递归删除文件"),
            (r"rm?\s+-r\s+[\/\.\*]", "递归删除文件"),
            (r"dd\s+if=", "磁盘写入操作"),
            (r"mkfs", "格式化操作"),
            (r"chmod?\s+777", "设置危险权限"),
            (r"curl.*\|.*sh", "远程代码执行"),
            (r"wget.*\|.*sh", "远程代码执行"),
            (r"python.*-c.*os\.system", "代码注入"),
            (r"python.*-c.*subprocess", "代码注入"),
            (r"bash.*-c.*os\.system", "代码注入"),
            (r"sudo\s+", "提权操作"),
            (r"drop\s+table", "数据库操作"),
            (r"delete\s+from", "数据库删除"),
            (r">\s*\/\w+", "文件重定向到系统目录"),
            (r"\|\s*sh", "管道到shell执行"),
        ]

        risks = []
        for pattern, desc in dangerous_patterns:
            if __import__("re").search(pattern, command_lower):
                risks.append(desc)

        if not risks:
            if risk_level == RiskLevel.LOW:
                return "✅ 低风险操作：只读文件系统访问"
            elif risk_level == RiskLevel.MEDIUM:
                return "⚠️ 中风险操作：代码执行命令"
            elif risk_level == RiskLevel.HIGH:
                return "🔴 高风险操作：代码执行 + 敏感路径"
            else:
                return "☠️ 极高风险操作：破坏性命令"

        return "⚠️ " + "\n⚠️ ".join(risks)

    def _log_event(
        self, event_type: str, request_id: Optional[str], details: Dict[str, Any]
    ) -> None:
        """记录审计日志"""
        log_entry = AuditLog(
            timestamp=datetime.now(),
            event_type=event_type,
            request_id=request_id,
            details=details,
        )

        self._audit_logs.append(log_entry)

        if self.audit_log_path:
            self._save_to_file(log_entry)

    def _save_to_file(self, log_entry: AuditLog) -> None:
        """保存日志到文件"""
        try:
            os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)

            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "timestamp": log_entry.timestamp.isoformat(),
                            "event_type": log_entry.event_type,
                            "request_id": log_entry.request_id,
                            "details": log_entry.details,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        except Exception as e:
            print(f"[WARNING] 保存审计日志失败: {e}")

    def get_audit_logs(
        self, event_type: Optional[str] = None, limit: int = 100
    ) -> List[AuditLog]:
        """获取审计日志

        Args:
            event_type: 事件类型过滤
            limit: 返回数量限制

        Returns:
            List[AuditLog]: 审计日志列表
        """
        logs = self._audit_logs

        if event_type:
            logs = [log for log in logs if log.event_type == event_type]

        return logs[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """获取审批统计信息"""
        with self._lock:
            total = len(self._requests)
            pending = sum(
                1
                for req in self._requests.values()
                if req.status == ApprovalStatus.PENDING
            )
            approved = sum(
                1
                for req in self._requests.values()
                if req.status == ApprovalStatus.APPROVED
            )
            rejected = sum(
                1
                for req in self._requests.values()
                if req.status == ApprovalStatus.REJECTED
            )
            timed_out = sum(
                1
                for req in self._requests.values()
                if req.status == ApprovalStatus.TIMEOUT
            )

            risk_distribution = {}
            for req in self._requests.values():
                level = req.risk_level.value
                risk_distribution[level] = risk_distribution.get(level, 0) + 1

        return {
            "total_requests": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "timed_out": timed_out,
            "risk_distribution": risk_distribution,
        }

    def clear_history(self, before: Optional[datetime] = None) -> int:
        """清理历史记录

        Args:
            before: 删除此时间之前的记录，None表示删除所有

        Returns:
            int: 删除的记录数量
        """
        with self._lock:
            if before is None:
                count = len(self._requests)
                self._requests.clear()
                self._execution_results.clear()
                return count

            to_delete = [
                req_id
                for req_id, req in self._requests.items()
                if req.updated_at < before
            ]

            for req_id in to_delete:
                del self._requests[req_id]
                self._execution_results.pop(req_id, None)

            return len(to_delete)


class AsyncApprovalManager(ApprovalManager):
    """异步审批管理器

    支持异步通知和WebSocket推送等高级功能。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pending_futures: Dict[str, threading.Event] = {}

    def request_approval_async(
        self,
        agent_id: str,
        command: str,
        risk_level: RiskLevel,
        context: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> tuple[str, threading.Event]:
        """异步发起审批请求

        Args:
            同 request_approval

        Returns:
            tuple[str, threading.Event]: (请求ID, 等待事件)
        """
        request_id = self.request_approval(
            agent_id=agent_id,
            command=command,
            risk_level=risk_level,
            context=context,
            timeout_seconds=timeout_seconds,
        )

        event = threading.Event()
        self._pending_futures[request_id] = event

        return request_id, event

    def wait_for_decision(
        self, request_id: str, timeout: Optional[float] = None
    ) -> ApprovalStatus:
        """等待审批决策

        Args:
            request_id: 审批请求ID
            timeout: 超时时间（秒）

        Returns:
            ApprovalStatus: 最终状态
        """
        if request_id not in self._pending_futures:
            request = self.get_status(request_id)
            if request:
                return request.status
            return ApprovalStatus.CANCELLED

        event = self._pending_futures[request_id]

        if event.wait(timeout=timeout):
            request = self.get_status(request_id)
            return request.status if request else ApprovalStatus.CANCELLED
        else:
            return ApprovalStatus.TIMEOUT

    def _notify_decision(self, request_id: str) -> None:
        """通知决策结果"""
        if request_id in self._pending_futures:
            self._pending_futures[request_id].set()
            del self._pending_futures[request_id]

    def approve(self, request_id: str, approver: str = "unknown") -> bool:
        result = super().approve(request_id, approver)
        if result:
            self._notify_decision(request_id)
        return result

    def reject(self, request_id: str, reason: str, rejector: str = "unknown") -> bool:
        result = super().reject(request_id, reason, rejector)
        if result:
            self._notify_decision(request_id)
        return result
