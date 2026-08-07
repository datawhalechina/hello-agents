"""Code Plan Agent - 智能代码计划工具，具备Reflection反思功能"""

import json
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime

from hello_agents.core.agent import Agent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config
from hello_agents.core.message import Message
from hello_agents.core.streaming import StreamEvent, StreamEventType
from hello_agents.core.lifecycle import LifecycleHook
from hello_agents.tools.registry import ToolRegistry


class PlanMemory:
    """
    计划记忆模块，用于存储代码计划的生成轨迹和反思记录
    """
    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def add_record(self, record_type: str, content: str, metadata: Optional[Dict] = None):
        """向记忆中添加一条新记录"""
        self.records.append({
            "type": record_type,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        })

    def get_trajectory(self) -> str:
        """将所有记忆记录格式化为一个连贯的字符串文本"""
        trajectory = ""
        for record in self.records:
            if record['type'] == 'plan':
                trajectory += f"--- 代码计划 ---\n{record['content']}\n\n"
            elif record['type'] == 'reflection':
                trajectory += f"--- 反思反馈 ---\n{record['content']}\n\n"
            elif record['type'] == 'revision':
                trajectory += f"--- 优化后计划 ---\n{record['content']}\n\n"
        return trajectory.strip()

    def get_last_plan(self) -> str:
        """获取最近一次的代码计划"""
        for record in reversed(self.records):
            if record['type'] in ['plan', 'revision']:
                return record['content']
        return ""

    def get_last_reflection(self) -> str:
        """获取最近一次的反思反馈"""
        for record in reversed(self.records):
            if record['type'] == 'reflection':
                return record['content']
        return ""


class CodePlanAgent(Agent):
    """
    Code Plan Agent - 智能代码计划工具，具备Reflection反思功能

    核心能力：
    1. 代码计划生成：根据需求描述生成结构化的代码实现计划
    2. 自我反思：对生成的代码计划进行质量评估和改进建议
    3. 迭代优化：根据反思结果优化代码计划
    4. 支持工具调用（可选）

    输出格式：
    - 代码计划采用结构化格式，包含多个步骤
    - 每个步骤包含：步骤编号、任务描述、实现要点、预期输出

    反思维度：
    - 完整性：计划是否覆盖所有需求
    - 可行性：技术方案是否可行
    - 效率：是否存在性能优化空间
    - 可维护性：代码结构是否清晰
    - 安全性：是否存在安全风险
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_reflection_iterations: int = 2,
        tool_registry: Optional['ToolRegistry'] = None,
        enable_tool_calling: bool = True,
        max_tool_iterations: int = 3
    ):
        """
        初始化CodePlanAgent

        Args:
            name: Agent名称
            llm: LLM实例
            system_prompt: 系统提示词（定义角色和行为）
            config: 配置对象
            max_reflection_iterations: 最大反思迭代次数
            tool_registry: 工具注册表（可选）
            enable_tool_calling: 是否启用工具调用
            max_tool_iterations: 最大工具调用迭代次数
        """
        # 默认 system_prompt - 代码规划专家
        default_system_prompt = """你是一位资深的软件架构师和代码规划专家。
你擅长将业务需求转化为清晰、可行的代码实现计划。

## 核心职责
1. 分析需求并生成结构化的代码实现计划
2. 确保计划覆盖所有核心功能和边界情况
3. 设计合理的模块划分和接口定义
4. 考虑代码的可维护性、扩展性和性能

## 输出格式要求
请按照以下结构化格式输出代码计划：

```code_plan
## 项目概述
[简要描述项目目标和核心功能]

## 技术栈
- 语言：[编程语言]
- 框架：[主要框架]
- 数据库：[数据库类型]
- 其他：[关键依赖]

## 目录结构
```
[项目目录结构]
```

## 实现步骤
1. [步骤1描述]
   - 实现要点：[关键实现细节]
   - 文件路径：[涉及文件]
   - 预期输出：[预期结果]

2. [步骤2描述]
   - 实现要点：[关键实现细节]
   - 文件路径：[涉及文件]
   - 预期输出：[预期结果]

...

## 关键设计
- [设计决策1]：[说明原因]
- [设计决策2]：[说明原因]

## 注意事项
- [注意事项1]
- [注意事项2]
```

