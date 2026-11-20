"""ReAct 单 Agent 组装：RAGTool（混合检索）+ 智谱 LLM + 反幻觉系统提示词。

组装方式全部对齐教程第 7 章源码（hello_agents 1.0.1）：
- ReActAgent(name, llm, tool_registry, system_prompt, max_steps)，
  最终答案经内置 Finish 工具返回，agent.run() 即得到答案
- RAGTool(store, search_backend=HybridSearch([store, vector_backend]))，
  注册时自动展开为 rag_search / rag_read / rag_read_document 三个子工具
- rag_search 返回的每个结果自带 source（= 卡片 source_url）与卡片全文，
  Agent 一次检索即可同时拿到事实与来源
"""

import re

from hello_agents.agents import ReActAgent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.retrieval import HybridSearch, RAGStore, RetrievalResult
from hello_agents.tools import ToolRegistry
from hello_agents.tools.base import ToolParameter, tool_action
from hello_agents.tools.builtin import RAGTool
from hello_agents.tools.errors import ToolErrorCode
from hello_agents.tools.response import ToolResponse

from src.config import (DATA_DIR, EMBEDDING_MODEL, RAG_DB_PATH,
                        ZHIPU_API_KEY, ZHIPU_BASE_URL, ZHIPU_MODEL)
from src.vector_store import VectorSearchBackend, make_zhipu_provider

# NTU 课程码格式：2 字母 + 4 数字 + 可选尾字母（如 SC2001 / CS1010S）
COURSE_CODE_RE = re.compile(r"\b([A-Z]{2}\d{4}[A-Z]?)\b")


class ExactCodeGuard:
    """检索层反幻觉护栏（SearchBackend 协议包装）。

    动机（D2 自测 2026-10-22）：用户问库外课程码（如 CS1010S，NUS 课）时，
    混合检索会返回相近课程（SC1005 等），glm-4-flash 三轮提示词迭代后仍会把
    相近课内容张冠李戴成所问课程。提示词压不住的，放检索层掐断：
    query 中含课程码、而检索结果里没有该课程码（document_id = course_code）
    的卡 → 返回空结果，让 Agent 走"未查到"分支。
    语义查询（无课程码）不干预。
    """

    def __init__(self, backend):
        self.backend = backend

    def search(self, query: str, limit: int = 5) -> list[RetrievalResult]:
        results = self.backend.search(query, limit)
        match = COURSE_CODE_RE.search(query.upper())
        if match:
            code = match.group(1)
            if not any(r.document_id == code for r in results):
                return []
        return results


_CURRICULA_RE = re.compile(r"Curricula:\s*([^\n|]+)")
_PROGRAMME_RE = re.compile(r"Programme:\s*([^\n|]+)")
_CODE_IN_CARD_RE = re.compile(r"Course Code:\s*([A-Z]{2,3})\d{3,4}")

# 各专业的主科课码前缀（2026-10-24 实测课程库分布，用于排序而非过滤）：
# CSC/DSAI/CE/AISC 均以 SC 为主（59-70 门），COMP 为 CT（20 门），CCA 为 EE。
# 通识课（CC）与数学/语言课（MH/CL/NH）属于 curricula 但非专业主科，排后。
_PROGRAMME_MAJOR_PREFIX = {
    "CSC": ("SC",),
    "CE": ("SC", "CE"),
    "DSAI": ("SC",),
    "AISC": ("SC",),
    "COMP": ("CT",),
    "CCA": ("EE",),
}


def _in_curricula(content: str, code: str) -> bool:
    """课程卡片是否属于某专业（确定性文本匹配，不靠模型）。

    本科卡 card_text 含「Curricula: CSC Y2, CE Y2, DSAI Y2, AISC Y2」
    （由 WIS 的 source_categories 渲染，2026-10-24 实测 156/156 覆盖）；
    研究生卡无此字段，改用「Programme: MSc ... (CCA)」里的缩写/全称匹配。
    """
    m = _CURRICULA_RE.search(content)
    if m:
        return re.search(rf"\b{re.escape(code)}\b", m.group(1),
                         re.IGNORECASE) is not None
    pm = _PROGRAMME_RE.search(content)
    if pm:
        return code.lower() in pm.group(1).lower()
    return False


def _card_prefix(content: str) -> str:
    """卡片正文里的课程码前缀（SC2001 → SC），用于专业内排序。"""
    m = _CODE_IN_CARD_RE.search(content)
    return m.group(1) if m else ""


