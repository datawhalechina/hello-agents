"""论文撰写助手协调器

五个专职 Agent：
  - PaperPlannerAgent      章节规划
  - LiteratureSearchAgent  学术检索 + PDF 下载 + RAG 索引
  - SectionWriterAgent     章节撰写（检索论文原文）
  - PaperReviewAgent       论文审校
  - ReportAssemblerAgent   最终论文汇总

"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

from hello_agents import HelloAgentsLLM, ToolAwareSimpleAgent
from hello_agents.tools import MemoryTool, NoteTool, ToolRegistry

from agents.literature_search import LiteratureSearchAgent
from config import Configuration
from models import PaperState, PaperStateOutput
from prompts import (
    paper_planner_system_prompt,
    paper_reviewer_system_prompt,
    report_assembler_system_prompt,
    section_writer_system_prompt,
)
from services.assembler import ReportAssemblyService
from services.planner import PlanningService
from services.reviewer import ReviewService
from services.tool_events import ToolCallTracker
from services.writer import SectionWritingService
from tools import PaperLibraryAskTool, PaperLibrarySearchTool

logger = logging.getLogger(__name__)


class PaperAssistantAgent:
    """论文撰写助手协调器"""

    def __init__(self, config: Optional[Configuration] = None) -> None:
        self.config = config or Configuration.from_env()
        self.llm = self._init_llm()

        # ---------- 内置工具 ----------
        self.note_tool = (
            NoteTool(workspace=self.config.notes_workspace)
            if self.config.enable_notes else None
        )
        self.memory_tool = (
            MemoryTool(user_id=self.config.memory_user_id)
            if self.config.enable_memory else None
        )

        # ---------- 工具调用追踪 ----------
        self._tool_tracker = ToolCallTracker(
            notes_workspace=self.config.notes_workspace
            if self.config.enable_notes else None
        )

        # ---------- 五个专职 Agent ----------
        self.planner_agent = self._make_agent(
            "论文规划专家", paper_planner_system_prompt.strip()
        )
        self.writer_agent = self._make_agent(
            "章节撰写专家", section_writer_system_prompt.strip()
        )
        self.reviewer_agent = self._make_agent(
            "论文审校专家", paper_reviewer_system_prompt.strip()
        )
        self.assembler_agent = self._make_agent(
            "报告汇总专家", report_assembler_system_prompt.strip()
        )

        # ---------- 文献检索 Agent ----------
        self.search_agent = LiteratureSearchAgent(
            llm=self.llm,
            config=self.config,
            tool_tracker=self._tool_tracker,
        )

        # ---------- 为写作 Agent 装配论文库检索工具（通过 add_tool） ----------
        self.writer_agent.add_tool(
            PaperLibrarySearchTool(self.search_agent.library)
        )
        self.writer_agent.add_tool(
            PaperLibraryAskTool(self.search_agent.library)
        )

        # ---------- 服务封装 ----------
        self.planner = PlanningService(self.planner_agent, self.config)
        self.writer = SectionWritingService(
            lambda: self.writer_agent, self.config
        )
        self.reviewer = ReviewService(
            lambda: self.reviewer_agent, self.config
        )
        self.assembler = ReportAssemblyService(
            lambda: self.assembler_agent, self.config
        )

    # ------------------------------------------------------------------
    def _init_llm(self) -> HelloAgentsLLM:
        """初始化 LLM 客户端

        直接交给 HelloAgentsLLM 的自动检测机制处理：
        - 参数优先，环境变量兜底；
        - 读取 LLM_PROVIDER / LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_ID，
          或 OPENAI_API_KEY / DEEPSEEK_API_KEY / DASHSCOPE_API_KEY 等；
        - 根据 base_url 或 api_key 格式自动识别 provider。

        应用层不感知 provider 细节，只设置业务相关参数（temperature=0.0）。
        """
        return HelloAgentsLLM(temperature=0.0)

    def _make_agent(self, name: str, system_prompt: str) -> ToolAwareSimpleAgent:
        """为每个 Agent 装配 NoteTool + MemoryTool（共享 registry）"""
        registry = ToolRegistry()
        if self.note_tool:
            registry.register_tool(self.note_tool)
        if self.memory_tool:
            registry.register_tool(self.memory_tool)

        return ToolAwareSimpleAgent(
            name=name,
            llm=self.llm,
            system_prompt=system_prompt,
            enable_tool_calling=True,
            tool_registry=registry,
            tool_call_listener=self._tool_tracker.record,
        )

    # ------------------------------------------------------------------
    def run(self, topic: str) -> PaperStateOutput:
        """执行完整论文撰写流程"""
        state = PaperState(
            research_topic=topic,
            paper_type=self._enum_value(self.config.paper_type),
            citation_style=self._enum_value(self.config.citation_style),
        )

        # 1) 记录研究主题到情景记忆
        if self.memory_tool:
            self.memory_tool.run({
                "action": "add",
                "content": f"开始撰写论文，研究主题：{topic}",
                "memory_type": "episodic",
                "importance": 0.9,
            })

        # 2) 章节规划
        logger.info("→ 规划章节大纲")
        sections = self.planner.plan_outline(state)
        if not sections:
            sections = PlanningService.create_fallback_sections()
        state.sections = sections
        self._drain_events()

        # 3) 逐章检索 + 撰写
        previous_context = ""
        for section in sections:
            logger.info("→ 章节 %d: %s", section.id, section.title)

            # 3.1 学术检索 + PDF 下载 + RAG 索引
            refs = self.search_agent.search_for_section(section)
            section.references = refs
            logger.info("   检索到 %d 篇，其中 %d 篇已下载索引",
                        len(refs), sum(1 for r in refs if r.get("indexed")))

            # 3.2 撰写章节（Writer Agent 可调用 search_paper_library 检索原文）
            content = self.writer.write_section(
                state, section, refs, previous_context
            )
            section.content = content
            section.status = "completed"
            previous_context += f"\n\n## {section.title}\n{content[:500]}"

            # 3.3 保存章节笔记（NoteTool）
            if self.note_tool:
                note_body = (
                    f"## 章节意图\n{section.intent}\n\n"
                    f"## 关键词\n{', '.join(section.keywords)}\n\n"
                    f"## 章节正文（节选）\n{content[:1500]}\n\n"
                    f"## 参考文献\n"
                    + "\n".join(
                        f"- {r.get('title', '')} "
                        f"{'[已索引]' if r.get('indexed') else ''}"
                        for r in refs
                    )
                )
                resp = self.note_tool.run({
                    "action": "create",
                    "title": f"章节 {section.id}: {section.title}",
                    "note_type": "conclusion",
                    "tags": ["paper", f"section_{section.id}"],
                    "content": note_body,
                })
                m = re.search(r"ID:\s*([^\n]+)", resp or "")
                if m:
                    section.note_id = m.group(1).strip()
                    if self.config.notes_workspace:
                        section.note_path = str(
                            Path(self.config.notes_workspace)
                            / f"{section.note_id}.md"
                        )

            self._drain_events()

            # 3.4 记录撰写事件到情景记忆
            if self.memory_tool:
                self.memory_tool.run({
                    "action": "add",
                    "content": f"完成章节「{section.title}」撰写",
                    "memory_type": "episodic",
                    "importance": 0.7,
                })

        # 4) 审校
        logger.info("→ 审校论文")
        full_draft = self._assemble_draft(state, sections)
        review_notes = self.reviewer.review(state, full_draft)
        state.review_notes = review_notes
        self._drain_events()

        # 5) 汇总
        logger.info("→ 汇总最终论文")
        final_paper = self.assembler.assemble(state, sections, review_notes)
        state.final_paper = final_paper
        self._drain_events()

        # 6) 保存终稿到笔记（NoteTool）
        if self.note_tool and final_paper:
            resp = self.note_tool.run({
                "action": "create",
                "title": f"论文终稿：{state.paper_title or topic}",
                "note_type": "conclusion",
                "tags": ["paper", "final"],
                "content": final_paper[:5000],
            })
            m = re.search(r"ID:\s*([^\n]+)", resp or "")
            if m:
                state.report_note_id = m.group(1).strip()
                if self.config.notes_workspace:
                    state.report_note_path = str(
                        Path(self.config.notes_workspace)
                        / f"{state.report_note_id}.md"
                    )

        # 7) 记录完成事件
        if self.memory_tool:
            total_refs = sum(len(s.references) for s in sections)
            indexed_refs = sum(
                1 for s in sections for r in s.references if r.get("indexed")
            )
            self.memory_tool.run({
                "action": "add",
                "content": (
                    f"论文《{state.paper_title or topic}》完成，"
                    f"共 {len(sections)} 章，"
                    f"{total_refs} 篇参考文献（{indexed_refs} 篇已索引）"
                ),
                "memory_type": "episodic",
                "importance": 0.9,
            })

        return PaperStateOutput(
            paper_markdown=final_paper,
            sections=sections,
            references=[r for s in sections for r in s.references],
            review_notes=review_notes,
            library_stats=self.search_agent.library_stats(),
        )

    # ------------------------------------------------------------------
    def _assemble_draft(self, state: PaperState, sections) -> str:
        parts = [f"# {state.paper_title or state.research_topic}\n"]
        for s in sections:
            parts.append(f"## {s.title}\n\n{s.content or ''}\n")
        return "\n".join(parts)

    def _drain_events(self) -> list[dict[str, Any]]:
        return self._tool_tracker.drain()

    @staticmethod
    def _enum_value(v: Any) -> str:
        return v.value if hasattr(v, "value") else str(v)