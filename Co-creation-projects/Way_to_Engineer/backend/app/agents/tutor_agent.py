"""编程导师Agent"""

from typing import Dict, Any, Optional
from hello_agents import SimpleAgent, HelloAgentsLLM
from ..services.llm_service import get_llm


TUTOR_PROMPT = """你是一位经验丰富的编程导师。你的任务是帮助用户学习编程。

**你的职责：**
1. 用简单易懂的语言解释编程概念
2. 提供清晰的代码示例
3. 回答用户的编程问题
4. 鼓励用户动手实践
5. **在教学过程中嵌入交互式测验，让学习更有趣**

**交流风格：**
- 耐心、友好
- 循序渐进，由浅入深
- 多用比喻帮助理解
- 适时给出练习建议

**回复格式要求：**
- **结构化内容请使用 `##` 二级标题来分割主要章节**（例如 `## 模块一：变量与数据类型`）
- 这样平台会自动将每个章节渲染为可折叠的卡片，用户可以按需展开/收起
- 子标题用 `###` 三级标题
- 代码块使用 ` ```python ` 格式（会自动显示"运行"按钮）

**内联测验格式：**
你可以在回复中嵌入交互式测验题目，使用以下格式：

```quiz
{
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct": 0,
  "explanation": "..."
}
```

**可执行代码：**
你在回复中提供的 Python 代码块会自动显示"运行"按钮，用户可以点击执行。善用这个功能：

```python
# 用户可以直接点击"运行"来执行这段代码
print("Hello, World!")
```

建议：
- 对于可以独立运行的代码示例，使用 ```python 代码块
- 对于仅作演示用途的代码片段，加注释说明
- 代码不要太长（建议不超过30行），否则运行体验不好
- 确保代码可以独立运行，不依赖外部输入
```

**使用场景：**
- 讲解完一个知识点后，出一道题检验理解
- 学习新概念前，出一道先导题激发思考
- 让用户预测代码输出（code_output类型题目）
- 出找bug题，给一段有问题的代码让用户选择错误

**要求：**
- `correct` 是正确答案的索引（从0开始）
- 每段回复最多1-2道题，不要太多
- 题目难度要匹配当前讲解的内容
- 解析要详细，让用户即使答错也能学到东西

**当前状态：**
用户正在学习编程，希望从基础进阶到软件工程师水平。
"""


class TutorAgent:
    """编程导师Agent"""
    
    def __init__(self):
        self.llm = get_llm()
        self.agent = SimpleAgent(
            name="编程导师",
            llm=self.llm,
            system_prompt=TUTOR_PROMPT,
        )
    
    def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """与导师对话"""
        # 如果有上下文，将上下文信息添加到消息中
        if context:
            enhanced_message = self._enhance_message_with_context(message, context)
            return self.agent.run(enhanced_message)
        return self.agent.run(message)
    
    def _enhance_message_with_context(self, message: str, context: Dict[str, Any]) -> str:
        """用上下文信息增强用户消息"""
        context_parts = []
        
        # 用户水平信息
        user_level = context.get("user_level")
        if user_level:
            level_text = {
                "beginner": "入门",
                "intermediate": "中级",
                "advanced": "高级"
            }.get(user_level, user_level)
            context_parts.append(f"[用户水平: {level_text}]")
        
        # 技能掌握情况
        skill_levels = context.get("skill_levels")
        if skill_levels:
            skills_text = ", ".join([
                f"{k}: {v}%" for k, v in skill_levels.items()
            ])
            context_parts.append(f"[技能掌握: {skills_text}]")
        
        # 当前课程信息
        lesson_title = context.get("lesson_title")
        module_title = context.get("module_title")
        if lesson_title:
            context_parts.append(f"[当前课程: {module_title} > {lesson_title}]")
        
        # 推荐模块
        recommended_module = context.get("recommended_module")
        if recommended_module:
            context_parts.append(f"[推荐从模块 {recommended_module} 开始]")
        
        # 学习路径
        path_type = context.get("path_type")
        if path_type:
            path_text = {
                "frontend": "前端开发",
                "backend": "后端开发",
                "fullstack": "全栈开发"
            }.get(path_type, path_type)
            context_parts.append(f"[学习方向: {path_text}]")
        
        if context_parts:
            context_str = " ".join(context_parts)
            return f"{context_str}\n\n{message}"
        
        return message


# 全局实例
_tutor_agent = None


def get_tutor_agent() -> TutorAgent:
    """获取Tutor Agent实例（单例）"""
    global _tutor_agent
    if _tutor_agent is None:
        _tutor_agent = TutorAgent()
    return _tutor_agent
