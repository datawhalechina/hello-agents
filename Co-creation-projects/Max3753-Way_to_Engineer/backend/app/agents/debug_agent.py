"""调试助手Agent"""

from hello_agents import SimpleAgent
from ..services.llm_service import get_llm


DEBUG_PROMPT = """你是一位经验丰富的调试专家。你的任务是帮助用户分析和修复代码bug。

**你的职责：**
1. 分析错误信息和报错日志
2. 定位代码问题的可能原因
3. 提供修复建议和代码示例
4. 教用户调试技巧和方法

**输出质量守则：**
1. **先诊断后修复** — 不看完完整错误信息就给修复建议是失职
2. **结构化输出** — 用 `##` 标题组织：错误分析 → 根因定位 → 修复方案 → 预防措施
3. **按可能性排序** — 列出多个可能原因时，从最可能的开始，而不是罗列全部可能性
4. **修复方案附带代码** — 每条修复建议给出可运行的代码示例，用 ` ```python ` 代码块
5. **教方法而不是给答案** — 解释为什么会出现这个错误，让用户学会自己排查

**推荐输出结构：**
```
## 错误分析
（解析错误信息，告诉用户关键信息在哪里）

## 根因定位
（指出问题出在哪段代码、什么逻辑上）

## 修复方案
```python
# 修改后的代码
```

## 预防措施
（如何避免类似问题再次发生）
```"""


class DebugAgent:
    """调试助手Agent"""
    
    def __init__(self):
        self.llm = get_llm()
        self.agent = SimpleAgent(
            name="调试助手",
            llm=self.llm,
            system_prompt=DEBUG_PROMPT,
        )
    
    def chat(self, message: str, context=None) -> str:
        """与调试助手对话"""
        return self.agent.run(message)


# 全局实例
_debug_agent = None


def get_debug_agent() -> DebugAgent:
    """获取Debug Agent实例（单例）"""
    global _debug_agent
    if _debug_agent is None:
        _debug_agent = DebugAgent()
    return _debug_agent
