#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文档问答助手 - 基于HelloAgents的智能文档问答系统

这是一个完整的PDF学习助手应用，支持：
- 加载PDF文档并构建知识库
- 智能问答（基于RAG）
- 学习历程记录（基于Memory）
- 学习回顾和报告生成
"""

from dotenv import load_dotenv

load_dotenv()
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from hello_agents.tools import MemoryTool, RAGTool
from hello_agents.context.retrieval_router import RetrievalRouter
from hello_agents.memory import MemoryManager
import gradio as gr


class PDFLearningAssistant:
    """智能文档问答助手"""

    def __init__(self, user_id: str = "default_user"):
        """初始化学习助手

        Args:
            user_id: 用户ID，用于隔离不同用户的数据
        """
        self.user_id = user_id
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 初始化工具
        self.memory_tool = MemoryTool(user_id=user_id)
        self.rag_tool = RAGTool(rag_namespace=f"pdf_{user_id}")

        # 学习统计
        self.stats = {
            "session_start": datetime.now(),
            "documents_loaded": 0,
            "questions_asked": 0,
            "concepts_learned": 0,
        }

        # 当前加载的文档
        self.current_document = None

    def load_document(self, pdf_path: str) -> Dict[str, Any]:
        """加载PDF文档到知识库

        Args:
            pdf_path: PDF文件路径

        Returns:
            Dict: 包含success和message的结果
        """
        if not os.path.exists(pdf_path):
            return {"success": False, "message": f"文件不存在: {pdf_path}"}

        start_time = time.time()

        try:
            # 使用RAG工具处理PDF
            self.rag_tool.run(
                {
                    "action": "add_document",
                    "file_path": pdf_path,
                    "chunk_size": 1000,
                    "chunk_overlap": 200,
                }
            )

            process_time = time.time() - start_time

            # RAG工具返回的是字符串消息
            self.current_document = os.path.basename(pdf_path)
            self.stats["documents_loaded"] += 1

            # 记录到学习记忆
            self.memory_tool.run(
                {
                    "action": "add",
                    "content": f"加载了文档《{self.current_document}》",
                    "memory_type": "episodic",
                    "importance": 0.9,
                    "event_type": "document_loaded",
                    "session_id": self.session_id,
                }
            )

            return {
                "success": True,
                "message": f"加载成功！(耗时: {process_time:.1f}秒)",
                "document": self.current_document,
            }
        except Exception as e:
            return {"success": False, "message": f"加载失败: {str(e)}"}

    def ask(self, question: str, use_advanced_search: bool = True) -> str:
        """向文档提问

        Args:
            question: 用户问题
            use_advanced_search: 是否使用高级检索（MQE + HyDE）

        Returns:
            str: 答案
        """
        if not self.current_document:
            return "⚠️ 请先加载文档！使用 load_document() 方法加载PDF文档。"

        # 记录问题到工作记忆
        self.memory_tool.run(
            {
                "action": "add",
                "content": f"提问: {question}",
                "memory_type": "working",
                "importance": 0.6,
                "session_id": self.session_id,
            }
        )

        # 使用RAG检索答案
        answer = self.rag_tool.run(
            {
                "action": "ask",
                "question": question,
                "limit": 5,
                "enable_advanced_search": use_advanced_search,
                "enable_mqe": use_advanced_search,
                "enable_hyde": use_advanced_search,
            }
        )

        # 记录到情景记忆
        self.memory_tool.run(
            {
                "action": "add",
                "content": f"关于'{question}'的学习",
                "memory_type": "episodic",
                "importance": 0.7,
                "event_type": "qa_interaction",
                "session_id": self.session_id,
            }
        )

        self.stats["questions_asked"] += 1

        return answer

    def add_note(self, content: str, concept: Optional[str] = None):
        """添加学习笔记

        Args:
            content: 笔记内容
            concept: 相关概念（可选）
        """
        self.memory_tool.run(
            {
                "action": "add",
                "content": content,
                "memory_type": "semantic",
                "importance": 0.8,
                "concept": concept or "general",
                "session_id": self.session_id,
            }
        )

        self.stats["concepts_learned"] += 1

    def recall(self, query: str, limit: int = 5) -> str:
        """回顾学习历程

        Args:
            query: 查询关键词
            limit: 返回结果数量

        Returns:
            str: 相关记忆
        """
        result = self.memory_tool.run(
            {"action": "search", "query": query, "limit": limit}
        )
        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取学习统计

        Returns:
            Dict: 统计信息
        """
        duration = (datetime.now() - self.stats["session_start"]).total_seconds()

        return {
            "会话时长": f"{duration:.0f}秒",
            "加载文档": self.stats["documents_loaded"],
            "提问次数": self.stats["questions_asked"],
            "学习笔记": self.stats["concepts_learned"],
            "当前文档": self.current_document or "未加载",
        }

    def generate_report(self, save_to_file: bool = True) -> Dict[str, Any]:
        """生成学习报告

        Args:
            save_to_file: 是否保存到文件

        Returns:
            Dict: 学习报告
        """
        report_gen = SmartLearningReportGenerator(
            self.memory_tool, self.rag_tool, self.stats, self.session_id, self.user_id
        )
        return report_gen.generate(save_to_file)


