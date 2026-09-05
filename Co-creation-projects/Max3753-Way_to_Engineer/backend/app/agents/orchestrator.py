"""总控Agent - 负责路由和状态管理"""

from typing import Dict, Any, Optional
from hello_agents import SimpleAgent
from ..services.llm_service import get_llm
from .tutor_agent import TutorAgent
from .debug_agent import DebugAgent
from .review_agent import ReviewAgent
from .arch_agent import ArchAgent
from .coach_agent import CoachAgent


ORCHESTRATOR_PROMPT = """你是一个智能路由系统。你的任务是分析用户输入，决定应该交给哪个Agent处理。

**可用的Agent：**
1. tutor - 编程导师：回答编程概念、解释代码、提供学习建议
2. debug - 调试助手：分析错误信息、帮助修复代码bug
3. review - 代码审查员：审查代码质量、发现潜在问题、提供优化建议
4. arch - 架构师：设计系统架构、技术选型、解决架构问题
5. coach - 学习教练：规划学习路径、跟踪进度、提供学习建议

**判断规则：**
- 如果用户在问学习路径、课程推荐、学习计划、进度相关 → 选择 coach
- 如果用户在问编程概念、原理、怎么用 → 选择 tutor
- 如果用户在报告错误、贴了报错信息、代码不工作 → 选择 debug
- 如果用户贴了代码想让帮忙看看、想优化代码 → 选择 review
- 如果用户在问系统设计、架构、技术选型 → 选择 arch
- 如果用户输入模棱两可，同时涉及多个领域 → 选择最匹配核心意图的那个，不要选 tutor 作为默认兜底

**关键规则：**
- 用户问"这段代码有什么问题"→ 优先 debug（检查是否报错），不是 review
- 用户问"帮我写个XX功能"→ 优先 tutor（指导怎么写），不是 review
- 用户问"设计一个XX系统"→ 优先 arch，不是 tutor
- 只有完全无法判断时才用 tutor 兜底

**输出格式（只输出一个词）：**
tutor 或 debug 或 review 或 arch 或 coach
"""


class Orchestrator:
    """总控Agent"""
    
    def __init__(self):
        self.llm = get_llm()
        
        # 创建路由Agent
        self.router = SimpleAgent(
            name="路由器",
            llm=self.llm,
            system_prompt=ORCHESTRATOR_PROMPT,
        )
        
        # 创建子Agent
        self.agents = {
            "tutor": TutorAgent(),
            "debug": DebugAgent(),
            "review": ReviewAgent(),
            "arch": ArchAgent(),
            "coach": CoachAgent(),
        }
        
        print("Orchestrator初始化完成，已加载Agent:", list(self.agents.keys()))
    
    def route(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        """路由用户输入到合适的Agent"""
        # 让LLM判断应该路由到哪个Agent
        router_response = self.router.run(
            f"用户输入：{user_input}\n\n请判断应该交给哪个Agent处理。"
        )
        
        # 解析路由结果
        agent_name = router_response.strip().lower()
        if agent_name not in self.agents:
            agent_name = "tutor"  # 默认使用tutor
        
        print(f"路由结果: {agent_name}")
        
        # 调用对应的Agent（传递上下文）
        agent = self.agents[agent_name]
        return agent.chat(user_input, context=context), agent_name


# 全局实例
_orchestrator = None


def get_orchestrator() -> Orchestrator:
    """获取Orchestrator实例（单例）"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
