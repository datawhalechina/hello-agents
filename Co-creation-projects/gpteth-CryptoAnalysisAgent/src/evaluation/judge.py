"""
LLM-as-Judge 评审

规则检查覆盖不了语义层面的质量 (矛盾信号是否被如实标注、
建议是否真的可执行)，由评审 Agent 按固定量表打分。

用法:
    judge = create_judge_agent(llm)
    scores = run_judge(judge, report)
"""

import json
import re
from typing import Any, Dict, Optional

from hello_agents import SimpleAgent, HelloAgentsLLM


JUDGE_PROMPT = """你是一位严格的加密货币分析报告评审员。你将收到一份综合分析报告，请按以下五个维度独立打分 (1-5 分，5 为最佳):

1. signal_consistency (矛盾信号处理): 不同维度结论冲突时，报告是否如实标注矛盾，而不是强行抹平或只呈现单边观点
2. conditionality (建议条件化): 建议是否针对不同情况的用户给出条件化方案，而非绝对预测
3. risk_awareness (风险意识): 是否先讲风险再讲机会，风险提示是否具体可操作
4. fact_judgment_separation (事实与判断分离): 是否区分了数据事实和主观推断
5. actionability (可执行性): 建议是否具体到价位/仓位/触发条件，用户能否直接参考执行

## 输出格式

只输出一个 JSON 对象，不要输出其他内容:

```json
{
  "signal_consistency": <1-5>,
  "conditionality": <1-5>,
  "risk_awareness": <1-5>,
  "fact_judgment_separation": <1-5>,
  "actionability": <1-5>,
  "overall": <五项平均分，保留一位小数>,
  "comments": "<不超过100字的总评，指出最主要的问题>"
}
```

## 评审原则

- 严格但公平: 缺失的维度直接给低分，做到的维度不吝啬给高分
- 只评审报告本身，不评判市场观点的对错
- 发现编造数据的迹象 (如报告中出现明显凭空捏造的精确数字) 时在 comments 中指出
"""


def create_judge_agent(llm: HelloAgentsLLM = None) -> SimpleAgent:
    """创建评审 Agent (无工具，纯打分)"""
    if llm is None:
        llm = HelloAgentsLLM()
    return SimpleAgent(
        name="报告评审员",
        llm=llm,
        system_prompt=JUDGE_PROMPT,
    )


def parse_judge_output(raw: str) -> Optional[Dict[str, Any]]:
    """从评审输出中提取 JSON 评分，解析失败返回 None"""
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def run_judge(judge: SimpleAgent, report: str) -> Dict[str, Any]:
    """评审一份报告，返回评分字典 (含原始输出，便于排查解析失败)"""
    raw = judge.run(f"请评审以下报告:\n\n{report}")
    scores = parse_judge_output(raw)
    return {"scores": scores, "raw": raw, "parse_ok": scores is not None}