class SmartLearningReportGenerator:
    """智能学习报告生成器

    分析用户的学习轨迹、识别知识盲点、推荐下一步学习内容。
    使用 EpisodicMemory 追踪学习历程，SemanticMemory 构建知识图谱，
    WorkingMemory 感知当前焦点，结合向量检索、图检索、模式发现、时间线分析等策略。
    """

    def __init__(
        self,
        memory_tool: MemoryTool,
        rag_tool: RAGTool,
        stats: Dict[str, Any],
        session_id: str,
        user_id: str,
    ):
        self.memory_tool = memory_tool
        self.rag_tool = rag_tool
        self.stats = stats
        self.session_id = session_id
        self.user_id = user_id
        self.router = RetrievalRouter()

        # 直接访问底层 MemoryManager 以使用高级检索
        self.memory_manager: MemoryManager = memory_tool.memory_manager

        self.start_time = stats.get("session_start", datetime.now())

    def generate(self, save_to_file: bool = True) -> Dict[str, Any]:
        duration = (datetime.now() - self.start_time).total_seconds()

        # 并行收集分析数据
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            ft_learning_trajectory = pool.submit(self._analyze_learning_trajectory)
            ft_knowledge_gaps = pool.submit(self._identify_knowledge_gaps)
            ft_recommendations = pool.submit(self._recommend_next_steps)
            ft_insights = pool.submit(self._generate_insights)

            learning_trajectory = ft_learning_trajectory.result()
            knowledge_gaps = ft_knowledge_gaps.result()
            recommendations = ft_recommendations.result()
            insights = ft_insights.result()

        # 基础统计
        base_stats = {
            "documents_loaded": self.stats.get("documents_loaded", 0),
            "questions_asked": self.stats.get("questions_asked", 0),
            "concepts_learned": self.stats.get("concepts_learned", 0),
            "current_document": self.stats.get("current_document", "未加载"),
        }

        report = {
            "session_info": {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "start_time": self.start_time.isoformat(),
                "duration_seconds": duration,
            },
            "learning_metrics": base_stats,
            "learning_trajectory": learning_trajectory,
            "knowledge_gaps": knowledge_gaps,
            "recommendations": recommendations,
            "insights": insights,
            "report_type": "smart",
        }

        if save_to_file:
            report_file = f"smart_learning_report_{self.session_id}.json"
            try:
                with open(report_file, "w", encoding="utf-8") as f:
                    json.dump(report, f, ensure_ascii=False, indent=2, default=str)
                report["report_file"] = report_file
            except Exception as e:
                report["save_error"] = str(e)

        return report

    def _analyze_learning_trajectory(self) -> Dict[str, Any]:
        """分析学习轨迹：使用 EpisodicMemory 的时间线和模式发现 + SemanticMemory 的实体知识"""
        trajectory = {"timeline": [], "topic_evolution": [], "session_summary": {}}

        # 1. 情景记忆时间线
        episodic = self.memory_manager.memory_types.get("episodic")
        if episodic:
            timeline = episodic.get_timeline(user_id=self.user_id, limit=50)
            trajectory["timeline"] = [
                {
                    "time": t["timestamp"],
                    "event": t["content"],
                    "type": t.get("session_id", ""),
                    "importance": t.get("importance", 0.5),
                }
                for t in timeline
            ]

            # 2. 模式发现：提取用户高频主题
            patterns = episodic.find_patterns(user_id=self.user_id, min_frequency=2)
            trajectory["topic_evolution"] = [
                {
                    "topic": p["pattern"],
                    "frequency": p["frequency"],
                    "confidence": p.get("confidence", 0),
                    "type": p.get("type", "keyword"),
                }
                for p in patterns[:20]
            ]

        # 3. 会话概要
        session_items = []
        for mt_name, mt_instance in self.memory_manager.memory_types.items():
            if hasattr(mt_instance, "retrieve"):
                items = mt_instance.retrieve(
                    query="", limit=5, user_id=self.user_id, session_id=self.session_id
                )
                session_items.extend(items)

        trajectory["session_summary"] = {
            "total_session_memories": len(session_items),
            "avg_importance": sum(m.importance for m in session_items)
            / len(session_items)
            if session_items
            else 0,
        }

        return trajectory

    def _identify_knowledge_gaps(self) -> List[Dict[str, Any]]:
        """识别知识盲点

        策略：
        1. 从 SemanticMemory 中提取用户已学概念（实体）
        2. 查询知识图谱中的关联概念（prerequisite / related）
        3. 对比发现：用户未学习但有关联的即为盲点
        4. 结合 RAG 检索文档中尚未被覆盖的概念
        """
        gaps = []

        semantic = self.memory_manager.memory_types.get("semantic")
        if not semantic:
            return gaps

        # 1. 获取用户已学的所有实体
        user_entities = {}
        if hasattr(semantic, "entities"):
            user_entities = {
                eid: e
                for eid, e in semantic.entities.items()
                if hasattr(e, "properties")
                and e.properties.get("user_id", self.user_id) == self.user_id
            }

        if not user_entities:
            # 回退：从记忆检索中提取
            all_semantic = semantic.retrieve(query="", limit=100, user_id=self.user_id)
            for mem in all_semantic:
                ent_name = (
                    mem.content.split(":")[0].strip()
                    if ":" in mem.content
                    else mem.content[:20]
                )
                if ent_name not in user_entities:
                    user_entities[ent_name] = ent_name

        if not user_entities:
            return gaps

        # 2. 对每个已学实体，查询图谱找到关联但未学的实体
        known_names = set()
        for eid, e in user_entities.items():
            name = getattr(e, "name", None) or getattr(e, "entity_id", str(e))
            known_names.add(name.lower())

        for eid, entity in user_entities.items():
            e_name = (
                getattr(entity, "name", None)
                or getattr(entity, "entity_id", str(eid))
                or str(eid)
            )
            related = []
            if hasattr(semantic, "get_related_entities"):
                try:
                    related = semantic.get_related_entities(entity_id=eid, max_hops=1)
                except Exception:
                    pass

            for rel in related:
                rel_entity = rel.get("entity")
                if not rel_entity:
                    continue
                rel_name = getattr(rel_entity, "name", None) or getattr(
                    rel_entity, "entity_id", ""
                )
                if not rel_name:
                    continue
                if rel_name.lower() not in known_names:
                    gaps.append(
                        {
                            "missing_concept": rel_name,
                            "related_to": e_name,
                            "relation_type": rel.get("relation_type", "related"),
                            "gap_score": 1.0 / (1.0 + len(gaps) * 0.1),
                        }
                    )
                    known_names.add(rel_name.lower())

        # 3. 回退：若图谱无结果，用检索路由做语义发现
        if not gaps:
            for known in list(known_names)[:5]:
                self.router.route(f"什么是{known}的相关概念？")
                gaps.append(
                    {
                        "missing_concept": f"{known}的进阶知识",
                        "related_to": known,
                        "relation_type": "advanced",
                        "gap_score": 0.5,
                    }
                )

        gaps.sort(key=lambda x: x["gap_score"], reverse=True)
        return gaps[:10]

    def _recommend_next_steps(self) -> List[Dict[str, Any]]:
        """推荐下一步学习内容

        策略：
        1. 基于知识盲点推荐（权重高）
        2. 基于学习轨迹中高频主题的进阶（权重中）
        3. 基于文档中提问较少的概念（权重中）
        """
        recommendations = []

        # 1. 从知识盲点生成推荐
        gaps = self._identify_knowledge_gaps()
        for gap in gaps[:5]:
            recommendations.append(
                {
                    "content": f"学习「{gap['missing_concept']}」— 与已学的「{gap['related_to']}」密切相关",
                    "type": "knowledge_gap",
                    "priority": "high" if gap["gap_score"] > 0.6 else "medium",
                    "score": gap["gap_score"],
                    "reason": f"你对「{gap['related_to']}」已有了解，但尚未探索关联概念「{gap['missing_concept']}」",
                }
            )

        # 2. 基于学习轨迹中的高频主题推荐进阶
        episodic = self.memory_manager.memory_types.get("episodic")
        if episodic:
            patterns = episodic.find_patterns(user_id=self.user_id, min_frequency=1)
            top_topics = [
                p["pattern"] for p in patterns[:5] if p.get("frequency", 0) >= 1
            ]
            for topic in top_topics:
                if not any(topic in r.get("content", "") for r in recommendations):
                    recommendations.append(
                        {
                            "content": f"深入探索「{topic}」的进阶内容",
                            "type": "deepen_topic",
                            "priority": "medium",
                            "score": 0.5,
                            "reason": f"你多次接触「{topic}」相关内容，建议深入学习",
                        }
                    )

        # 3. 基于当前文档推荐未被充分提问的概念
        self.rag_tool.run({"action": "stats"})
        doc_info = self.stats.get("current_document", "")
        if doc_info:
            recommendations.append(
                {
                    "content": f"尝试对文档「{doc_info}」中的更多概念进行提问",
                    "type": "explore_document",
                    "priority": "low",
                    "score": 0.3,
                    "reason": "深入阅读当前文档能帮助建立更完整的知识体系",
                }
            )

        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:8]

    def _generate_insights(self) -> Dict[str, Any]:
        """生成学习洞察：综合分析"""
        duration_hours = (datetime.now() - self.start_time).total_seconds() / 3600.0
        q_count = self.stats.get("questions_asked", 0)
        n_count = self.stats.get("concepts_learned", 0)
        d_count = self.stats.get("documents_loaded", 0)

        # 计算学习效率
        questions_per_doc = q_count / max(d_count, 1)
        notes_per_hour = n_count / max(duration_hours, 0.01)

        memory_stats = self.memory_manager.get_memory_stats()
        total_memories = memory_stats.get("total_memories", 0)

        # 基于统计数据给出状态评估
        if q_count > 10 and n_count > 5:
            engagement = "highly_engaged"
            engagement_label = "学习投入度高"
        elif q_count > 3:
            engagement = "moderately_engaged"
            engagement_label = "学习投入度中等"
        else:
            engagement = "low_engagement"
            engagement_label = "学习投入度较低，建议多提问"

        insights = {
            "engagement_level": engagement,
            "engagement_label": engagement_label,
            "learning_efficiency": {
                "questions_per_document": round(questions_per_doc, 1),
                "notes_per_hour": round(notes_per_hour, 1),
                "total_memories_created": total_memories,
            },
            "coverage_assessment": {
                "documents_loaded": d_count,
                "concepts_documented": n_count,
                "interaction_depth": "deep" if questions_per_doc > 3 else "shallow",
            },
            "suggestions": [],
        }

        if questions_per_doc < 2:
            insights["suggestions"].append("对每篇文档多提几个问题以加深理解")
        if n_count < 3:
            insights["suggestions"].append("多记录学习笔记，有助于知识沉淀")
        if duration_hours < 0.5:
            insights["suggestions"].append(
                "建议延长单次学习时长，以获得更连贯的学习体验"
            )

        return insights