请确保计划详细、清晰、可执行。"""

        super().__init__(
            name,
            llm,
            system_prompt or default_system_prompt,
            config,
            tool_registry=tool_registry
        )

        self.max_reflection_iterations = max_reflection_iterations
        self.memory = PlanMemory()
        self.enable_tool_calling = enable_tool_calling
        self.max_tool_iterations = max_tool_iterations

    def run(self, input_text: str, **kwargs) -> str:
        """
        运行CodePlanAgent

        Args:
            input_text: 需求描述
            **kwargs: 其他参数（temperature, max_tokens等）

        Returns:
            最终优化后的代码计划
        """
        print(f"\n🤖 {self.name} 开始处理代码规划任务: {input_text[:50]}...")

        # 重置记忆
        self.memory = PlanMemory()

        # 1. 生成初始代码计划
        print("\n--- 阶段1: 生成初始代码计划 ---")
        initial_plan = self._generate_code_plan(input_text, **kwargs)
        self.memory.add_record("plan", initial_plan, {"phase": "initial"})

        print(f"\n✅ 初始计划已生成:\n{initial_plan}")

        # 2. 迭代反思与优化
        for i in range(self.max_reflection_iterations):
            print(f"\n--- 阶段2: 第 {i+1}/{self.max_reflection_iterations} 轮反思优化 ---")

            # a. 反思当前计划
            print("\n-> 正在进行计划反思...")
            last_plan = self.memory.get_last_plan()
            reflection = self._reflect_on_plan(input_text, last_plan, **kwargs)
            self.memory.add_record("reflection", reflection, {"iteration": i + 1})

            print(f"\n💡 反思结果:\n{reflection}")

            # b. 检查是否需要停止
            if "无需改进" in reflection or "no need for improvement" in reflection.lower():
                print("\n✅ 反思认为计划已无需改进，任务完成。")
                break

            # c. 优化计划
            print("\n-> 正在优化代码计划...")
            refined_plan = self._refine_plan(input_text, last_plan, reflection, **kwargs)
            self.memory.add_record("revision", refined_plan, {"iteration": i + 1})

            print(f"\n🔄 优化后的计划:\n{refined_plan}")

        final_plan = self.memory.get_last_plan()
        print(f"\n--- 🎉 任务完成 ---\n最终代码计划:\n{final_plan}")

        # 保存到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_plan, "assistant"))

        return final_plan

    def _generate_code_plan(self, requirements: str, **kwargs) -> str:
        """
        生成初始代码计划

        Args:
            requirements: 需求描述
            **kwargs: LLM调用参数

        Returns:
            代码计划文本
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""请根据以下需求描述，生成一份详细的代码实现计划：

## 需求描述
{requirements}

请按照指定的格式输出代码计划。"""}
        ]

        return self._get_llm_response(messages, **kwargs)

    def _reflect_on_plan(self, requirements: str, plan: str, **kwargs) -> str:
        """
        对代码计划进行反思评估

        Args:
            requirements: 原始需求
            plan: 当前代码计划
            **kwargs: LLM调用参数

        Returns:
            反思反馈文本
        """
        reflection_prompt = f"""你是一位资深的技术评审专家。请对以下代码计划进行全面评估：

## 原始需求
{requirements}

## 当前代码计划
{plan}

## 评审维度
请从以下维度进行评估：

1. **完整性**：计划是否覆盖了所有核心需求？是否有遗漏的功能？
2. **可行性**：技术方案是否可行？是否存在技术风险？
3. **架构合理性**：模块划分是否合理？接口设计是否清晰？
4. **可维护性**：代码结构是否清晰？是否遵循最佳实践？
5. **性能考虑**：是否考虑了性能优化？是否存在潜在的性能瓶颈？
6. **安全性**：是否存在安全风险？是否需要添加安全措施？
7. **测试覆盖**：是否考虑了测试策略？关键路径是否有测试覆盖？

