"""Plan and Solve Agent实现 - 分解规划与逐步执行的智能体"""

import ast
from typing import Optional, List, Dict, Iterator
from ..core.agent import Agent
from ..core.llm import HelloAgentsLLM
from ..core.config import Config
from ..core.stream import StreamEvent

# 默认规划器提示词模板
DEFAULT_PLANNER_PROMPT = """
你是一个顶级的AI规划专家。你的任务是将用户提出的复杂问题分解成一个由多个简单步骤组成的行动计划。
请确保计划中的每个步骤都是一个独立的、可执行的子任务，并且严格按照逻辑顺序排列。
你的输出必须是一个Python列表，其中每个元素都是一个描述子任务的字符串。

问题: {question}

请严格按照以下格式输出你的计划:
```python
["步骤1", "步骤2", "步骤3", ...]
```
"""

# 默认执行器提示词模板
DEFAULT_EXECUTOR_PROMPT = """
你是一位顶级的AI执行专家。你的任务是严格按照给定的计划，一步步地解决问题。
你将收到原始问题、完整的计划、以及到目前为止已经完成的步骤和结果。
请你专注于解决"当前步骤"，并仅输出该步骤的最终答案，不要输出任何额外的解释或对话。

# 原始问题:
{question}

# 完整计划:
{plan}

# 历史步骤与结果:
{history}

# 当前步骤:
{current_step}

请仅输出针对"当前步骤"的回答:
"""


class Planner:
    """规划器 - 负责将复杂问题分解为简单步骤"""

    def __init__(
        self, llm_client: HelloAgentsLLM, prompt_template: Optional[str] = None
    ):
        self.llm_client = llm_client
        self.prompt_template = (
            prompt_template if prompt_template else DEFAULT_PLANNER_PROMPT
        )

    def plan(self, question: str, **kwargs) -> List[str]:
        """
        生成执行计划

        Args:
            question: 要解决的问题
            **kwargs: LLM调用参数

        Returns:
            步骤列表
        """
        prompt = self.prompt_template.format(question=question)
        messages = [{"role": "user", "content": prompt}]

        print("--- 正在生成计划 ---")
        response_text = self.llm_client.invoke(messages, **kwargs) or ""
        print(f"✅ 计划已生成:\n{response_text}")

        try:
            plan_str = response_text.split("```python")[1].split("```")[0].strip()
            plan = ast.literal_eval(plan_str)
            return plan if isinstance(plan, list) else []
        except (ValueError, SyntaxError, IndexError) as e:
            print(f"❌ 解析计划时出错: {e}")
            print(f"原始响应: {response_text}")
            return []
        except Exception as e:
            print(f"❌ 解析计划时发生未知错误: {e}")
            return []

    def stream_plan(self, question: str, **kwargs) -> Iterator[StreamEvent]:
        """
        流式生成执行计划

        Args:
            question: 要解决的问题
            **kwargs: LLM调用参数

        Yields:
            StreamEvent: 流式事件
        """
        yield StreamEvent.status("正在生成计划...")
        prompt = self.prompt_template.format(question=question)
        messages = [{"role": "user", "content": prompt}]

        full_response = ""
        for chunk in self.llm_client.stream_invoke(messages, **kwargs):
            if chunk:
                full_response += chunk
                yield StreamEvent.text(chunk)

        plan: List[str] = []
        try:
            plan_str = full_response.split("```python")[1].split("```")[0].strip()
            plan = ast.literal_eval(plan_str)
            if not isinstance(plan, list):
                plan = []
        except Exception:
            plan = []

        yield StreamEvent.status(f"计划已生成，共 {len(plan)} 个步骤")
        yield StreamEvent("plan", str(plan))