def create_gradio_ui():
    """创建Gradio Web UI"""
    # 全局助手实例
    assistant_state = {"assistant": None}

    def init_assistant(user_id: str) -> str:
        """初始化助手"""
        if not user_id:
            user_id = "web_user"
        assistant_state["assistant"] = PDFLearningAssistant(user_id=user_id)
        return f"✅ 助手已初始化 (用户: {user_id})"

    def load_pdf(pdf_file) -> str:
        """加载PDF文件"""
        if assistant_state["assistant"] is None:
            return "❌ 请先初始化助手"

        if pdf_file is None:
            return "❌ 请上传PDF文件"

        # Gradio上传的文件是临时文件对象
        pdf_path = pdf_file.name
        result = assistant_state["assistant"].load_document(pdf_path)

        if result["success"]:
            return f"✅ {result['message']}\n📄 文档: {result['document']}"
        else:
            return f"❌ {result['message']}"

    def chat(message: str, history: List) -> Tuple[str, List]:
        """聊天功能"""
        if assistant_state["assistant"] is None:
            return "", history + [[message, "❌ 请先初始化助手并加载文档"]]

        if not message.strip():
            return "", history

        # 判断是技术问题还是回顾问题
        if any(
            keyword in message for keyword in ["之前", "学过", "回顾", "历史", "记得"]
        ):
            # 回顾学习历程
            response = assistant_state["assistant"].recall(message)
            response = f"🧠 **学习回顾**\n\n{response}"
        else:
            # 技术问答
            response = assistant_state["assistant"].ask(message)
            response = f"💡 **回答**\n\n{response}"

        history.append([message, response])
        return "", history

    def add_note_ui(note_content: str, concept: str) -> str:
        """添加笔记"""
        if assistant_state["assistant"] is None:
            return "❌ 请先初始化助手"

        if not note_content.strip():
            return "❌ 笔记内容不能为空"

        assistant_state["assistant"].add_note(note_content, concept or None)
        return f"✅ 笔记已保存: {note_content[:50]}..."

    def get_stats_ui() -> str:
        """获取统计信息"""
        if assistant_state["assistant"] is None:
            return "❌ 请先初始化助手"

        stats = assistant_state["assistant"].get_stats()
        result = "📊 **学习统计**\n\n"
        for key, value in stats.items():
            result += f"- **{key}**: {value}\n"
        return result

    def generate_report_ui() -> str:
        """生成报告"""
        if assistant_state["assistant"] is None:
            return "❌ 请先初始化助手"

        report = assistant_state["assistant"].generate_report(save_to_file=True)

        result = []
        result.append("# 🧠 智能学习报告\n")

        # 基本信息
        result.append("## 📊 学习统计")
        result.append(f"- 会话时长: {report['session_info']['duration_seconds']:.0f}秒")
        result.append(f"- 加载文档: {report['learning_metrics']['documents_loaded']}")
        result.append(f"- 提问次数: {report['learning_metrics']['questions_asked']}")
        result.append(f"- 学习笔记: {report['learning_metrics']['concepts_learned']}\n")

        # 学习轨迹
        trajectory = report.get("learning_trajectory", {})
        if trajectory.get("topic_evolution"):
            result.append("## 📈 学习轨迹 (高频主题)")
            for topic in trajectory["topic_evolution"][:8]:
                bar = "█" * int(topic["frequency"] * 3)
                result.append(f"- **{topic['topic']}**: {bar} (x{topic['frequency']})")
            result.append("")

        # 知识盲点
        gaps = report.get("knowledge_gaps", [])
        if gaps:
            result.append("## 🔍 知识盲点识别")
            for gap in gaps[:5]:
                score_bar = "●" * int(gap["gap_score"] * 5) + "○" * (
                    5 - int(gap["gap_score"] * 5)
                )
                result.append(
                    f"- **{gap['missing_concept']}** (与{gap['related_to']}相关) [{score_bar}]"
                )
            result.append("")

        # 学习推荐
        recs = report.get("recommendations", [])
        if recs:
            result.append("## 🎯 下一步学习推荐")
            for rec in recs[:5]:
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    rec["priority"], "⚪"
                )
                result.append(f"- {priority_icon} **{rec['content']}**")
                result.append(f"  - 原因: {rec['reason']}")
            result.append("")

        # 学习洞察
        insights = report.get("insights", {})
        if insights:
            result.append("## 💡 学习洞察")
            result.append(f"- 学习状态: **{insights.get('engagement_label', '未知')}**")
            eff = insights.get("learning_efficiency", {})
            result.append(f"- 每文档提问数: {eff.get('questions_per_document', 0)}")
            result.append(f"- 每小时笔记数: {eff.get('notes_per_hour', 0)}")
            result.append(f"- 记忆总数: {eff.get('total_memories_created', 0)}")
            if insights.get("suggestions"):
                result.append("\n**改进建议:**")
                for s in insights["suggestions"]:
                    result.append(f"- 💬 {s}")
            result.append("")

        if "report_file" in report:
            result.append(f"\n💾 完整报告已保存至: `{report['report_file']}`")

        return "\n".join(result)

    # 创建Gradio界面
    with gr.Blocks(title="智能文档问答助手") as demo:
        gr.Markdown("""
        # 📚 智能文档问答助手

        基于HelloAgents的智能文档问答系统，支持：
        - 📄 加载PDF文档并构建知识库
        - 💬 智能问答（基于RAG）
        - 📝 学习笔记记录
        - 🧠 学习历程回顾
        - 📊 学习报告生成
        """)

        with gr.Tab("🏠 开始使用"):
            with gr.Row():
                user_id_input = gr.Textbox(
                    label="用户ID",
                    placeholder="输入你的用户ID（可选，默认为web_user）",
                    value="web_user",
                )
                init_btn = gr.Button("初始化助手", variant="primary")

            init_output = gr.Textbox(label="初始化状态", interactive=False)
            init_btn.click(
                init_assistant, inputs=[user_id_input], outputs=[init_output]
            )

            gr.Markdown("### 📄 加载PDF文档")
            pdf_upload = gr.File(
                label="上传PDF文件", file_types=[".pdf"], type="filepath"
            )
            load_btn = gr.Button("加载文档", variant="primary")
            load_output = gr.Textbox(label="加载状态", interactive=False)
            load_btn.click(load_pdf, inputs=[pdf_upload], outputs=[load_output])

        with gr.Tab("💬 智能问答"):
            gr.Markdown("### 向文档提问或回顾学习历程")
            chatbot = gr.Chatbot(
                label="对话历史", height=400, layout="bubble", type="messages"
            )
            with gr.Row():
                msg_input = gr.Textbox(
                    label="输入问题",
                    placeholder="例如：什么是Transformer？ 或 我之前学过什么？",
                    scale=4,
                )
                send_btn = gr.Button("发送", variant="primary", scale=1)

            gr.Examples(
                examples=[
                    "什么是大语言模型？",
                    "Transformer架构有哪些核心组件？",
                    "如何训练大语言模型？",
                    "我之前学过什么内容？",
                    "回顾一下关于注意力机制的学习",
                ],
                inputs=msg_input,
            )

            msg_input.submit(
                chat, inputs=[msg_input, chatbot], outputs=[msg_input, chatbot]
            )
            send_btn.click(
                chat, inputs=[msg_input, chatbot], outputs=[msg_input, chatbot]
            )

        with gr.Tab("📝 学习笔记"):
            gr.Markdown("### 记录学习心得和重要概念")
            note_content = gr.Textbox(
                label="笔记内容", placeholder="输入你的学习笔记...", lines=3
            )
            concept_input = gr.Textbox(
                label="相关概念（可选）", placeholder="例如：transformer, attention"
            )
            note_btn = gr.Button("保存笔记", variant="primary")
            note_output = gr.Textbox(label="保存状态", interactive=False)
            note_btn.click(
                add_note_ui, inputs=[note_content, concept_input], outputs=[note_output]
            )

        with gr.Tab("📊 学习统计"):
            gr.Markdown("### 查看学习进度和统计信息")
            stats_btn = gr.Button("刷新统计", variant="primary")
            stats_output = gr.Markdown()
            stats_btn.click(get_stats_ui, outputs=[stats_output])

            gr.Markdown("### 生成学习报告")
            report_btn = gr.Button("生成报告", variant="primary")
            report_output = gr.Textbox(label="报告状态", interactive=False)
            report_btn.click(generate_report_ui, outputs=[report_output])

    return demo


def main():
    """主函数 - 启动Gradio Web UI"""
    print("\n" + "=" * 60)
    print("智能文档问答助手")
    print("=" * 60)
    print("正在启动Web界面...\n")

    demo = create_gradio_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7862,
        share=False,
        show_error=True,
        prevent_thread_lock=False,
    )


if __name__ == "__main__":
    main()
