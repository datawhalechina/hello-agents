"""
PaperAssistant - 智能论文助手 Gradio Web 界面

提供文献检索、论文总结、引用生成、论文润色、大纲生成、PDF 提取等功能。
所有操作自动记录到对话历史，可回溯查看。
"""
import os
import sys
import json
from datetime import datetime
import gradio as gr

from dotenv import load_dotenv
load_dotenv()

# Windows UTF-8 兼容
sys.stdout.reconfigure(encoding='utf-8')

from hello_agents import (
    HelloAgentsLLM, SimpleAgent, ToolRegistry, Config
)
from src.arxiv_tool import ArxivSearchTool
from src.pdf_tool import PDFExtractTool
from src.citation_tool import CitationTool
from src.literature_tool import LiteratureSearchTool
from src.pubmed_tool import PubMedSearchTool
from src.crossref_tool import CrossRefSearchTool
from src.openalex_tool import OpenAlexSearchTool
from src.aminer_tool import AminerSearchTool


# ========================================
# 对话日志系统
# ========================================
HISTORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "conversations")

class ConversationLogger:
    """对话日志管理器：记录、持久化、检索所有交互"""

    def __init__(self, save_dir=HISTORY_DIR):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        self.records = self._load_all()

    def _filepath(self):
        """当前会话的日志文件"""
        today = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.save_dir, f"session_{today}.json")

    def _load_all(self):
        """加载所有历史记录"""
        records = []
        if os.path.exists(self.save_dir):
            for fname in sorted(os.listdir(self.save_dir), reverse=True):
                if fname.endswith(".json"):
                    fpath = os.path.join(self.save_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            records.extend(json.load(f))
                    except Exception:
                        pass
        return records

    def add(self, tab, action, user_input, output):
        """添加一条对话记录并持久化"""
        record = {
            "id": len(self.records) + 1,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tab": tab,
            "action": action,
            "user_input": user_input[:200] + ("..." if len(user_input) > 200 else ""),
            "output_preview": output[:200] + ("..." if len(output) > 200 else ""),
            "output_full": output
        }
        self.records.insert(0, record)  # 最新的在前

        # 追加到今日文件
        today_file = self._filepath()
        try:
            existing = []
            if os.path.exists(today_file):
                with open(today_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing.insert(0, record)
            with open(today_file, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return record

    def format_history_html(self):
        """格式化为 HTML 展示，每条记录带独立删除按钮"""
        if not self.records:
            return "<p><i>暂无对话记录，开始使用后会自动保存。</i></p>"

        lines = [f'<p style="color:#888;">共 {len(self.records)} 条记录</p>']
        for r in self.records[:50]:
            escaped_output = (r['output_full']
                             .replace("&", "&amp;")
                             .replace("<", "&lt;")
                             .replace(">", "&gt;")
                             .replace("\n", "<br>")
                             .replace("`", "&#96;"))
            rid = r["id"]
            lines.append(f'''
<div style="border:1px solid #e0e0e0; border-radius:8px; padding:12px; margin:10px 0; position:relative;">
  <div style="position:absolute; top:8px; right:8px;">
    <button onclick="document.getElementById('del_trigger').querySelector('textarea,input').value='{rid}';
                     document.getElementById('del_trigger').querySelector('textarea,input').dispatchEvent(new Event('input',{{bubbles:true}}));
                     document.getElementById('del_trigger').querySelector('textarea,input').dispatchEvent(new Event('change',{{bubbles:true}}));"
            style="background:#e74c3c; color:#fff; border:none; border-radius:4px; cursor:pointer; padding:4px 12px; font-size:12px;">
      ✕ 删除
    </button>
  </div>
  <div style="margin-right:70px;">
    <strong>[#{r['id']}] {r['timestamp']}</strong>
    <span style="color:#666;"> | {r['tab']} | {r['action']}</span>
    <p style="margin:6px 0 2px 0; color:#555; font-size:13px;"><b>输入:</b> {r['user_input']}</p>
    <details style="margin-top:6px;">
      <summary style="cursor:pointer; color:#2980b9;">查看完整输出</summary>
      <div style="background:#f8f9fa; padding:10px; border-radius:4px; margin-top:4px; max-height:300px; overflow-y:auto; font-size:13px; white-space:pre-wrap;">{escaped_output}</div>
    </details>
  </div>
</div>''')
        return "\n".join(lines)

    def delete_record(self, record_id: int) -> str:
        """删除单条记录"""
        for i, r in enumerate(self.records):
            if r.get("id") == record_id:
                del self.records[i]
                # 重新持久化当天文件
                today_file = self._filepath()
                try:
                    with open(today_file, "w", encoding="utf-8") as f:
                        json.dump(self.records, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                return f"已删除记录 #{record_id}"
        return f"未找到记录 #{record_id}"

    def clear(self):
        """清空记录"""
        self.records = []
        for fname in os.listdir(self.save_dir):
            if fname.endswith(".json"):
                os.remove(os.path.join(self.save_dir, fname))
        return "对话记录已清空。"


# 全局日志实例
logger = ConversationLogger()


# ========================================
# 会话管理器（润色 & 大纲的对话历史）
# ========================================
class ChatSessionManager:
    """管理润色和大纲的多轮对话会话"""

    def __init__(self, save_dir: str):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)

    def _filepath(self, session_id: str) -> str:
        return os.path.join(self.save_dir, f"{session_id}.json")

    def save(self, session_id: str, messages: list, title: str = ""):
        """保存会话"""
        data = {
            "id": session_id,
            "title": title or f"会话 {session_id[:8]}",
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messages": messages
        }
        with open(self._filepath(session_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, session_id: str) -> list:
        """加载会话，返回 messages 列表"""
        with open(self._filepath(session_id), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("messages", [])

    def list_sessions(self):
        """列出所有会话 [(id, title, updated), ...]"""
        sessions = []
        if os.path.exists(self.save_dir):
            for fname in sorted(os.listdir(self.save_dir), reverse=True):
                if fname.endswith(".json"):
                    try:
                        with open(os.path.join(self.save_dir, fname), "r", encoding="utf-8") as f:
                            data = json.load(f)
                        sessions.append((
                            data.get("id", fname[:-5]),
                            data.get("title", fname[:-5]),
                            data.get("updated", "")
                        ))
                    except Exception:
                        pass
        return sessions

    def delete(self, session_id: str):
        """删除会话"""
        path = self._filepath(session_id)
        if os.path.exists(path):
            os.remove(path)


# 为润色和大纲各创建一个会话管理器
polish_sessions = ChatSessionManager(os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "polish_sessions"))
outline_sessions = ChatSessionManager(os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "outline_sessions"))
paper_sessions = ChatSessionManager(os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "paper_sessions"))


# ========================================
# 初始化：LLM + 工具 + 智能体
# ========================================
config = Config(trace_enabled=False)
llm = HelloAgentsLLM()

tool_registry = ToolRegistry()
tool_registry.register_tool(LiteratureSearchTool())
tool_registry.register_tool(ArxivSearchTool())
tool_registry.register_tool(PubMedSearchTool())
tool_registry.register_tool(CrossRefSearchTool())
tool_registry.register_tool(OpenAlexSearchTool())
tool_registry.register_tool(AminerSearchTool())
tool_registry.register_tool(PDFExtractTool())
tool_registry.register_tool(CitationTool())

# ---- 文献检索智能体 ----
search_agent = SimpleAgent(
    name="文献检索助手", llm=llm, config=config,
    system_prompt="""你是一位学术文献检索专家。你有 6 个检索工具可用，请严格按用户指定的工具名称调用：

- literature_search: Semantic Scholar，全学科覆盖（推荐）
- aminer_search: AMiner，中文学术论文
- openalex_search: OpenAlex，开放获取论文
- pubmed_search: PubMed，生物医学领域
- crossref_search: CrossRef，期刊论文元数据
- arxiv_search: arXiv，CS/数学/物理预印本

规则：
1. 必须使用用户指定的工具搜索论文，不要用其他工具替代
2. 基于工具返回的真实结果进行分析和推荐
3. 绝对禁止在工具调用失败时凭空编造论文信息
4. 如果工具返回错误，直接向用户报告错误"""
)
# 注册全部 5 个检索工具
search_agent.add_tool(tool_registry.get_tool("literature_search"))
search_agent.add_tool(tool_registry.get_tool("openalex_search"))
search_agent.add_tool(tool_registry.get_tool("pubmed_search"))
search_agent.add_tool(tool_registry.get_tool("crossref_search"))
search_agent.add_tool(tool_registry.get_tool("arxiv_search"))
search_agent.add_tool(tool_registry.get_tool("aminer_search"))

# ---- 论文总结智能体 ----
summary_agent = SimpleAgent(
    name="论文总结助手", llm=llm, config=config,
    system_prompt="""你是一位学术论文审稿专家。请按以下结构生成总结报告：

## 论文信息
## 研究问题
## 方法与创新点
## 贡献与局限
## 启发与延伸

请使用中文输出报告，专业术语保留英文。"""
)

# ---- 对话智能体工厂（每次新对话创建独立实例，保持上下文记忆） ----

def create_polish_agent():
    """创建论文润色对话智能体"""
    return SimpleAgent(
        name="论文润色助手", llm=llm, config=config,
        system_prompt="""你是资深学术论文语言编辑。以对话方式帮助用户润色论文。

润色原则：
1. 保持原意不变，仅优化表达
2. 改善句式结构，消除冗余
3. 确保逻辑连贯，统一术语
4. 对修改处简要说明原因

对话方式：用户可能多次提出修改要求（如"更正式一些"、"缩短第三段"），
你需要记住之前的内容和修改历史，在此基础上继续优化。"""
    )

def create_outline_agent():
    """创建论文大纲对话智能体"""
    return SimpleAgent(
        name="大纲生成助手", llm=llm, config=config,
        system_prompt="""你是经验丰富的学术导师。以对话方式帮助用户构建论文大纲。

你需要：
1. 根据主题拆解核心章节和子主题
2. 为每个章节规划核心内容要点
3. 推荐研究方法和参考文献方向

对话方式：用户可能多次要求调整（如"在第三章加入实验对比"、"细化文献综述部分"），
你需要记住已生成的大纲内容，在此基础上修改，而不是每次重新开始。"""
    )

def create_paper_writer_agent():
    """创建论文写作对话智能体（带文献检索能力）"""
    agent = SimpleAgent(
        name="论文写作助手", llm=llm, config=config,
        system_prompt="""你是一位学术论文写作专家。你有 6 个文献检索工具可用：

- literature_search: Semantic Scholar，全学科文献检索（推荐优先使用）
- aminer_search: AMiner，中文学术论文
- openalex_search: OpenAlex，开放获取论文
- pubmed_search: PubMed，生物医学文献
- crossref_search: CrossRef，期刊论文
- arxiv_search: arXiv，预印本

写作规则（必须严格遵守）：
1. 根据用户提供的大纲，逐章节撰写论文
2. 学术化语言风格，逻辑严谨，段落清晰
3. **引用文献时，必须先使用检索工具搜索真实论文，只引用工具返回的真实文献**
4. 每引用一篇论文，必须在参考文献处标注真实信息（作者、标题、年份、期刊）
5. **绝对禁止**编造不存在的论文标题、作者或期刊名
6. 如果工具检索失败，明确告知用户"该领域文献检索失败，建议稍后重试"，而不是编造文献"""
    )
    # 注册全部检索工具，确保文献来源真实
    for name in ["literature_search", "openalex_search", "pubmed_search",
                 "crossref_search", "arxiv_search", "aminer_search"]:
        agent.add_tool(tool_registry.get_tool(name))
    return agent


# ========================================
# Gradio 回调函数（所有操作自动记录日志）
# ========================================

def search_papers(query, source, max_results, field, year_from, year_to):
    """文献检索 — 支持 5 大数据源"""
    if not query.strip():
        return "请输入搜索关键词。"

    # 数据源 → 工具名映射
    SOURCE_MAP = {
        "Semantic Scholar": "literature_search",
        "AMiner": "aminer_search",
        "OpenAlex": "openalex_search",
        "PubMed": "pubmed_search",
        "CrossRef": "crossref_search",
        "arXiv": "arxiv_search",
    }
    tool_name = next((v for k, v in SOURCE_MAP.items() if source.startswith(k)), "literature_search")
    source_name = next((k for k in SOURCE_MAP if source.startswith(k)), "Semantic Scholar")

    # 构建参数（高级筛选仅 Semantic Scholar 和 OpenAlex 支持）
    params_str = f"max_results={int(max_results)}"
    supports_advanced = source_name in ("Semantic Scholar", "OpenAlex", "PubMed", "CrossRef")
    if supports_advanced and field and field != "全部领域":
        params_str += f", field='{field}'"
    if supports_advanced and year_from and year_from.strip():
        params_str += f", year_from='{year_from.strip()}'"
    if supports_advanced and year_to and year_to.strip():
        params_str += f", year_to='{year_to.strip()}'"

    try:
        result = search_agent.run(
            f"请使用 {tool_name} 工具搜索以下主题的论文，然后分析结果：{query}\n"
            f"参数设置: {params_str}"
        )
        logger.add("文献检索", f"{source_name} 论文搜索", query, result)
        return result
    except Exception as e:
        err = f"检索出错: {str(e)}"
        logger.add("文献检索", f"{source_name} 搜索失败", query, err)
        return err


def summarize_paper(content):
    """论文总结"""
    if not content.strip():
        return "请输入论文内容。"
    try:
        result = summary_agent.run(f"请对以下论文内容进行结构化总结：\n\n{content}")
        logger.add("论文总结", "结构化总结", content, result)
        return result
    except Exception as e:
        err = f"总结出错: {str(e)}"
        logger.add("论文总结", "总结失败", content, err)
        return err


def generate_citation(title, authors, journal, year, volume, pages, doi, fmt):
    """引用生成"""
    if not title.strip() or not authors.strip():
        return "请至少填写论文标题和作者。"
    user_input = f"{title} | {authors} | {journal} | {year} | 格式: {fmt}"
    try:
        params = {
            "title": title, "authors": authors,
            "journal": journal, "year": year,
            "volume": volume, "pages": pages, "doi": doi,
            "format": fmt
        }
        resp = tool_registry.execute_tool("citation_generator", json.dumps(params))
        logger.add("引用生成", f"{fmt} 格式引用", user_input, resp.text)
        return resp.text
    except Exception as e:
        err = f"生成出错: {str(e)}"
        logger.add("引用生成", "生成失败", user_input, err)
        return err


def polish_chat(message, history, session_id):
    """论文润色对话 — 多轮交互，自动保存会话"""
    if not message.strip():
        return "", history, session_id, _polish_sessions_dropdown()

    # 新会话自动生成 ID
    if not session_id:
        session_id = f"polish_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        context = ""
        for msg in history:
            role = "用户" if msg["role"] == "user" else "助手"
            context += f"{role}: {msg['content']}\n"
        context += f"用户: {message}\n助手: "

        agent = create_polish_agent()
        result = agent.run(context)
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": result})

        # 自动保存（用第一条用户消息做标题）
        title = history[0]["content"][:50] if history else "新对话"
        polish_sessions.save(session_id, history, title)
        logger.add("论文润色（对话）", "多轮润色", message, result)
        return "", history, session_id, _polish_sessions_dropdown()
    except Exception as e:
        err = f"润色出错: {str(e)}"
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": err})
        return "", history, session_id, _polish_sessions_dropdown()




def outline_chat(message, history, session_id):
    """大纲生成对话 — 多轮交互，自动保存会话"""
    if not message.strip():
        return "", history, session_id, _outline_sessions_dropdown()
    if not session_id:
        session_id = f"outline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        context = ""
        for msg in history:
            role = "用户" if msg["role"] == "user" else "助手"
            context += f"{role}: {msg['content']}\n"
        context += f"用户: {message}\n助手: "
        agent = create_outline_agent()
        result = agent.run(context)
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": result})
        title = history[0]["content"][:50] if history else "新对话"
        outline_sessions.save(session_id, history, title)
        logger.add("大纲生成（对话）", "多轮大纲调整", message, result)
        return "", history, session_id, _outline_sessions_dropdown()
    except Exception as e:
        err = f"生成出错: {str(e)}"
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": err})
        return "", history, session_id, _outline_sessions_dropdown()


def _polish_choices():
    sessions = polish_sessions.list_sessions()
    return [(f"{t} ({u})", sid) for sid, t, u in sessions]

def _outline_choices():
    sessions = outline_sessions.list_sessions()
    return [(f"{t} ({u})", sid) for sid, t, u in sessions]

def _paper_choices():
    sessions = paper_sessions.list_sessions()
    return [(f"{t} ({u})", sid) for sid, t, u in sessions]

def _polish_sessions_dropdown():
    """润色会话列表 → gr.update"""
    choices = _polish_choices()
    return gr.update(choices=choices, value=None if not choices else choices[0][1])

def _outline_sessions_dropdown():
    """大纲会话列表 → gr.update"""
    choices = _outline_choices()
    return gr.update(choices=choices, value=None if not choices else choices[0][1])

def _paper_sessions_dropdown():
    """论文写作会话列表 → gr.update"""
    choices = _paper_choices()
    return gr.update(choices=choices, value=None if not choices else choices[0][1])

def clear_polish_chat():
    """重置润色对话"""
    return "", [], "", _polish_sessions_dropdown()


def clear_outline_chat():
    """重置大纲对话"""
    return "", [], "", _outline_sessions_dropdown()


def load_polish_session(session_id):
    """加载润色历史会话到 chatbot"""
    if not session_id:
        return [], session_id, _polish_sessions_dropdown()
    try:
        messages = polish_sessions.load(session_id)
        return messages, session_id, _polish_sessions_dropdown()
    except Exception:
        return [], "", _polish_sessions_dropdown()


def load_outline_session(session_id):
    """加载大纲历史会话到 chatbot"""
    if not session_id:
        return [], session_id, _outline_sessions_dropdown()
    try:
        messages = outline_sessions.load(session_id)
        return messages, session_id, _outline_sessions_dropdown()
    except Exception:
        return [], "", _outline_sessions_dropdown()

def delete_polish_session(session_id):
    """删除润色历史会话"""
    if session_id:
        polish_sessions.delete(session_id)
    return [], "", _polish_sessions_dropdown()

def delete_outline_session(session_id):
    """删除大纲历史会话"""
    if session_id:
        outline_sessions.delete(session_id)
    return [], "", _outline_sessions_dropdown()


# ========================================
# 论文写作回调（对话模式 + DOCX 下载）

def paper_write_chat(message, history, session_id):
    """论文写作对话 — 多轮交互，自动保存"""
    if not message.strip():
        return "", history, session_id, _paper_sessions_dropdown()
    if not session_id:
        session_id = f"paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        context = ""
        for msg in history:
            role = "用户" if msg["role"] == "user" else "助手"
            context += f"{role}: {msg['content']}\n"
        context += f"用户: {message}\n助手: "
        agent = create_paper_writer_agent()
        result = agent.run(context)
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": result})
        title = history[0]["content"][:50] if history else "新对话"
        paper_sessions.save(session_id, history, title)
        logger.add("论文写作（对话）", "多轮写作", message, result)
        return "", history, session_id, _paper_sessions_dropdown()
    except Exception as e:
        err = f"写作出错: {str(e)}"
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": err})
        return "", history, session_id, _paper_sessions_dropdown()

def load_paper_session(session_id):
    """加载论文写作历史会话"""
    if not session_id:
        return [], session_id, _paper_sessions_dropdown()
    try:
        messages = paper_sessions.load(session_id)
        return messages, session_id, _paper_sessions_dropdown()
    except Exception:
        return [], "", _paper_sessions_dropdown()

def delete_paper_session(session_id):
    """删除论文写作历史会话"""
    if session_id:
        paper_sessions.delete(session_id)
    return [], "", _paper_sessions_dropdown()

def clear_paper_chat():
    """重置论文写作对话"""
    return "", [], "", _paper_sessions_dropdown()

def extract_pdf(pdf_file, max_chars):
    """PDF 文本提取"""
    if pdf_file is None:
        return "请上传一个 PDF 文件。"
    try:
        resp = tool_registry.execute_tool("pdf_extract", json.dumps({
            "file_path": pdf_file.name,
            "max_chars": int(max_chars)
        }))
        logger.add("PDF 提取", "PDF 文本提取", f"文件: {pdf_file.name}", resp.text)
        return resp.text
    except Exception as e:
        err = f"提取出错: {str(e)}"
        logger.add("PDF 提取", "提取失败", f"文件: {pdf_file.name}", err)
        return err


def refresh_history():
    """刷新对话记录显示"""
    return logger.format_history_html()


def delete_history_record(record_id):
    """删除指定编号的记录（由 HTML 按钮触发）"""
    if not record_id:
        return logger.format_history_html()
    try:
        rid = int(record_id)
        logger.delete_record(rid)
        return logger.format_history_html()
    except (ValueError, TypeError):
        return logger.format_history_html()


def clear_history():
    """清空对话记录"""
    msg = logger.clear()
    return msg


# ========================================
# Gradio UI 布局
# ========================================

THEME = gr.themes.Soft(primary_hue="blue", secondary_hue="slate")

with gr.Blocks(title="PaperAssistant - 智能论文助手") as demo:
    gr.Markdown("""
    # 🎓 PaperAssistant - 智能论文助手
    ### 基于 HelloAgents 框架 + DeepSeek 的多智能体论文学术辅助工具
    """)

    with gr.Tab("📚 文献检索"):
        with gr.Row():
            with gr.Column(scale=3):
                search_input = gr.Textbox(
                    label="研究主题",
                    placeholder="支持中英文关键词，如：气候变化对农业的影响、cancer immunotherapy...",
                    lines=2
                )
                with gr.Row():
                    search_source = gr.Dropdown(
                        choices=[
                            "Semantic Scholar（全学科推荐）",
                            "AMiner（中文论文强项）",
                            "OpenAlex（开放获取综合）",
                            "PubMed（生物医学）",
                            "CrossRef（期刊论文）",
                            "arXiv（CS/数学/物理）"
                        ],
                        value="Semantic Scholar（全学科推荐）",
                        label="数据源"
                    )
                    max_results = gr.Slider(1, 10, value=5, step=1, label="返回论文数")

                # 高级筛选（仅 Semantic Scholar 支持）
                with gr.Accordion("高级筛选", open=False):
                    search_field = gr.Dropdown(
                        choices=["全部领域"] + [
                            "计算机科学", "人工智能", "医学", "生物学", "物理学", "化学",
                            "数学", "经济学", "心理学", "社会学", "语言学", "哲学",
                            "工程", "环境科学", "材料科学", "教育学", "法学", "商学"
                        ],
                        value="全部领域",
                        label="学科领域"
                    )
                    with gr.Row():
                        year_from = gr.Textbox(label="起始年份", placeholder="2020", scale=1)
                        year_to = gr.Textbox(label="截止年份", placeholder="2025", scale=1)

                search_btn = gr.Button("🔍 开始检索", variant="primary")
            with gr.Column(scale=7):
                search_output = gr.Markdown(label="检索结果", value="*等待搜索...*")
        search_btn.click(
            fn=search_papers,
            inputs=[search_input, search_source, max_results, search_field, year_from, year_to],
            outputs=search_output
        )

    with gr.Tab("📝 论文总结"):
        with gr.Row():
            with gr.Column(scale=4):
                summary_input = gr.Textbox(
                    label="论文内容（粘贴标题、作者、摘要等信息）",
                    placeholder="粘贴论文信息，包括标题、作者、摘要、方法描述...",
                    lines=15
                )
                summary_btn = gr.Button("📝 生成总结", variant="primary")
            with gr.Column(scale=6):
                summary_output = gr.Markdown(label="总结报告", value="*等待输入...*")
        summary_btn.click(
            fn=summarize_paper,
            inputs=[summary_input],
            outputs=summary_output
        )

    with gr.Tab("📎 引用生成"):
        with gr.Row():
            with gr.Column(scale=4):
                cite_title = gr.Textbox(label="论文标题 *", placeholder="Attention Is All You Need")
                cite_authors = gr.Textbox(label="作者 *", placeholder="Vaswani, A., Shazeer, N., Parmar, N., et al.")
                with gr.Row():
                    cite_journal = gr.Textbox(label="期刊/会议", placeholder="NeurIPS")
                    cite_year = gr.Textbox(label="年份", placeholder="2017")
                with gr.Row():
                    cite_volume = gr.Textbox(label="卷号", placeholder="30")
                    cite_pages = gr.Textbox(label="页码", placeholder="5998-6008")
                cite_doi = gr.Textbox(label="DOI（可选）")
                cite_format = gr.Radio(
                    choices=["gbt7714", "apa", "mla"],
                    value="gbt7714",
                    label="引用格式"
                )
                cite_btn = gr.Button("📎 生成引用", variant="primary")
            with gr.Column(scale=6):
                cite_output = gr.Textbox(label="生成的引用", lines=8)
        cite_btn.click(
            fn=generate_citation,
            inputs=[cite_title, cite_authors, cite_journal, cite_year,
                    cite_volume, cite_pages, cite_doi, cite_format],
            outputs=cite_output
        )

    with gr.Tab("✍️ 论文润色"):
        # 当前会话 ID（隐藏）
        polish_session_id = gr.State(value="")

        # 历史会话面板
        with gr.Accordion("📋 历史会话", open=False):
            with gr.Row():
                polish_history_list = gr.Dropdown(
                    label="历史对话", choices=_polish_choices(), scale=6,
                    info="选择一条历史会话后点击加载，可继续对话"
                )
                polish_load_btn = gr.Button("📂 加载", variant="primary", size="sm", scale=1)
                polish_del_btn = gr.Button("🗑️ 删除", variant="stop", size="sm", scale=1)

        # 对话区
        gr.Markdown("粘贴文本后可以持续对话: 说'更正式一些'、'缩短第三段'等，我会记住上下文。")
        polish_chatbot = gr.Chatbot(label="润色对话", height=450)
        with gr.Row():
            polish_msg = gr.Textbox(
                label="输入修改要求",
                placeholder="例如：请润色这段文字... / 把第二段改得更学术化...",
                scale=7
            )
            polish_send = gr.Button("发送", variant="primary", scale=1)
        polish_clear = gr.Button("🗑️ 开始新对话", size="sm", variant="stop")

        # 事件绑定
        polish_send.click(
            fn=polish_chat,
            inputs=[polish_msg, polish_chatbot, polish_session_id],
            outputs=[polish_msg, polish_chatbot, polish_session_id, polish_history_list]
        )
        polish_msg.submit(
            fn=polish_chat,
            inputs=[polish_msg, polish_chatbot, polish_session_id],
            outputs=[polish_msg, polish_chatbot, polish_session_id, polish_history_list]
        )
        polish_clear.click(
            fn=clear_polish_chat,
            outputs=[polish_msg, polish_chatbot, polish_session_id, polish_history_list]
        )
        polish_load_btn.click(
            fn=load_polish_session,
            inputs=[polish_history_list],
            outputs=[polish_chatbot, polish_session_id, polish_history_list]
        )
        polish_del_btn.click(
            fn=delete_polish_session,
            inputs=[polish_history_list],
            outputs=[polish_chatbot, polish_session_id, polish_history_list]
        )

    with gr.Tab("📊 大纲生成"):
        # 当前会话 ID（隐藏）
        outline_session_id = gr.State(value="")

        # 历史会话面板
        with gr.Accordion("📋 历史会话", open=False):
            with gr.Row():
                outline_history_list = gr.Dropdown(
                    label="历史对话", choices=_outline_choices(), scale=6,
                    info="选择一条历史会话后点击加载，可继续对话"
                )
                outline_load_btn = gr.Button("📂 加载", variant="primary", size="sm", scale=1)
                outline_del_btn = gr.Button("🗑️ 删除", variant="stop", size="sm", scale=1)

        # 对话区
        gr.Markdown("输入论文主题后，可以持续对话优化: 说'细化第三章'、'增加实验对比章节'等，我会记住已有大纲并在此基础上修改。")
        outline_chatbot = gr.Chatbot(label="大纲对话", height=450)
        with gr.Row():
            outline_msg = gr.Textbox(
                label="输入要求",
                placeholder="例如：我想写一篇关于XX的毕业论文，帮我生成大纲...",
                scale=7
            )
            outline_send = gr.Button("发送", variant="primary", scale=1)
        outline_clear = gr.Button("🗑️ 开始新对话", size="sm", variant="stop")

        # 事件绑定
        outline_send.click(
            fn=outline_chat,
            inputs=[outline_msg, outline_chatbot, outline_session_id],
            outputs=[outline_msg, outline_chatbot, outline_session_id, outline_history_list]
        )
        outline_msg.submit(
            fn=outline_chat,
            inputs=[outline_msg, outline_chatbot, outline_session_id],
            outputs=[outline_msg, outline_chatbot, outline_session_id, outline_history_list]
        )
        outline_clear.click(
            fn=clear_outline_chat,
            outputs=[outline_msg, outline_chatbot, outline_session_id, outline_history_list]
        )
        outline_load_btn.click(
            fn=load_outline_session,
            inputs=[outline_history_list],
            outputs=[outline_chatbot, outline_session_id, outline_history_list]
        )
        outline_del_btn.click(
            fn=delete_outline_session,
            inputs=[outline_history_list],
            outputs=[outline_chatbot, outline_session_id, outline_history_list]
        )

    with gr.Tab("📝 论文写作"):
        paper_session_id = gr.State(value="")

        with gr.Accordion("📋 历史会话", open=False):
            with gr.Row():
                paper_history_list = gr.Dropdown(
                    label="历史对话", choices=_paper_choices(), scale=6,
                    info="选择历史会话后加载，可继续写作"
                )
                paper_load_btn = gr.Button("📂 加载", variant="primary", size="sm", scale=1)
                paper_del_btn = gr.Button("🗑️ 删除", variant="stop", size="sm", scale=1)

        gr.Markdown("根据大纲逐章撰写论文。粘贴大纲后说'开始写第一章'，可持续对话调整内容。")
        paper_chatbot = gr.Chatbot(label="论文写作对话", height=450)
        with gr.Row():
            paper_msg = gr.Textbox(
                label="输入写作要求",
                placeholder="例如：以下是论文大纲...请从摘要开始撰写 / 写第三章实验部分 / 这部分再详细一些...",
                scale=7
            )
            paper_send = gr.Button("发送", variant="primary", scale=1)
        with gr.Row():
            paper_clear = gr.Button("🗑️ 开始新对话", size="sm", variant="stop")

        paper_send.click(
            fn=paper_write_chat,
            inputs=[paper_msg, paper_chatbot, paper_session_id],
            outputs=[paper_msg, paper_chatbot, paper_session_id, paper_history_list]
        )
        paper_msg.submit(
            fn=paper_write_chat,
            inputs=[paper_msg, paper_chatbot, paper_session_id],
            outputs=[paper_msg, paper_chatbot, paper_session_id, paper_history_list]
        )
        paper_clear.click(
            fn=clear_paper_chat,
            outputs=[paper_msg, paper_chatbot, paper_session_id, paper_history_list]
        )
        paper_load_btn.click(
            fn=load_paper_session,
            inputs=[paper_history_list],
            outputs=[paper_chatbot, paper_session_id, paper_history_list]
        )
        paper_del_btn.click(
            fn=delete_paper_session,
            inputs=[paper_history_list],
            outputs=[paper_chatbot, paper_session_id, paper_history_list]
        )
    with gr.Tab("📄 PDF → Markdown"):
        gr.Markdown("上传 PDF 论文，自动识别标题、章节、段落，输出为格式化的 **Markdown** 文本。")
        with gr.Row():
            with gr.Column(scale=4):
                pdf_input = gr.File(label="上传 PDF 文件", file_types=[".pdf"])
                pdf_max_chars = gr.Slider(0, 100000, value=0, step=1000,
                                           label="字符上限（0=不限制）")
                pdf_btn = gr.Button("📄 转换为 Markdown", variant="primary")
            with gr.Column(scale=6):
                pdf_output = gr.Code(label="Markdown 输出", language="markdown", lines=20)
        pdf_btn.click(
            fn=extract_pdf,
            inputs=[pdf_input, pdf_max_chars],
            outputs=pdf_output
        )

    with gr.Tab("💬 对话记录"):
        # 操作按钮（页面顶部）
        with gr.Row():
            refresh_btn = gr.Button("🔄 刷新", size="sm")
            clear_btn = gr.Button("🗑️ 清空全部", size="sm", variant="stop")

        # 隐藏触发组件：删除按钮通过 JS 填充此字段
        delete_trigger = gr.Textbox(visible=False, elem_id="del_trigger")

        # 历史展示（HTML 格式，每条带删除按钮）
        history_display = gr.HTML(value=logger.format_history_html())

        refresh_btn.click(fn=refresh_history, outputs=history_display)
        clear_btn.click(fn=clear_history, outputs=history_display)
        delete_trigger.change(
            fn=delete_history_record,
            inputs=[delete_trigger],
            outputs=[history_display]
        )

    gr.Markdown("""
    ---
    ### 👤 作者: [@chengH425](https://github.com/chengH425) | 🙏 感谢 Datawhale 社区和 Hello-Agents 项目
    """)


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False, theme=THEME)