## 输出要求
请给出具体的改进建议。如果计划已经很好，请回答"无需改进"。"""

        messages = [
            {"role": "system", "content": "你是一位严格的技术评审专家，擅长发现代码计划中的潜在问题并提出改进建议。"},
            {"role": "user", "content": reflection_prompt}
        ]

        return self._get_llm_response(messages, **kwargs)

    def _refine_plan(self, requirements: str, current_plan: str, feedback: str, **kwargs) -> str:
        """
        根据反馈优化代码计划

        Args:
            requirements: 原始需求
            current_plan: 当前代码计划
            feedback: 反思反馈
            **kwargs: LLM调用参数

        Returns:
            优化后的代码计划
        """
        refinement_prompt = f"""请根据评审反馈优化以下代码计划：

## 原始需求
{requirements}

## 当前代码计划
{current_plan}

## 评审反馈
{feedback}

## 优化要求
请根据反馈意见对代码计划进行修改和完善，确保：
1. 解决反馈中指出的所有问题
2. 保持计划的结构化格式
3. 提供具体的改进方案

请输出优化后的完整代码计划。"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": refinement_prompt}
        ]

        return self._get_llm_response(messages, **kwargs)

    def _get_llm_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        调用LLM并获取完整响应（支持 Function Calling）

        Args:
            messages: 消息列表
            **kwargs: 其他参数

        Returns:
            LLM响应文本
        """
        # 如果没有启用工具调用，直接返回
        if not self.enable_tool_calling or not self.tool_registry:
            llm_response = self.llm.invoke(messages, **kwargs)
            return llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

        # 启用工具调用模式
        tool_schemas = self._build_tool_schemas()
        current_iteration = 0

        while current_iteration < self.max_tool_iterations:
            current_iteration += 1

            try:
                response = self.llm.invoke_with_tools(
                    messages=messages,
                    tools=tool_schemas,
                    tool_choice="auto",
                    **kwargs
                )
            except Exception as e:
                print(f"❌ LLM 调用失败: {e}")
                break

            response_message = response.choices[0].message

            # 处理工具调用
            tool_calls = response_message.tool_calls
            if not tool_calls:
                # 没有工具调用，返回文本响应
                return response_message.content or ""

            # 将助手消息添加到历史
            messages.append({
                "role": "assistant",
                "content": response_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in tool_calls
                ]
            })

            # 执行所有工具调用
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_call_id = tool_call.id

                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    print(f"❌ 工具参数解析失败: {e}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": f"错误：参数格式不正确 - {str(e)}"
                    })
                    continue

                # 执行工具（复用基类方法）
                result = self._execute_tool_call(tool_name, arguments)

                # 添加工具结果到消息
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result
                })

        # 如果超过最大迭代次数，获取最后一次回答
        if current_iteration >= self.max_tool_iterations:
            llm_response = self.llm.invoke(messages, **kwargs)
            return llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

        return ""

    async def arun_stream(
        self,
        input_text: str,
        on_start: LifecycleHook = None,
        on_finish: LifecycleHook = None,
        on_error: LifecycleHook = None,
        **kwargs
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        CodePlanAgent 流式执行

        实时返回：
        - 计划生成阶段的输出
        - 反思阶段的思考过程
        - 优化阶段的输出

        Args:
            input_text: 用户输入
            on_start: 开始钩子
            on_finish: 完成钩子
            on_error: 错误钩子
            **kwargs: 其他参数

        Yields:
            StreamEvent: 流式事件
        """
        # 发送开始事件
        yield StreamEvent.create(
            StreamEventType.AGENT_START,
            self.name,
            input_text=input_text
        )

        try:
            # 阶段 1：生成代码计划
            yield StreamEvent.create(
                StreamEventType.STEP_START,
                self.name,
                phase="plan_generation",
                description="生成初始代码计划"
            )

            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})

            plan_prompt = f"""请根据以下需求描述，生成一份详细的代码实现计划：

## 需求描述
{input_text}

请按照指定的格式输出代码计划。"""

            messages.append({"role": "user", "content": plan_prompt})

            initial_plan = ""
            async for chunk in self.llm.astream_invoke(messages, **kwargs):
                initial_plan += chunk
                yield StreamEvent.create(
                    StreamEventType.LLM_CHUNK,
                    self.name,
                    chunk=chunk,
                    phase="plan_generation"
                )

            yield StreamEvent.create(
                StreamEventType.STEP_FINISH,
                self.name,
                phase="plan_generation",
                result=initial_plan
            )

            # 阶段 2：反思与优化循环
            current_plan = initial_plan

            for iteration in range(self.max_reflection_iterations):
                # 反思阶段
                yield StreamEvent.create(
                    StreamEventType.STEP_START,
                    self.name,
                    phase="reflection",
                    iteration=iteration + 1,
                    description=f"第 {iteration + 1} 次反思"
                )

                reflection_prompt = f"""你是一位资深的技术评审专家。请对以下代码计划进行全面评估：

## 原始需求
{input_text}

## 当前代码计划
{current_plan}

## 评审维度
请从以下维度进行评估：
1. 完整性：计划是否覆盖了所有核心需求？
2. 可行性：技术方案是否可行？
3. 架构合理性：模块划分是否合理？
4. 可维护性：代码结构是否清晰？
5. 性能考虑：是否考虑了性能优化？
6. 安全性：是否存在安全风险？
7. 测试覆盖：是否考虑了测试策略？

请给出具体的改进建议。如果计划已经很好，请回答"无需改进"。"""

                reflection_messages = [{"role": "user", "content": reflection_prompt}]

                reflection = ""
                async for chunk in self.llm.astream_invoke(reflection_messages, **kwargs):
                    reflection += chunk
                    yield StreamEvent.create(
                        StreamEventType.THINKING,
                        self.name,
                        chunk=chunk,
                        phase="reflection",
                        iteration=iteration + 1
                    )

                yield StreamEvent.create(
                    StreamEventType.STEP_FINISH,
                    self.name,
                    phase="reflection",
                    iteration=iteration + 1,
                    reflection=reflection
                )

                # 检查是否需要停止
                if "无需改进" in reflection or "no need for improvement" in reflection.lower():
                    break

                # 优化阶段
                yield StreamEvent.create(
                    StreamEventType.STEP_START,
                    self.name,
                    phase="refinement",
                    iteration=iteration + 1,
                    description=f"第 {iteration + 1} 次优化"
                )

                refinement_prompt = f"""请根据评审反馈优化以下代码计划：

## 原始需求
{input_text}

## 当前代码计划
{current_plan}

## 评审反馈
{reflection}

请输出优化后的完整代码计划。"""

                refinement_messages = [{"role": "user", "content": refinement_prompt}]

                refined_plan = ""
                async for chunk in self.llm.astream_invoke(refinement_messages, **kwargs):
                    refined_plan += chunk
                    yield StreamEvent.create(
                        StreamEventType.LLM_CHUNK,
                        self.name,
                        chunk=chunk,
                        phase="refinement",
                        iteration=iteration + 1
                    )

                yield StreamEvent.create(
                    StreamEventType.STEP_FINISH,
                    self.name,
                    phase="refinement",
                    iteration=iteration + 1,
                    result=refined_plan
                )

                current_plan = refined_plan

            # 发送完成事件
            yield StreamEvent.create(
                StreamEventType.AGENT_FINISH,
                self.name,
                result=current_plan,
                total_iterations=self.max_reflection_iterations
            )

            # 保存到历史
            self.add_message(Message(input_text, "user"))
            self.add_message(Message(current_plan, "assistant"))

        except Exception as e:
            # 发送错误事件
            yield StreamEvent.create(
                StreamEventType.ERROR,
                self.name,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def get_plan_trajectory(self) -> str:
        """获取完整的计划生成轨迹"""
        return self.memory.get_trajectory()


def create_code_plan_agent(llm: HelloAgentsLLM) -> CodePlanAgent:
    """
    创建CodePlanAgent实例的便捷工厂函数

    Args:
        llm: LLM实例

    Returns:
        CodePlanAgent实例
    """
    return CodePlanAgent(
        name="CodePlanAgent",
        llm=llm,
        max_reflection_iterations=2
    )