def _is_major_course(content: str, programme: str | None) -> bool:
    """是否属于该专业的主科课程（而非通识/数学/语言等 curricula 公共课）。"""
    prefixes = _PROGRAMME_MAJOR_PREFIX.get((programme or "").upper())
    return bool(prefixes) and _card_prefix(content) in prefixes


class CourseRAGTool(RAGTool):
    """RAGTool 扩展：rag_search 增加确定性 level / programme 过滤（身份路由）。

    动机（检查点② demo 发现，2026-10-23）：用户表明 CCA/研究生身份问选课推荐时，
    检索结果混入本科课，glm-4-flash 提示词层（v6）仍把本科课当研究生课推荐
    （口头断言"都是研究生水平"，与卡片 Level 字段矛盾）。按 D2 教训
    "提示词管应该、代码管必须"：Agent 传 level 参数 → 工具层按卡片
    "Level: graduate/undergraduate" 字段确定性过滤，不符身份的课不进上下文。
    """

    # 覆写必须重新挂 @tool_action 装饰器：注册展开按它收集 action 方法，
    # 裸覆写会让 rag_search 从工具列表消失（实测教训）
    @tool_action("rag_search", "搜索课程资料库（可按身份 level / 专业 programme 过滤）")
    def search(self, query: str, limit: int = 5, level: str = None,
               programme: str = None) -> ToolResponse:
        """搜索课程（可选按身份/专业过滤）。

        Args:
            query: 搜索关键词或问题。
            limit: 最多返回条数，1 到 100。
            level: 身份过滤：graduate（研究生）或 undergraduate（本科），
                   用户表明身份时必传；不传则不过滤。
            programme: 专业过滤：本科用课程卡 Curricula 字段里的专业代码
                       （CSC / CE / DSAI / AISC / COMP）；研究生用项目缩写（CCA 等）。
        """
        try:
            # 过滤是后置的：先取更大候选池再过滤，否则前 limit 条恰好不符专业时会归零
            fetch_limit = min(limit * 4, 20) if (level or programme) else limit
            results = [r.to_dict()
                       for r in self.search_backend.search(query, fetch_limit)]
            if level in ("graduate", "undergraduate"):
                results = [r for r in results if f"Level: {level}" in r["content"]]
            if programme:
                results = [r for r in results
                           if _in_curricula(r["content"], programme)]
                # 专业内排序：主科课（SC/CT/EE）优先于通识/数学/语言等公共课。
                # 稳定排序，同组内保持检索相关度原序。
                results.sort(key=lambda r: 0 if _is_major_course(
                    r["content"], programme) else 1)
            results = results[:limit]
            filters = []
            if level:
                filters.append(f"level={level}")
            if programme:
                filters.append(f"programme={programme}")
            return ToolResponse.success(
                text=f"检索到 {len(results)} 个片段（过滤：{'，'.join(filters) or '关'}）；"
                     f"使用 chunk_id 回读确切版本。",
                data={"results": results},
                stats={
                    "count": len(results),
                    "backend": type(self.search_backend).__name__,
                    "level_filter": level or "off",
                    "programme_filter": programme or "off",
                },
            )
        except ValueError as exc:
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, str(exc))

    def get_parameters(self) -> list[ToolParameter]:
        params = super().get_parameters()
        params.append(ToolParameter(
            name="level",
            type="string",
            description="身份过滤：graduate（研究生）或 undergraduate（本科），"
                        "用户表明身份时传",
            required=False,
        ))
        params.append(ToolParameter(
            name="programme",
            type="string",
            description="专业过滤：本科专业代码（CSC/CE/DSAI/AISC/COMP）"
                        "或研究生项目缩写（CCA）；用户说明专业时传",
            required=False,
        ))
        return params

