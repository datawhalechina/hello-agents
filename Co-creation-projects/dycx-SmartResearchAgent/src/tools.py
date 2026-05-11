# tools.py
# 自定义工具集：网络搜索、文本摘要、报告生成

from hello_agents.tools import Tool, ToolParameter
from typing import Dict, Any, List
import json


class WebSearchTool(Tool):
    """网络搜索工具 - 使用DuckDuckGo搜索互联网信息"""

    def __init__(self):
        super().__init__(
            name="web_search",
            description="搜索互联网获取最新信息。输入搜索关键词，返回相关网页标题、摘要和链接。"
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        """执行网络搜索"""
        query = parameters.get("query", "")
        max_results = parameters.get("max_results", 5)

        if not query:
            return "错误：搜索关键词不能为空"

        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", "")
                    })

            if not results:
                return f"未找到关于 '{query}' 的相关结果"

            # 格式化输出
            output = f"搜索 '{query}' 找到 {len(results)} 条结果：\n\n"
            for i, r in enumerate(results, 1):
                output += f"**{i}. {r['title']}**\n"
                output += f"   {r['snippet']}\n"
                output += f"   链接：{r['url']}\n\n"

            return output

        except ImportError:
            return "错误：请安装 duckduckgo-search 包 (pip install duckduckgo-search)"
        except Exception as e:
            return f"搜索失败：{str(e)}"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="搜索关键词",
                required=True
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description="最大返回结果数（默认5）",
                required=False
            )
        ]


class TextSummarizerTool(Tool):
    """文本摘要工具 - 将长文本压缩为关键要点"""

    def __init__(self):
        super().__init__(
            name="text_summarizer",
            description="将长文本压缩为简洁的摘要，提取关键信息和要点。"
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        """生成文本摘要"""
        text = parameters.get("text", "")
        max_points = parameters.get("max_points", 5)

        if not text:
            return "错误：文本内容不能为空"

        # 简单的提取式摘要（基于句子重要性评分）
        sentences = text.replace("\n", " ").split("。")
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if not sentences:
            return "文本内容过短，无法生成摘要"

        # 基于关键词权重的简单评分
        important_keywords = ["重要", "关键", "核心", "主要", "发现", "表明",
                            "研究", "结果", "结论", "创新", "突破", "首次",
                            "important", "key", "main", "result", "conclusion",
                            "study", "research", "finding", "breakthrough"]

        scored_sentences = []
        for sentence in sentences:
            score = sum(1 for kw in important_keywords if kw in sentence.lower())
            # 较短的句子通常更核心
            length_bonus = max(0, 1 - len(sentence) / 200)
            score += length_bonus
            scored_sentences.append((score, sentence))

        # 取得分最高的句子
        scored_sentences.sort(reverse=True)
        top_sentences = [s[1] for s in scored_sentences[:max_points]]

        summary = "摘要要点：\n"
        for i, point in enumerate(top_sentences, 1):
            summary += f"{i}. {point}。\n"

        return summary

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="text",
                type="string",
                description="需要摘要的文本内容",
                required=True
            ),
            ToolParameter(
                name="max_points",
                type="integer",
                description="摘要要点数量（默认5）",
                required=False
            )
        ]


class ReportGeneratorTool(Tool):
    """报告生成工具 - 将研究结果整理为结构化Markdown报告"""

    def __init__(self):
        super().__init__(
            name="report_generator",
            description="将研究资料整理为结构化的Markdown研究报告。输入研究主题和收集到的资料，输出完整报告。"
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        """生成研究报告"""
        topic = parameters.get("topic", "")
        findings = parameters.get("findings", "")
        sources = parameters.get("sources", "")

        if not topic:
            return "错误：研究主题不能为空"

        if not findings:
            return "错误：研究发现内容不能为空"

        # 生成结构化报告
        report = f"""# 研究报告：{topic}

## 1. 研究概述

本报告围绕 **{topic}** 进行了系统性的信息收集与分析，旨在梳理该领域的核心概念、最新进展和关键发现。

## 2. 核心发现

{findings}

## 3. 关键要点总结

基于以上研究资料，提炼出以下关键要点：

- 该领域正在快速发展，新的技术和方法不断涌现
- 多学科交叉融合是当前研究的重要趋势
- 实际应用落地仍面临诸多挑战

## 4. 参考来源

{sources if sources else "（来源信息未提供）"}

## 5. 结论与展望

**{topic}** 是一个充满活力的研究领域。随着技术的不断进步和应用场景的拓展，预计未来将有更多突破性进展。

---

*报告生成时间：由SmartResearchAgent自动生成*
*基于HelloAgents框架构建*
"""
        return report

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="topic",
                type="string",
                description="研究主题",
                required=True
            ),
            ToolParameter(
                name="findings",
                type="string",
                description="研究发现和资料内容",
                required=True
            ),
            ToolParameter(
                name="sources",
                type="string",
                description="参考来源列表",
                required=False
            )
        ]
