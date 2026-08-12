"""
HealthRecordAgent 基础智能体类
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Callable, Optional, ClassVar
from datetime import datetime

from core.config import get_config
from core.llm_adapter import get_llm_adapter
from core.exceptions import AgentException, TimeoutException

from enum import Enum

# 全局任务状态管理
TASKS = {}

def create_task(task_id: str, user_id: str | None = None):
    TASKS[task_id] = {
        "task_id": task_id,
        "user_id": user_id,
        "state": "running",
        "agents": {
            "PlannerAgent": "pending",
            "HealthIndicatorAgent": "pending",
            "RiskAssessmentAgent": "pending",
            "AdviceAgent": "pending",
            "ReportAgent": "pending"},
        "report": None,  # 最终报告
    }

def update_agent_state(task_id: str, agent_name: str, state: str, partial_report=None):
    task = TASKS.get(task_id)
    if not task:
        return
    task["agents"][agent_name] = state
    if partial_report:
        task["report"] = partial_report
    
def complete_task(task_id: str, report: dict):
    task = TASKS.get(task_id)
    if not task:
        return
    task["state"] = "completed"
    task["report"] = report
    for agent in task["agents"]:
        task["agents"][agent] = "completed"

def get_task_status(task_id: str):
    return TASKS.get(task_id)

class TraceLevel(str, Enum):
    INFO = "INFO"
    DEBUG = "DEBUG"
    TRACE = "TRACE"
    ERROR = "ERROR"

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    基础智能体抽象类
    """

    def __init__(
        self, name: str, llm = None, 
                 max_steps: int = None, timeout: int = None, debug: bool = True, task_id = None):
        self.name = name
        self.config = get_config()
        self.llm = llm or get_llm_adapter()
        
        self.max_steps = max_steps or self.config.agent.max_steps
        self.timeout = timeout or self.config.agent.timeout

        self.history = []
        self.tools = {}
        self.state = "idle"
        self.created_at = datetime.now()
        self.debug = debug
        self.traces: List[Dict[str, Any]] = []
        self.task_id = task_id
    # ========== 核心接口 ==========
    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """Agent 执行入口"""
        pass

    # ========== LLM 思考 ==========
    async def think(self, prompt: str, context: Dict = None) -> str:
        """调用LLM进行思考"""
        try:
            # 构建完整的提示词
            full_prompt = prompt
            
            # 添加上下文信息
            if context:
                context_str = json.dumps(context, ensure_ascii=False, indent=2)
                full_prompt = f"上下文信息:\n{context_str}\n\n任务:\n{prompt}"
            
            # 添加历史记录
            if self.history:
                history_str = "\n".join(self.history[-10:])  # 只保留最近10条
                full_prompt += f"\n\n历史记录:\n{history_str}"
            
            self.trace("LLM CALL",
                {
                    "prompt_length": len(full_prompt),
                    "history_length": len(self.history)
                },
                TraceLevel.INFO
            )

            start = datetime.now()
            
            # 调用 HelloAgent LLM
            response = await asyncio.wait_for(
                self.llm.ainvoke(full_prompt),
                timeout=self.timeout
            )

            duration = (datetime.now() - start).total_seconds()

            self.trace("LLM TTHINKING TIME",
                {
                    "duration_sec": duration,
                    "prompt_tokens": len(full_prompt),
                }
            )
            
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            self.trace("LLM RESPONSE", response_text)

            self._add_to_history(f"LLM prompt: {prompt}")
            self._add_to_history(f"LLM response: {response_text}")
            
            return response_text
            
        except asyncio.TimeoutError:
            raise TimeoutException(f"LLM思考超时")
        except Exception as e:
            raise AgentException(f"LLM思考失败: {str(e)}")
    # ========== Tool 机制 ==========
    def add_tool(self, tool_name: str, tool_func: Callable, description: str = ""):
        """添加工具"""
        self.tools[tool_name] = {
            "function": tool_func,
            "description": description
        }
    
    def get_tools_description(self) -> str:
        """获取工具描述"""
        if not self.tools:
            return "暂无可用工具"
        
        descriptions = []
        for name, tool_info in self.tools.items():
            descriptions.append(f"- {name}: {tool_info['description']}")
        
        return "\n".join(descriptions)
    
    async def call_tool(self, tool_name: str, tool_input: Any) -> Any:
        """调用工具"""
        if tool_name not in self.tools:
            raise AgentException(f"工具 '{tool_name}' 不存在")
        
        try:
            tool_func = self.tools[tool_name]["function"]
            if asyncio.iscoroutinefunction(tool_func):
                result = await asyncio.wait_for(
                    tool_func(tool_input), 
                    timeout=self.timeout
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.to_thread(tool_func, tool_input),
                    timeout=self.timeout
                )
            
            self._add_to_history(f"Tool {tool_name} called with input: {tool_input}")
            self._add_to_history(f"Tool {tool_name} result: {result}")
            
            return result
            
        except asyncio.TimeoutError:
            raise TimeoutException(f"工具 '{tool_name}' 执行超时")
        except Exception as e:
            raise AgentException(f"工具 '{tool_name}' 执行失败: {str(e)}")
    # ========== 状态 & 历史 ==========
    def _add_to_history(self, message: str):
        """添加到历史记录"""
        timestamp = datetime.now().isoformat()
        self.history.append(f"[{timestamp}] {message}")
        
        # 限制历史记录长度
        if len(self.history) > 100:
            self.history = self.history[-50:]
    
    def get_history(self, limit: int = 10) -> List[str]:
        """获取历史记录"""
        return self.history[-limit:]
    
    def clear_history(self):
        """清空历史记录"""
        self.history = []
    
    def set_state(self, state: str):
        """设置智能体状态"""
        self.state = state

        # 更新全局任务状态
        if self.task_id:
            update_agent_state(self.task_id, self.name, state)

        self.trace("STATE CHANGE",
            {
                "state": state
            }
        )
        logger.info(f"Agent {self.name} state changed to: {state}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取智能体状态"""
        return {
            "name": self.name,
            "state": self.state,
            "created_at": self.created_at.isoformat(),
            "history_count": len(self.history),
            "tools_count": len(self.tools),
            "max_steps": self.max_steps,
            "timeout": self.timeout
        }

    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        required_fields = self.get_required_fields()
        
        for field in required_fields:
            if field not in input_data:
                raise AgentException(f"缺少必需字段: {field}")
        
        return True
    
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """获取必需的输入字段"""
        pass

    def trace(self, title: str, data: Any, level: TraceLevel = TraceLevel.DEBUG):
        """统一Agent调试输出"""
        event = {
        "agent": self.name,
        "title": title,
        "timestamp": datetime.now().isoformat(),
        "data": data
        }

        self.traces.append({
            **event,
            "level": level
        })

        if not self.debug:
            return
        
        if level in [TraceLevel.INFO, TraceLevel.ERROR]:
            logger.info(f"[{self.name}] {title}")
            return

        if level == TraceLevel.DEBUG:
            preview = self._preview(data)
            logger.debug(f"[{self.name}] {title}: {preview}")

        try:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            print(data)

    def trace_step(self, step: str, status: str):
        self.trace(
            "STEP",
            {
                "step": step,
                "status": status
            }
        )
    def get_traces(self) -> List[Dict[str, Any]]:
        return self.traces
    
    def _preview(self, data, max_len: int = 300):
        """日志摘要"""
        if data is None:
            return ""

        text = str(data)

        if len(text) > max_len:
            return text[:max_len] + "...(truncated)"

        return text
