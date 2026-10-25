"""NTU 课程目录 MCP server（stdio）。

把本项目的**课程检索能力**做成独立工具服务：外部程序（其他 Agent / IDE /
CLI）通过 MCP 即可查询课程库，无需了解内部 RAG 实现。这是 MCP 的真实价值
——能力外放，而非在主流程里多绕一层（后者与本地工具重复，2026-10-24 拍板）。

工具：
  search_courses  —— 混合检索（BM25 ⊕ 向量）+ level / programme 过滤
  get_course      —— 按课码取单课全字段
  list_coverage   —— 课程库覆盖范围（避免外部调用方提问越界）
  cca_degree_rules / cca_specialized_elective_list —— 学位规则（原有能力）

运行：python scripts/mcp_server.py（stdio，由客户端拉起）
演示：python scripts/mcp_demo.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# mcp 2.x：FastMCP 改名 MCPServer（与框架 hello-agents 1.0.1 的 MCPConnection
# 所要求的 `from mcp import Client` 同版本线）
from mcp.server.mcpserver import MCPServer  # noqa: E402

from hello_agents.retrieval import HybridSearch, RAGStore  # noqa: E402

from src.agent import ExactCodeGuard, _in_curricula  # noqa: E402
from src.config import (DATA_DIR, EMBEDDING_MODEL, RAG_DB_PATH,  # noqa: E402
                        ZHIPU_API_KEY, ZHIPU_BASE_URL)
from src.validators import CCA_OPTIONS, CCA_PROGRAMME_URL, _cards  # noqa: E402
from src.vector_store import VectorSearchBackend, make_zhipu_provider  # noqa: E402

mcp = MCPServer("ntu-course-catalog")

# ---------- 检索栈（与主流程同构：RAGStore BM25 ⊕ 向量余弦 → RRF） ----------
# 延迟初始化：MCP 的 stdio 通道占用 stdout，任何 print 都会污染 JSON 流
# （实测 Windows 下中文日志按 GBK 输出，客户端报 UnicodeDecodeError）。
# 因此在 run() 之前初始化，且初始化期把 stdout 临时指向 stderr。
_backend = None


def _ensure_backend():
    global _backend
    if _backend is not None:
        return _backend
    saved, sys.stdout = sys.stdout, sys.stderr
    try:
        store = RAGStore(str(RAG_DB_PATH))
        provider = make_zhipu_provider(EMBEDDING_MODEL, ZHIPU_API_KEY, ZHIPU_BASE_URL)
        vector = VectorSearchBackend(
            store, provider,
            cache_path=DATA_DIR / f"vector_index_{EMBEDDING_MODEL}.json")
        _backend = ExactCodeGuard(HybridSearch([store, vector]))
        # 预热一次：向量缓存是惰性加载的（首次 search 才打出 "[vector] 命中缓存"），
        # 不在重定向期内触发就会污染 MCP 的 stdout JSON 流
        _backend.search("warmup", 1)
    finally:
        sys.stdout = saved
    return _backend

_CODE_RE = re.compile(r"Course Code:\s*([A-Z]{2}\d{4}[A-Z]?)")

_CARD_FIELDS = ("course_code", "title", "au", "level", "programme", "category",
                "semesters", "prerequisite", "mutually_exclusive",
                "not_available_to", "description", "source_url")


def _card_of(content: str) -> dict | None:
    """检索结果文本 → 结构化卡片（课码来自 card_text 首行）。"""
    m = _CODE_RE.search(content)
    if not m:
        return None
    return _cards().get(m.group(1))


def _pick(card: dict, with_description: bool = True) -> dict:
    fields = _CARD_FIELDS if with_description else _CARD_FIELDS[:-2]
    return {k: card.get(k) for k in fields if card.get(k) not in (None, "", [])}


@mcp.tool()
def search_courses(query: str, level: str = "", programme: str = "",
                   limit: int = 5) -> str:
    """检索 NTU 课程库（201 门：本科 CCDS 学院 5 专业 + 研究生 CCA/Robotics）。

    Args:
        query: 检索词（英文效果更好；中文可依赖向量语义召回）
        level: 可选，graduate / undergraduate；留空不过滤
        programme: 可选，本科 CSC/CE/DSAI/AISC/COMP，研究生 CCA；留空不过滤
        limit: 返回条数，1-20
    """
    limit = max(1, min(int(limit), 20))
    # 过滤是后置的：先取更大候选池，否则前 limit 条恰好不符条件时会归零
    fetched = min(limit * 4, 20) if (level or programme) else limit
    results = [r.to_dict() for r in _ensure_backend().search(query, fetched)]
    if level in ("graduate", "undergraduate"):
        results = [r for r in results if f"Level: {level}" in r["content"]]
    if programme:
        results = [r for r in results if _in_curricula(r["content"], programme)]
        results.sort(key=lambda r: 0 if _in_curricula(r["content"], programme) else 1)

    items, seen = [], set()
    for r in results:
        card = _card_of(r["content"])
        if card is None or card["course_code"] in seen:
            continue
        seen.add(card["course_code"])
        items.append({**_pick(card), "source": r.get("source") or card.get("source_url")})
        if len(items) >= limit:
            break
    return json.dumps({"count": len(items), "results": items},
                      ensure_ascii=False, indent=2)


@mcp.tool()
def get_course(course_code: str) -> str:
    """按课程码取单门课的全部字段（含来源 URL）。查不到会明说，不猜测。

    Args:
        course_code: 课程代码，如 SC2001 / EE6407
    """
    code = (course_code or "").strip().upper()
    card = _cards().get(code)
    if card is None:
        return json.dumps({"found": False,
                           "message": f"课程库中未收录 {code}（覆盖范围见 list_coverage）"},
                          ensure_ascii=False)
    return json.dumps({"found": True, "course": _pick(card)},
                      ensure_ascii=False, indent=2)


@mcp.tool()
def list_coverage() -> str:
    """列出课程库覆盖范围（学历层次、项目、课程数）。"""
    cards = _cards()
    ug = sum(1 for c in cards.values() if c.get("level") == "undergraduate")
    grad: dict[str, int] = {}
    for c in cards.values():
        if c.get("level") == "graduate":
            name = c.get("programme") or "未标注项目"
            grad[name] = grad.get(name, 0) + 1
    return json.dumps({
        "total": len(cards),
        "undergraduate": {"count": ug,
                          "programmes": ["CSC", "CE", "DSAI", "AISC", "COMP"],
                          "note": "仅覆盖 CCDS 学院；其他学院未收录"},
        "graduate": [{"programme": k, "count": v} for k, v in sorted(grad.items())],
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def cca_degree_rules(option: int = 0) -> str:
    """查询 NTU MSc Computer Control & Automation (CCA) 学位规则。

    Args:
        option: 1 = Option 1（10 门课 30AU）、2 = Option 2（8 门课+论文）；
                0 或其他值 = 返回两个 Option 的完整规则
    """
    if option in CCA_OPTIONS:
        payload = {"option": option, **CCA_OPTIONS[option],
                   "source": CCA_PROGRAMME_URL}
    else:
        payload = {"options": {str(k): v for k, v in CCA_OPTIONS.items()},
                   "source": CCA_PROGRAMME_URL}
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.tool()
def cca_specialized_elective_list() -> str:
    """列出课程库内属于 CCA 专选（specialized elective）的课程码与名称。"""
    items = [{"code": c["course_code"], "title": c["title"]}
             for c in _cards().values()
             if c.get("category") == "specialized_elective"]
    return json.dumps({"count": len(items), "courses": items,
                       "source": CCA_PROGRAMME_URL}, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # stdout 必须是 UTF-8 且只承载 MCP 协议 JSON（Windows 默认 GBK 会污染流）
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    _ensure_backend()  # 索引加载期日志已重定向到 stderr
    mcp.run()  # stdio 模式
