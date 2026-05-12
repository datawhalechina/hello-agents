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
from memory_tool import MemoryTool
from rag_tool import RAGTool
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
            "concepts_learned": 0
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
            result = self.rag_tool.run({
                "action":"add_document",
                "file_path":pdf_path,
                "chunk_size":1000,
                "chunk_overlap":200
            })

            process_time = time.time() - start_time

            # RAG工具返回的是字符串消息
            self.current_document = os.path.basename(pdf_path)
            self.stats["documents_loaded"] += 1

            # 记录到学习记忆
            self.memory_tool.run({
                "action":"add",
                "content":f"加载了文档《{self.current_document}》",
                "memory_type":"episodic",
                "importance":0.9,
                "event_type":"document_loaded",
                "session_id":self.session_id
            })

            return {
                "success": True,
                "message": f"加载成功！(耗时: {process_time:.1f}秒)",
                "document": self.current_document
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"加载失败: {str(e)}"
            }

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
        self.memory_tool.run({
            "action":"add",
            "content":f"提问: {question}",
            "memory_type":"working",
            "importance":0.6,
            "session_id":self.session_id
        })

        # 使用RAG检索答案
        answer = self.rag_tool.run({
            "action":"ask",
            "question":question,
            "limit":5,
            "enable_advanced_search":use_advanced_search,
            "enable_mqe":use_advanced_search,
            "enable_hyde":use_advanced_search
        })

        # 记录到情景记忆
        self.memory_tool.run({
            "action":"add",
            "content":f"关于'{question}'的学习",
            "memory_type":"episodic",
            "importance":0.7,
            "event_type":"qa_interaction",
            "session_id":self.session_id
        })

        self.stats["questions_asked"] += 1

        return answer

    def add_note(self, content: str, concept: Optional[str] = None):
        """添加学习笔记

        Args:
            content: 笔记内容
            concept: 相关概念（可选）
        """
        self.memory_tool.run({
            "action":"add",
            "content":content,
            "memory_type":"semantic",
            "importance":0.8,
            "concept":concept or "general",
            "session_id":self.session_id
        })

        self.stats["concepts_learned"] += 1

    def recall(self, query: str, limit: int = 5) -> str:
        """回顾学习历程

        Args:
            query: 查询关键词
            limit: 返回结果数量

        Returns:
            str: 相关记忆
        """
        result = self.memory_tool.run({
            "action":"search",
            "query":query,
            "limit":limit
        })
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
            "当前文档": self.current_document or "未加载"
        }

    def generate_report(self, save_to_file: bool = True) -> Dict[str, Any]:
        """生成学习报告

        Args:
            save_to_file: 是否保存到文件

        Returns:
            Dict: 学习报告
        """
        # 获取记忆摘要
        memory_summary = self.memory_tool.run({"action":"summary", "limit":10})

        # 获取RAG统计
        rag_stats = self.rag_tool.run({"action":"stats"})

        # 生成报告
        duration = (datetime.now() - self.stats["session_start"]).total_seconds()
        report = {
            "session_info": {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "start_time": self.stats["session_start"].isoformat(),
                "duration_seconds": duration
            },
            "learning_metrics": {
                "documents_loaded": self.stats["documents_loaded"],
                "questions_asked": self.stats["questions_asked"],
                "concepts_learned": self.stats["concepts_learned"]
            },
            "memory_summary": memory_summary,
            "rag_status": rag_stats
        }

        # 保存到文件
        if save_to_file:
            report_file = f"learning_report_{self.session_id}.json"
            try:
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=2, default=str)
                report["report_file"] = report_file
            except Exception as e:
                report["save_error"] = str(e)

        return report





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
        if any(keyword in message for keyword in ["之前", "学过", "回顾", "历史", "记得"]):
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

        result = f"✅ 学习报告已生成\n\n"
        result += f"**会话信息**\n"
        result += f"- 会话时长: {report['session_info']['duration_seconds']:.0f}秒\n"
        result += f"- 加载文档: {report['learning_metrics']['documents_loaded']}\n"
        result += f"- 提问次数: {report['learning_metrics']['questions_asked']}\n"
        result += f"- 学习笔记: {report['learning_metrics']['concepts_learned']}\n"

        if "report_file" in report:
            result += f"\n💾 报告已保存至: {report['report_file']}"

        return result

    # 创建Gradio界面
    with gr.Blocks(title="智能文档问答助手", theme=gr.themes.Soft()) as demo:
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
                    value="web_user"
                )
                init_btn = gr.Button("初始化助手", variant="primary")

            init_output = gr.Textbox(label="初始化状态", interactive=False)
            init_btn.click(init_assistant, inputs=[user_id_input], outputs=[init_output])

            gr.Markdown("### 📄 加载PDF文档")
            pdf_upload = gr.File(
                label="上传PDF文件",
                file_types=[".pdf"],
                type="filepath"
            )
            load_btn = gr.Button("加载文档", variant="primary")
            load_output = gr.Textbox(label="加载状态", interactive=False)
            load_btn.click(load_pdf, inputs=[pdf_upload], outputs=[load_output])

        with gr.Tab("💬 智能问答"):
            gr.Markdown("### 向文档提问或回顾学习历程")
            chatbot = gr.Chatbot(
                label="对话历史",
                height=400,
                bubble_full_width=False
            )
            with gr.Row():
                msg_input = gr.Textbox(
                    label="输入问题",
                    placeholder="例如：什么是Transformer？ 或 我之前学过什么？",
                    scale=4
                )
                send_btn = gr.Button("发送", variant="primary", scale=1)

            gr.Examples(
                examples=[
                    "什么是大语言模型？",
                    "Transformer架构有哪些核心组件？",
                    "如何训练大语言模型？",
                    "我之前学过什么内容？",
                    "回顾一下关于注意力机制的学习"
                ],
                inputs=msg_input
            )

            msg_input.submit(chat, inputs=[msg_input, chatbot], outputs=[msg_input, chatbot])
            send_btn.click(chat, inputs=[msg_input, chatbot], outputs=[msg_input, chatbot])

        with gr.Tab("📝 学习笔记"):
            gr.Markdown("### 记录学习心得和重要概念")
            note_content = gr.Textbox(
                label="笔记内容",
                placeholder="输入你的学习笔记...",
                lines=3
            )
            concept_input = gr.Textbox(
                label="相关概念（可选）",
                placeholder="例如：transformer, attention"
            )
            note_btn = gr.Button("保存笔记", variant="primary")
            note_output = gr.Textbox(label="保存状态", interactive=False)
            note_btn.click(add_note_ui, inputs=[note_content, concept_input], outputs=[note_output])

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
    print("\n" + "="*60)
    print("智能文档问答助手")
    print("="*60)
    print("正在启动Web界面...\n")

    demo = create_gradio_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )


if __name__ == "__main__":
    main()

