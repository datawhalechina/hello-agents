# -*- coding: utf-8 -*-
"""VulnAuditAgent - 智能代码漏洞审计助手
规则引擎 + 污点追踪 + LLM 研判 三通道协同审计
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from hello_agents import HelloAgentsLLM, ToolRegistry
from fixed_agent import FixedSimpleAgent as SimpleAgent
from audit_tools import RuleEngineTool, TaintTrackTool, LLMVerifyTool

SYSTEM_PROMPT = """你是一名资深安全代码审计员，工作流为三通道协同。

【最重要的规则】
- 需要调用工具时，直接输出工具调用标记，不要输出任何解释、预告或客套话
- 禁止输出"我将...""首先我会..."这类开场白，直接行动

【第一步】调用 rule_scan 对源码做规则引擎扫描（危险函数/硬编码密钥/弱加密）
【第二步】调用 taint_track 做污点追踪（外部输入->危险函数的数据流链路）
【第三步】对规则扫描中 严重/高危 的每一条，调用 llm_verify 研判真伪
【第四步】汇总输出 Markdown 格式的审计报告

报告格式：
# 代码审计报告
## 概览
| 项目 | 值 |
表格：文件、扫描规则命中数、污点链路数、研判后确认漏洞数
## 漏洞详情
每条漏洞：
### [序号] 漏洞类型（文件名:行号）
- 风险等级:
- 研判结论: 真阳性/误报/存疑
- 代码片段:
- 风险说明:
- 修复建议:
## 总结
一段话总结整体安全状况和最优先修复项。

注意：文件名只写相对文件名（如 vulnerable_sample.py），不要写完整路径。"""


def main():
    llm = HelloAgentsLLM(temperature=1.0, max_tokens=8192)
    registry = ToolRegistry()
    registry.register_tool(RuleEngineTool())
    registry.register_tool(TaintTrackTool())
    registry.register_tool(LLMVerifyTool(llm))

    agent = SimpleAgent(
        name="漏洞审计员",
        llm=llm,
        system_prompt=SYSTEM_PROMPT,
        tool_registry=registry,
        enable_tool_calling=True,
    )

    prompt = (
        "请审计项目中的 data/vulnerable_sample.py 文件。"
        "严格按照工作流执行，第一条回复就必须是工具调用标记，禁止任何开场白或解释：\n"
        "1. 调用工具 rule_scan，参数 file_path=data/vulnerable_sample.py\n"
        "2. 调用工具 taint_track，参数 file_path=data/vulnerable_sample.py\n"
        "3. 对规则扫描中 严重/高危 的每一条，调用 llm_verify 研判（传入 finding_type、code_snippet、line_number）\n"
        "4. 汇总输出完整 Markdown 审计报告\n"
    )
    print("开始审计，Agent 工作中（规则扫描→污点追踪→LLM研判→写报告，约1-3分钟）...")

    report = ""
    for attempt in range(3):
        report = agent.run(prompt, max_tool_iterations=15)
        if "# 代码审计报告" in report and "漏洞详情" in report and len(report) > 2000:
            break
        print(f"[重试] 第{attempt + 1}次输出不完整，换个方式再问一次...")
        prompt = "你刚才没有按流程执行工具调用。现在请立即执行：调用 rule_scan，参数 file_path=data/vulnerable_sample.py。直接输出工具调用标记，不要任何解释。"

    out_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "audit_report.md")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report)
    print()
    print(report)
    print()
    print("审计完成，报告已保存: outputs/audit_report.md")


if __name__ == "__main__":
    main()