class Executor:
    """执行器 - 负责按计划逐步执行"""

    def __init__(
        self, llm_client: HelloAgentsLLM, prompt_template: Optional[str] = None
    ):
        self.llm_client = llm_client
        self.prompt_template = (
            prompt_template if prompt_template else DEFAULT_EXECUTOR_PROMPT
        )

    def stream_execute(
        self, question: str, plan: List[str], **kwargs
    ) -> Iterator[StreamEvent]:
        """
        流式按计划执行任务

        Args:
            question: 原始问题
            plan: 执行计划
            **kwargs: LLM调用参数

        Yields:
            StreamEvent: 流式事件
        """
        yield StreamEvent.status("正在执行计划...")
        history = ""

        for i, step in enumerate(plan, 1):
            yield StreamEvent.status(f"正在执行步骤 {i}/{len(plan)}: {step}")
            prompt = self.prompt_template.format(
                question=question,
                plan=plan,
                history=history if history else "无",
                current_step=step,
            )
            messages = [{"role": "user", "content": prompt}]

            step_result = ""
            for chunk in self.llm_client.stream_invoke(messages, **kwargs):
                if chunk:
                    step_result += chunk
                    yield StreamEvent.text(chunk)

            history += f"步骤 {i}: {step}\n结果: {step_result}\n\n"
            _final_answer = step_result
            yield StreamEvent.status(f"步骤 {i} 已完成")

        yield StreamEvent.status("计划执行完成")

    def execute(self, question: str, plan: List[str], **kwargs) -> str:
        """
        按计划执行任务

        Args:
            question: 原始问题
            plan: 执行计划
            **kwargs: LLM调用参数

        Returns:
            最终答案
        """
        history = ""
        final_answer = ""

        print("\n--- 正在执行计划 ---")
        for i, step in enumerate(plan, 1):
            print(f"\n-> 正在执行步骤 {i}/{len(plan)}: {step}")
            prompt = self.prompt_template.format(
                question=question,
                plan=plan,
                history=history if history else "无",
                current_step=step,
            )
            messages = [{"role": "user", "content": prompt}]

            response_text = self.llm_client.invoke(messages, **kwargs) or ""

            history += f"步骤 {i}: {step}\n结果: {response_text}\n\n"
            final_answer = response_text
            print(f"✅ 步骤 {i} 已完成，结果: {final_answer}")

        return final_answer


class PlanAndSolveAgent(Agent):
    """
    Plan and Solve Agent - 分解规划与逐步执行的智能体

    这个Agent能够：
    1. 将复杂问题分解为简单步骤
    2. 按照计划逐步执行
    3. 维护执行历史和上下文
    4. 得出最终答案

    特别适合多步骤推理、数学问题、复杂分析等任务。
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        custom_prompts: Optional[Dict[str, str]] = None,
    ):
        """
        初始化PlanAndSolveAgent

        Args:
            name: Agent名称
            llm: LLM实例
            system_prompt: 系统提示词
            config: 配置对象
            custom_prompts: 自定义提示词模板 {"planner": "", "executor": ""}
        """
        super().__init__(name, llm, system_prompt, config)

        if custom_prompts:
            planner_prompt = custom_prompts.get("planner")
            executor_prompt = custom_prompts.get("executor")
        else:
            planner_prompt = None
            executor_prompt = None

        self.planner = Planner(self.llm, planner_prompt)
        self.executor = Executor(self.llm, executor_prompt)

    def stream_run(self, input_text: str, **kwargs) -> Iterator[StreamEvent]:
        """
        流式运行Plan and Solve Agent

        Args:
            input_text: 要解决的问题
            **kwargs: 支持 conversation_id 参数

        Yields:
            StreamEvent: 流式事件
        """
        conversation_id = kwargs.pop("conversation_id", None)
        yield StreamEvent.status(f"开始处理问题: {input_text}")

        plan: List[str] = []
        for event in self.planner.stream_plan(input_text, **kwargs):
            if event.event_type == "plan":
                try:
                    plan = ast.literal_eval(event.content)
                    if not isinstance(plan, list):
                        plan = []
                except Exception:
                    plan = []
            else:
                yield event

        if not plan:
            final_answer = "无法生成有效的行动计划，任务终止。"
            yield StreamEvent.text(final_answer)
            self._save_conversation_messages(input_text, final_answer, conversation_id)
            yield StreamEvent.done(final_answer)
            return

        final_answer = ""
        for event in self.executor.stream_execute(input_text, plan, **kwargs):
            if event.event_type == "text":
                final_answer = event.content
            yield event

        self._save_conversation_messages(input_text, final_answer, conversation_id)
        yield StreamEvent.done(final_answer)

    def run(self, input_text: str, **kwargs) -> str:
        """
        运行Plan and Solve Agent

        Args:
            input_text: 要解决的问题
            **kwargs: 支持 conversation_id 参数

        Returns:
            最终答案
        """
        conversation_id = kwargs.pop("conversation_id", None)

        print(f"\n🤖 {self.name} 开始处理问题: {input_text}")

        plan = self.planner.plan(input_text, **kwargs)
        if not plan:
            final_answer = "无法生成有效的行动计划，任务终止。"
            print(f"\n--- 任务终止 ---\n{final_answer}")

            self._save_conversation_messages(input_text, final_answer, conversation_id)

            return final_answer

        final_answer = self.executor.execute(input_text, plan, **kwargs)
        print(f"\n--- 任务完成 ---\n最终答案: {final_answer}")

        self._save_conversation_messages(input_text, final_answer, conversation_id)

        return final_answer
