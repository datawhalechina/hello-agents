# agents/vibe_learning_agent.py
"""互动学习 Agent - 通过对话和测验巩固知识"""

import json
from datetime import datetime
from typing import Dict, List
from hello_agents import HelloAgentsLLM
from hello_agents import SimpleAgent
from specialist.quiz_generator import QuizGeneratorAgent
from core.file_manager import FileManager
from core.summary_manager import SummaryManager


class VibeLearningAgent(SimpleAgent):
    """
    互动学习专家

    功能：
    - 支持两种模式：free（自由对话）和 quiz（结构化测验）
    - 根据学习计划生成问题
    - 评估用户回答并提供反馈
    - 动态调整问题难度
    - 生成会话总结
    """

    def __init__(self, llm: HelloAgentsLLM, file_manager: FileManager, streaming: bool = None):
        """
        初始化 VibeLearningAgent

        Args:
            llm: HelloAgentsLLM 实例
            file_manager: FileManager 实例
            streaming: 是否启用流式输出（None = 自动检测）
        """
        system_prompt = """
你是专业的学习教练。

工作流程：
1. 读取学习计划（plan.md），了解知识体系
2. 根据模式（free/quiz）生成初始问题
3. 评估用户回答，给予反馈
4. 动态调整问题难度
5. 结束时生成会话总结

模式差异：
- free: 开放性问题，鼓励讨论，引导思考
- quiz: 结构化考察，固定问题，自动评分

反馈技巧：
- 肯定正确的部分
- 指出需要改进的地方
- 提供额外的知识点链接
- 鼓励继续探索
"""

        self.llm = llm
        self.file_manager = file_manager
        self.quiz_generator = QuizGeneratorAgent(llm)
        self.max_iterations = 10

        # 添加流式输出支持
        from utils.streaming import should_stream
        self.streaming = should_stream(streaming)

        # 使用父类初始化
        super().__init__("VibeLearningAgent", llm, system_prompt)

    def start_session(
        self, domain: str, mode: str = "free"
    ) -> str:
        """
        开始互动学习会话（只生成第一个问题）

        Args:
            domain: 领域名称
            mode: 学习模式（free/quiz）

        Returns:
            第一个问题
        """
        # 检查领域是否存在
        if not self.file_manager.domain_exists(domain):
            return f"❌ 领域 '{domain}' 不存在。请先使用 /create 创建学习计划。"

        # 读取学习计划
        try:
            plan = self.file_manager.read_plan(domain)
        except Exception as e:
            return f"❌ 读取学习计划失败：{e}"

        # 生成第一个问题
        question = self._generate_first_question(plan, mode)

        # 保存问题到会话历史（用于后续继续）
        self._save_session_start(domain, mode, question)

        return f"""💬 {mode.upper()} 模式学习会话开始

{question}

💡 提示：输入你的回答开始对话
"""

    def _save_session_start(self, domain: str, mode: str, question: str) -> None:
        """
        保存会话开始状态

        Args:
            domain: 领域名称
            mode: 模式
            question: 第一个问题
        """
        session_path = self.file_manager.BASE_DIR / domain / "sessions"
        session_path.mkdir(parents=True, exist_ok=True)

        # 创建临时会话文件
        temp_file = session_path / ".current_session.txt"
        temp_file.write_text(
            f"{mode}\n{datetime.now().strftime('%Y-%m-%d %H:%M')}\n{question}",
            encoding='utf-8'
        )

    def continue_session(self, domain: str, user_answer: str, mode: str) -> str:
        """
        继续对话会话

        Args:
            domain: 领域名称
            user_answer: 用户回答
            mode: 模式

        Returns:
            反馈和下一个问题
        """
        try:
            # 读取计划
            plan = self.file_manager.read_plan(domain)

            # 读取上一个问题（从临时文件）
            session_path = self.file_manager.BASE_DIR / domain / "sessions"
            temp_file = session_path / ".current_session.txt"

            if temp_file.exists():
                lines = temp_file.read_text(encoding='utf-8').strip().split('\n')
                last_question = lines[-1] if len(lines) > 0 else ""
            else:
                last_question = "请描述你对这个主题的理解。"

            # 生成反馈
            feedback = self._generate_feedback(last_question, user_answer, plan)

            # 生成下一个问题
            next_question = self._generate_next_question(plan, [last_question, user_answer], mode)

            # 更新临时文件
            temp_file.write_text(
                f"{mode}\n{datetime.now().strftime('%Y-%m-%d %H:%M')}\n{next_question}",
                encoding='utf-8'
            )

            # 返回反馈和下一个问题
            return f"""✅ {feedback}

{next_question}

💡 输入你的回答，或输入"退出"结束会话
"""

        except Exception as e:
            # 发生错误时保存会话并返回
            return f"❌ 处理回答时发生错误：{e}\n\n会话已自动保存。"

    def _save_conversation_history(self, domain: str, mode: str, conversation: List[str], error: str = None) -> None:
        """
        保存对话历史

        Args:
            domain: 领域名称
            mode: 模式
            conversation: 对话记录
            error: 错误信息（可选）
        """
        try:
            session_path = self.file_manager.BASE_DIR / domain / "sessions"
            timestamp = datetime.now().strftime("%Y-%m-%d %H-%M")

            content = f"# 学习会话 - {domain}\n"
            content += f"模式: {mode}\n"
            content += f"时间: {timestamp}\n\n"

            if conversation:
                content += "\n".join(conversation)

            if error:
                content += f"\n\n错误: {error}"

            # 保存会话
            self.file_manager.save_session(domain, content)

        except Exception:
            pass  # 静默失败，避免干扰主流程

    def _generate_first_question(self, plan: str, mode: str) -> str:
        """
        生成第一个问题

        Args:
            plan: 学习计划
            mode: 模式（free/quiz）

        Returns:
            问题文本
        """
        if mode == "quiz":
            # quiz 模式：使用 QuizGenerator
            return self.quiz_generator.generate_question(plan, difficulty="easy")
        else:
            # free 模式：生成开放性问题
            user_prompt = f"""基于以下学习计划，生成一个开放性的问题，开始对话：

{plan[:2000]}

问题应该：
1. 从基础概念开始
2. 引导用户思考和表达
3. 不要太难，建立信心

直接返回问题，不需要额外说明。
"""

            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的学习教练，擅长通过提问引导学习。",
                },
                {"role": "user", "content": user_prompt},
            ]

            try:
                if self.streaming:
                    from utils.streaming import stream_response
                    return stream_response(self.llm, messages)
                else:
                    return self.llm.invoke(messages).strip()
            except Exception:
                return "请简单描述一下你对这个主题的理解，以及你最想学习的部分是什么？"

    def _generate_next_question(
        self, plan: str, history: List[str], mode: str
    ) -> str:
        """
        生成下一个问题（根据历史对话调整）

        Args:
            plan: 学习计划
            history: 对话历史
            mode: 模式

        Returns:
            问题文本
        """
        # 提取最后一个问题和回答（如果有）
        if len(history) < 3:
            return self._generate_first_question(plan, mode)

        if mode == "quiz":
            # quiz 模式：逐步增加难度
            difficulty = min(1.0, 0.3 + len(history) * 0.1)
            return self.quiz_generator.generate_question(plan, difficulty=difficulty)
        else:
            # free 模式：基于上下文生成问题
            recent_context = "\n".join(history[-5:])

            user_prompt = f"""基于以下对话历史，生成下一个问题：

{recent_context}

要求：
1. 继续深入探讨
2. 根据用户之前的回答调整方向
3. 保持对话流畅性

直接返回问题，不需要额外说明。
"""

            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的学习教练，擅长通过对话引导深入学习。",
                },
                {"role": "user", "content": user_prompt},
            ]

            try:
                if self.streaming:
                    from utils.streaming import stream_response
                    return stream_response(self.llm, messages)
                else:
                    return self.llm.invoke(messages).strip()
            except Exception:
                return "请继续分享你的想法，或者有什么具体的问题想讨论吗？"

    def _generate_feedback(
        self, question: str, answer: str, plan: str
    ) -> str:
        """
        生成反馈

        Args:
            question: 问题
            answer: 用户回答
            plan: 学习计划

        Returns:
            反馈文本
        """
        user_prompt = f"""问题：{question}

用户回答：{answer}

参考计划：{plan[:1000]}

生成友好的反馈（100字以内）：
1. 肯定正确的部分
2. 指出需要改进的地方（温和地）
3. 提供一个额外的知识点或建议
"""

        messages = [
            {
                "role": "system",
                "content": "你是一个友善的学习教练，善于鼓励和引导。",
            },
            {"role": "user", "content": user_prompt},
        ]

        try:
            if self.streaming:
                from utils.streaming import stream_response
                return stream_response(self.llm, messages)
            else:
                return self.llm.invoke(messages).strip()
        except Exception:
            return "好的，谢谢你的回答。让我们继续深入探讨这个话题。"

    def _evaluate_answer(
        self, question: str, answer: str, plan: str
    ) -> Dict[str, any]:
        """
        评估回答质量

        Args:
            question: 问题
            answer: 回答
            plan: 学习计划

        Returns:
            评估结果（包含 score, mastery_level, suggested_next）
        """
        user_prompt = f"""评估以下回答的质量（0-1分）：

问题：{question}

回答：{answer}

返回 JSON 格式：
{{
  "score": 0.8,
  "mastery_level": "good/poor/medium",
  "suggested_next": "increase/maintain/decrease"
}}

只返回 JSON，不需要其他内容。
"""

        messages = [
            {
                "role": "system",
                "content": "你是一个教育评估专家，擅长评估学生的学习质量。",
            },
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = self.llm.invoke(messages).strip()

            # 尝试解析 JSON
            # 简化实现：使用规则提取
            return self._extract_evaluation(response)

        except Exception:
            # 降级：返回默认评估
            return {
                "score": 0.5,
                "mastery_level": "medium",
                "suggested_next": "maintain",
            }

    def _extract_evaluation(self, text: str) -> Dict[str, any]:
        """
        从文本中提取评估结果（简化版）

        Args:
            text: LLM 响应文本

        Returns:
            评估结果字典
        """
        # 简化实现：返回默认值
        # 在真实场景中，应该使用更健壮的 JSON 解析
        try:
            # 尝试直接解析
            return json.loads(text)
        except Exception:
            # 失败则返回默认值
            return {
                "score": 0.5,
                "mastery_level": "medium",
                "suggested_next": "maintain",
            }

    def _summarize_session(self, conversation: List[str], domain: str) -> str:
        """
        总结会话

        Args:
            conversation: 对话历史
            domain: 领域名称

        Returns:
            会话总结
        """
        content = "\n".join(conversation)

        user_prompt = f"""总结以下学习会话（控制在200字以内）：

{content[:3000]}

包括：
1. 讨论的主题
2. 用户掌握良好的知识点
3. 需要复习的内容
4. 下次学习的建议

输出格式：
## 会话总结

**讨论主题：** ...

**掌握情况：**
- ...

**需要复习：**
- ...

**下一步建议：**
- ...
"""

        messages = [
            {
                "role": "system",
                "content": "你是一个学习总结专家，擅长提炼关键信息。",
            },
            {"role": "user", "content": user_prompt},
        ]

        try:
            return self.llm.invoke(messages).strip()
        except Exception:
            return f"## 会话总结\n\n完成了 {domain} 领域的学习会话。\n继续加油！"
