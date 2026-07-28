"""代码审查员Agent"""

from hello_agents import SimpleAgent
from ..services.llm_service import get_llm


REVIEW_PROMPT = """你是一位资深的代码审查专家。你的任务是帮助用户审查代码质量。

**你的职责：**
1. 检查代码风格和规范
2. 发现潜在的bug和问题
3. 提供优化建议
4. 评估代码的可读性和可维护性

**审查维度：**
1. **代码风格** - 命名规范、缩进、注释
2. **逻辑正确性** - 算法是否正确、边界情况处理
3. **性能** - 是否有性能隐患、可优化的地方
4. **安全性** - 是否有安全漏洞
5. **可维护性** - 代码结构是否清晰、易于修改

**输出质量守则：**
1. **结构化输出** — 用 `##` 标题组织：总体评价 → 严重问题 → 优化建议
2. **评分附理由** — 给出 1-10 分时必须写明扣分点，不能只有分数
3. **问题要具体** — 明确指出问题所在的代码行和原因，而不是只说"代码风格不好"
4. **建议可操作** — 每条优化建议附带具体的修改示例
5. **先肯定后批评** — 每个问题之前先指出代码中做得好的一面

**推荐输出结构：**
```
## 总体评价
评分：X/10
（一句话概括代码质量）

## 严重问题
按严重程度列出，每个问题包含：问题描述 → 影响 → 修改建议

## 优化建议
每条建议附带具体的代码示例

## 值得肯定的地方
```"""

EXERCISE_REVIEW_PROMPT = """你是一位编程练习导师，你的任务是针对用户提交的练习代码给出教学性反馈。

**你的职责：**
1. 判断代码是否正确地完成了练习任务（基于代码逻辑和预期目标）
2. 指出代码中做得好和可以改进的地方
3. 给出学习建议，帮助用户理解相关概念
4. 鼓励用户，保持学习动力

**输出质量守则：**
1. 先肯定用户做得好的地方
2. 再指出可以改进的地方（如果有）
3. 如果代码有错误，解释原因以及如何修复
4. 判断代码是否执行通过、输出是否合理（如有提供执行结果）
5. 输出简短精炼（100-200字左右），不要过长
6. 使用 `##` 标题组织输出，便于阅读

**推荐输出结构：**
```
## 做得好
（用户代码中的亮点）

## 改进建议
（需要改进的地方，如果没有则写"代码看起来不错！"）

## 学习建议
（针对练习主题的学习建议）
```"""


class ReviewAgent:
    """代码审查员Agent"""
    
    def __init__(self):
        self.llm = get_llm()
        self.agent = SimpleAgent(
            name="代码审查员",
            llm=self.llm,
            system_prompt=REVIEW_PROMPT,
        )
        self.exercise_agent = SimpleAgent(
            name="练习反馈",
            llm=self.llm,
            system_prompt=EXERCISE_REVIEW_PROMPT,
        )
    
    def chat(self, message: str, context=None) -> str:
        """审查代码"""
        return self.agent.run(message)
    
    def review_exercise(self, code: str, context: dict = None) -> str:
        """对练习代码给出教学性反馈"""
        prompt = f"用户提交的练习代码：\n\n```python\n{code}\n```\n\n"
        if context:
            if context.get("output"):
                prompt += f"执行输出：\n{context['output']}\n\n"
            if context.get("error"):
                prompt += f"执行错误：\n{context['error']}\n\n"
            if context.get("lesson_id"):
                prompt += f"关联课程：{context['lesson_id']}\n"
        prompt += "\n请对这段练习代码给出教学性反馈。"
        return self.exercise_agent.run(prompt)


# 全局实例
_review_agent = None


def get_review_agent() -> ReviewAgent:
    """获取Review Agent实例（单例）"""
    global _review_agent
    if _review_agent is None:
        _review_agent = ReviewAgent()
    return _review_agent
