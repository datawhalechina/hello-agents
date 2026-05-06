"""工具系统"""

from .base import Tool, ToolParameter
from .registry import ToolRegistry, global_registry

# 内置工具
from .builtin.search_tool import SearchTool
from .builtin.calculator import CalculatorTool
from .builtin.memory_tool import MemoryTool
from .builtin.rag_tool import RAGTool
from .builtin.note_tool import NoteTool
from .builtin.terminal_tool import TerminalTool
from .builtin.approval_manager import (
    ApprovalManager,
    AsyncApprovalManager,
    RiskLevel,
    ApprovalStatus,
    ApprovalRequest,
)
from .builtin.secure_terminal_tool import SecureTerminalTool

# 协议工具
from .builtin.protocol_tools import MCPTool, A2ATool, ANPTool

# 评估工具（第12章）
from .builtin.bfcl_evaluation_tool import BFCLEvaluationTool
from .builtin.gaia_evaluation_tool import GAIAEvaluationTool
from .builtin.llm_judge_tool import LLMJudgeTool
from .builtin.win_rate_tool import WinRateTool

# RL训练工具（第11章）
from .builtin.rl_training_tool import RLTrainingTool

# 高级功能
from .chain import (
    ToolChain,
    ToolChainManager,
    create_research_chain,
    create_simple_chain,
)
from .async_executor import (
    AsyncToolExecutor,
    run_parallel_tools,
    run_batch_tool,
    run_parallel_tools_sync,
    run_batch_tool_sync,
)

__all__ = [
    # 基础工具系统
    "Tool",
    "ToolParameter",
    "ToolRegistry",
    "global_registry",
    # 内置工具
    "SearchTool",
    "CalculatorTool",
    "MemoryTool",
    "RAGTool",
    "NoteTool",
    "TerminalTool",
    "ApprovalManager",
    "AsyncApprovalManager",
    "RiskLevel",
    "ApprovalStatus",
    "ApprovalRequest",
    "SecureTerminalTool",
    # 协议工具
    "MCPTool",
    "A2ATool",
    "ANPTool",
    # 评估工具
    "BFCLEvaluationTool",
    "GAIAEvaluationTool",
    "LLMJudgeTool",
    "WinRateTool",
    # RL训练工具
    "RLTrainingTool",
    # 工具链功能
    "ToolChain",
    "ToolChainManager",
    "create_research_chain",
    "create_simple_chain",
    # 异步执行功能
    "AsyncToolExecutor",
    "run_parallel_tools",
    "run_batch_tool",
    "run_parallel_tools_sync",
    "run_batch_tool_sync",
]