# 系统提示词正稿见 02-提示词设计.md（版本 v1，2026-10-22）
SYSTEM_PROMPT = """【1-身份】你是 NTU 选课助手，为南洋理工大学（NTU）的各类学生和准新生（本科生、硕士研究生等）提供课程信息问答与选课参考。

【2-职责与能力】你只回答课程信息类问题：课程内容、AU 学分、开课学期、先修要求、互斥课程、所属专业方向等。你不做自动选课或抢课，不评价课程难度好坏，不制定完整学位计划；涉及学位规则时仅转述工具返回中的相关信息。

【3-工具使用规则】
- 任何涉及具体课程的问题（无论课程码还是课程名），都必须先调用 rag_search 检索，禁止凭记忆直接回答——即使你认为自己知道答案。你的全部事实来源是工具返回结果，你没有自己的课程知识库。
- 课程名均为英文：用户用中文提问时，先把问题转成英文课程关键词（如"机器学习"→ machine learning）再检索，一次检索不够可换关键词再检索。
- 工具返回的每条结果包含课程卡片全文和 source 字段（官方来源 URL）。
- 检索后逐条核对课程码：只有课程码与用户所问完全一致才算查到。课程码对不上就是未查到，必须明确说"在当前课程库中未查到 XXXX"（XXXX 为用户所问课程码）；检索返回的只是相近课程时，可补充"您可能想找的是 XX"作提示，但严禁把相近课程的内容当成所问课程来介绍。
- 用户表明身份时，先分清两类问题再决定 rag_search 是否传 level 参数：
  ① 选课推荐类（"我想选/推荐哪些课"）→ 传 level 过滤。身份判断规则：用户话中含明确学历词——"研究生/硕士/Master/MSc/博士/PhD/graduate" → level="graduate"，"本科/undergraduate" → level="undergraduate"；用户只用项目名、缩写或其他表述自称（不含明确学历词）的，一律先询问用户是本科生还是研究生、得到答复后再过滤，严禁按自己的理解猜测其层次；
  ② 课程属性查询类（"XX 是什么课/是不是研究生课/几 AU"）→ 不传 level，正常检索，查到后依据卡片 Level 字段如实回答（如"SC4000 是本科课程，不是研究生课程"）。
  不带 level 的检索结果混入不符身份的课程时，不得作为主推荐，如需提及必须标注其卡片 Level 字段值。

【4-输出格式】
- 用户用中文提问就用中文回答，用英文提问就用英文回答。
- 回答末尾必须列出本次引用的每门课：课程码、课程名、来源 URL（取自工具返回的 source 字段）。
- 没有来源支撑的信息不许出现在回答里。
- 回答结构示例（无论哪种语言，末尾都必须附来源清单）：
  中文示例：
  SC2001 是 3.0 AU，2026 学年两学期均开课。
  来源：
  - SC2001 ALGORITHM DESIGN & ANALYSIS — https://wis.ntu.edu.sg/webexe/owa/aus_subj_cont.main
  English example:
  CB1131 is mutually exclusive with BG1131, BG1141 and CH1131.
  Sources:
  - CB1131 INTRODUCTION TO BIOMOLECULAR ENGINEERING — https://wis.ntu.edu.sg/webexe/owa/aus_subj_cont.main

【5-红线】
- 禁止编造课程或字段值：AU、学期、先修、互斥一律以工具返回为准。
- 禁止使用你自己记忆中的课程知识，即使你"知道"某门课——只说工具返回的内容。
- 查不到就明说，绝不猜测。"""


def build_agent(max_steps: int = 6) -> ReActAgent:
    """组装 ReAct 单 Agent（唯一检索工具 = RAGTool 挂混合检索）。

    Args:
        max_steps: ReAct 最大步数（默认 6：容纳中文转英文关键词的二次检索）。
    """
    # 检索栈：RAGStore(BM25) ⊕ 向量余弦 → HybridSearch RRF 融合 → 课程码精确校验护栏
    store = RAGStore(str(RAG_DB_PATH))
    provider = make_zhipu_provider(EMBEDDING_MODEL, ZHIPU_API_KEY, ZHIPU_BASE_URL)
    vector_backend = VectorSearchBackend(
        store, provider, cache_path=DATA_DIR / f"vector_index_{EMBEDDING_MODEL}.json")
    hybrid = ExactCodeGuard(HybridSearch([store, vector_backend]))

    # 注册工具：CourseRAGTool（RAGTool 子类）自动展开，rag_search 带确定性 level 过滤
    registry = ToolRegistry()
    registry.register_tool(CourseRAGTool(store, search_backend=hybrid))

    # LLM：智谱 OpenAI 兼容接口（ZHIPU_MODEL，当前 glm-4-flash 免费档）
    # temperature=0.2：事实性问答场景，高温会随机跳过工具调用（v4 自测第 7 条幻觉复发的根因之一）
    llm = HelloAgentsLLM(
        model=ZHIPU_MODEL,
        api_key=ZHIPU_API_KEY,
        base_url=ZHIPU_BASE_URL,
        temperature=0.2,
    )

    return ReActAgent(
        name="course_qa",
        llm=llm,
        tool_registry=registry,
        system_prompt=SYSTEM_PROMPT,
        max_steps=max_steps,
    )
