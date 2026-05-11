# agent.py
# SmartResearchAgent - 智能研究助手
# 基于HelloAgents框架构建，整合搜索、摘要、报告生成能力

from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from typing import Optional, Iterator
from .tools import WebSearchTool, TextSummarizerTool, ReportGeneratorTool


class SmartResearchAgent:
    """
    智能研究助手 - 一个多智能体研究系统
    
    整合了三个核心能力：
    1. 网络搜索 - 从互联网获取最新信息
    2. 文本摘要 - 提取关键信息和要点
    3. 报告生成 - 整理为结构化的研究报告
    
    使用HelloAgents框架的SimpleAgent作为核心，
    通过工具调用实现自动化研究流程。
    """

    def __init__(
        self,
        llm: Optional[HelloAgentsLLM] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        初始化智能研究助手
        
        Args:
            llm: LLM实例，如果不提供则使用默认配置
            system_prompt: 自定义系统提示词
        """
        # 初始化LLM
        self.llm = llm or HelloAgentsLLM()
        
        # 创建工具注册表
        self.tool_registry = ToolRegistry()
        
        # 注册工具
        self.web_search_tool = WebSearchTool()
        self.summarizer_tool = TextSummarizerTool()
        self.report_tool = ReportGeneratorTool()
        
        self.tool_registry.register_tool(self.web_search_tool)
        self.tool_registry.register_tool(self.summarizer_tool)
        self.tool_registry.register_tool(self.report_tool)
        
        # 系统提示词
        default_prompt = """你是一个专业的智能研究助手。你的任务是帮助用户进行深度研究。

你拥有以下工具：
1. web_search - 搜索互联网获取最新信息
2. text_summarizer - 将长文本压缩为摘要
3. report_generator - 生成结构化的研究报告

当需要使用工具时，请使用以下格式：
[TOOL_CALL:工具名:参数]

例如：
- 搜索：[TOOL_CALL:web_search:人工智能最新进展]
- 摘要：[TOOL_CALL:text_summarizer:这里是要摘要的文本]
- 生成报告：[TOOL_CALL:report_generator:主题|发现内容|来源]

你的工作流程：
1. 理解用户的研究需求
2. 使用搜索工具收集相关信息
3. 对收集的信息进行分析和摘要
4. 生成结构化的研究报告
5. 回答用户的后续问题

请始终保持客观、准确，引用可靠的来源。"""
        
        self.system_prompt = system_prompt or default_prompt
        
        # 创建核心Agent
        self.agent = SimpleAgent(
            name="SmartResearchAgent",
            llm=self.llm,
            system_prompt=self.system_prompt,
            tool_registry=self.tool_registry,
            enable_tool_calling=True
        )
        
        # 研究状态
        self.research_topic = None
        self.research_findings = []
        self.research_sources = []
        
        print("🔬 SmartResearchAgent 初始化完成")
        print(f"   可用工具: web_search, text_summarizer, report_generator")

    def research(self, topic: str, max_searches: int = 3) -> str:
        """
        执行完整的研究流程
        
        Args:
            topic: 研究主题
            max_searches: 最大搜索次数
            
        Returns:
            研究报告内容
        """
        print(f"\n{'='*60}")
        print(f"🔬 开始研究：{topic}")
        print(f"{'='*60}\n")
        
        self.research_topic = topic
        self.research_findings = []
        self.research_sources = []
        
        # 步骤1：搜索收集信息
        print("📡 步骤1：搜索收集信息...")
        search_queries = self._generate_search_queries(topic)
        
        for i, query in enumerate(search_queries[:max_searches], 1):
            print(f"   搜索 {i}/{max_searches}: {query}")
            result = self.web_search_tool.run({"query": query, "max_results": 3})
            self.research_findings.append(result)
        
        # 步骤2：分析和摘要
        print("\n📊 步骤2：分析和摘要...")
        all_findings = "\n\n".join(self.research_findings)
        summary = self.summarizer_tool.run({
            "text": all_findings,
            "max_points": 5
        })
        print(f"   {summary}")
        
        # 步骤3：生成报告
        print("\n📝 步骤3：生成研究报告...")
        sources_list = "\n".join([f"- 来源{i+1}" for i in range(len(self.research_findings))])
        report = self.report_tool.run({
            "topic": topic,
            "findings": summary,
            "sources": sources_list
        })
        
        print(f"\n{'='*60}")
        print("✅ 研究完成！")
        print(f"{'='*60}\n")
        
        return report

    def ask(self, question: str) -> str:
        """
        基于研究结果回答问题
        
        Args:
            question: 用户的问题
            
        Returns:
            回答内容
        """
        if not self.research_topic:
            return "请先使用 research() 方法进行研究，然后再提问。"
        
        # 构建包含研究背景的问题
        context = f"基于之前对 '{self.research_topic}' 的研究，"
        full_question = f"{context}{question}"
        
        print(f"\n💬 回答问题：{question}")
        response = self.agent.run(full_question)
        return response

    def quick_search(self, query: str) -> str:
        """
        快速搜索，不进入完整研究流程
        
        Args:
            query: 搜索关键词
            
        Returns:
            搜索结果
        """
        print(f"🔍 快速搜索：{query}")
        return self.web_search_tool.run({"query": query, "max_results": 5})

    def summarize(self, text: str) -> str:
        """
        对文本进行摘要
        
        Args:
            text: 需要摘要的文本
            
        Returns:
            摘要内容
        """
        print("📊 生成摘要...")
        return self.summarizer_tool.run({"text": text, "max_points": 5})

    def _generate_search_queries(self, topic: str) -> list:
        """根据主题生成多个搜索关键词"""
        queries = [
            topic,
            f"{topic} 最新进展 2025",
            f"{topic} 研究综述",
            f"{topic} 应用案例",
            f"{topic} 技术原理",
        ]
        return queries

    def get_research_summary(self) -> str:
        """获取当前研究的摘要信息"""
        if not self.research_topic:
            return "尚未进行研究"
        
        return f"""
研究主题：{self.research_topic}
搜索次数：{len(self.research_findings)}
收集资料：{len(self.research_findings)} 份
研究状态：已完成
"""
