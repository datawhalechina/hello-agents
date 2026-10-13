# -*- coding: utf-8 -*-
"""政策检索：规则级切分 + BM25 打分。

设计要点（与方案一致）：

1. **按二级标题切分，一条规则一片，保留规则编号作元数据**。
   这样检索结果天然带编号，回复引用编号才有据可查，评测也能据此算「依据准确率」。
   原项目用的是 Qdrant 稠密 + 稀疏 + 重排的完整链路，本工程刻意简化为纯 Python
   BM25：不引入向量库与嵌入模型，工程自包含、体积小、离线可跑。

2. **查询里直接出现规则编号时，跳过打分直接加权抬前**。
   这是低成本高收益的兜底：模型把编号写对了却检索不到，是最冤枉的一类失败。

3. **同时保留无编号片段**（文件首部概况、"附：速查"等章节）。
   它们含大量业务关键词，参与检索能提升召回，但不出现在规则清单里。
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, replace
from pathlib import Path

import jieba

# jieba 默认在 DEBUG 级别打印词典加载与缓存日志，批量评测时会把输出刷得看不清，
# 统一压到 WARNING。必须在首次分词之前设置。
jieba.setLogLevel(logging.WARNING)

# 第三方客户端在限流重试时会打 INFO 日志，同样压掉，避免干扰评测进度观察
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

#: 规则编号形如 LOG-001 / GEN-003
RULE_ID_RE = re.compile(r"\b([A-Z]{3})-(\d{3})\b")

#: 二级标题形如 "## LOG-001 发货时效与超时处理"，也可能是无编号章节
SECTION_RE = re.compile(r"^##\s+(?:(?P<rule>[A-Z]{3}-\d{3})\s+)?(?P<name>.+?)\s*$")

#: 文件首部元信息：" > 业务域：物流履约 ｜ 规则前缀：`LOG` ｜ 责任部门：仓储物流部"
DOMAIN_RE = re.compile(r"业务域：\s*([^｜|]+)")

#: BM25 参数：k1 控制词频饱和，b 控制长度归一化，取常见默认值
BM25_K1 = 1.5
BM25_B = 0.75

#: 命中规则编号的额外加权：编号是强信号，值得直接抬到前面
RULE_ID_BOOST = 3.0

#: 无编号片段降权系数。文件首部概况与"附：速查"表内容重复度高、可执行信息少，
#: 实测会挤占正规规则条目的位置（如"少件漏发"案例里 RET-003 被速查表压到第三），
#: 故整体降权，但保留参与召回的能力。
NO_RULE_PENALTY = 0.6

#: 停用词只挡高频虚词，避免把"退款""发货"这类关键词误伤
STOPWORDS = {
    "的", "了", "是", "在", "和", "与", "或", "请", "我", "你", "他", "她", "它",
    "这", "那", "有", "没有", "怎么", "如何", "什么", "为什么", "可以", "能", "吗",
    "呢", "啊", "就", "都", "也", "还", "但", "而", "把", "被", "给", "对", "为",
    "一个", "一下", "一直", "已经", "现在", "但是", "因为", "所以", "如果", "以及",
}


@dataclass
class PolicyChunk:
    """一条规则（或一个无编号章节）的切分结果。"""

    rule_id: str  # 规则编号，无编号章节为空串
    name: str  # 规则名称
    domain: str  # 业务域，取自文件首部元信息
    source: str  # 来源文件名
    text: str  # 正文（不含二级标题行）
    score: float = 0.0  # 检索得分，由检索器填充

    def render(self, head_chars: int = 1400) -> str:
        """渲染成给模型看的观察文本。"""
        title = f"【{self.rule_id}】{self.name}" if self.rule_id else f"【{self.name}】"
        body = self.text.strip()
        if len(body) > head_chars:
            body = body[:head_chars] + "\n…（原文较长，此处截断）"
        return f"{title}（来源：{self.source}）\n{body}"


#: 有实义的字符：中文、字母、数字。用来剔除纯标点词项。
#: 为什么必须剔除：政策正文里当然有大量标点，若不剔除，用户输入一串"？。，"也能命中
#: 一批文档——分数不高但结果毫无意义，还会让"未命中"这个信号失真。
MEANINGFUL_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]")


def tokenize(text: str) -> list[str]:
    """分词并保留规则编号，作为 BM25 的词项。"""
    tokens = [t.strip() for t in jieba.lcut(text)]
    tokens += [m.group(0) for m in RULE_ID_RE.finditer(text)]

    result: list[str] = []
    for token in tokens:
        if not token or token in STOPWORDS:
            continue
        if not MEANINGFUL_RE.search(token):
            continue
        result.append(token.lower())
    return result


class PolicyRetriever:
    """政策知识库检索器：启动时切分建索引，之后只做内存内打分。"""

    def __init__(self, knowledge_dir: Path | str):
        self.knowledge_dir = Path(knowledge_dir)
        self.chunks: list[PolicyChunk] = []
        self._doc_tokens: list[list[str]] = []
        self._doc_len: list[int] = []
        self._avg_len: float = 1.0
        self._inv_index: dict[str, list[int]] = {}
        self._idf: dict[str, float] = {}
        self._by_rule: dict[str, int] = {}
        self._load()

    # ── 切分与建索引 ──

    def _load(self) -> None:
        md_files = sorted(p for p in self.knowledge_dir.glob("*.md") if not p.name.startswith("README"))
        for path in md_files:
            text = path.read_text(encoding="utf-8")
            domain_match = DOMAIN_RE.search(text)
            domain = domain_match.group(1).strip() if domain_match else ""
            self.chunks.extend(self._split(text, path.name, domain))
        self._build_index()

    @staticmethod
    def _split(text: str, source: str, domain: str) -> list[PolicyChunk]:
        """按二级标题切分；首个二级标题之前的内容作为文件概况片段。"""
        chunks: list[PolicyChunk] = []
        file_title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), source)
        rule_id = ""
        name = file_title
        buf: list[str] = []
        saw_heading = False

        def flush() -> None:
            nonlocal buf
            body = "\n".join(buf).strip()
            if name and body:
                chunks.append(PolicyChunk(rule_id=rule_id, name=name, domain=domain, source=source, text=body))
            buf = []

        for line in text.splitlines():
            if line.startswith("## "):
                if saw_heading or buf:
                    flush()
                match = SECTION_RE.match(line)
                rule_id = (match.group("rule") or "") if match else ""
                name = (match.group("name") if match else line[3:]).strip()
                saw_heading = True
                continue
            if line.startswith("# "):
                continue
            buf.append(line)
        flush()
        return chunks

    def _build_index(self) -> None:
        self._doc_tokens = [tokenize(f"{c.name}\n{c.text}") for c in self.chunks]
        self._doc_len = [max(1, len(t)) for t in self._doc_tokens]
        self._avg_len = sum(self._doc_len) / max(1, len(self._doc_len))

        inv: dict[str, list[int]] = {}
        for i, tokens in enumerate(self._doc_tokens):
            for token in set(tokens):
                inv.setdefault(token, []).append(i)
        self._inv_index = inv

        total = len(self.chunks)
        self._idf = {
            token: math.log(1 + (total - len(ids) + 0.5) / (len(ids) + 0.5))
            for token, ids in inv.items()
        }
        self._by_rule = {c.rule_id: i for i, c in enumerate(self.chunks) if c.rule_id}

    # ── 对外接口 ──

    @property
    def rule_ids(self) -> set[str]:
        """知识库中真实存在的规则编号集合，供评测判定"编造编号"。"""
        return set(self._by_rule)

    def search(self, query: str, top_k: int = 5) -> list[PolicyChunk]:
        """BM25 检索，返回得分最高的若干片段（得分为 0 的不返回）。"""
        query = (query or "").strip()
        if not query:
            return []

        scores = [0.0] * len(self.chunks)
        for token in tokenize(query):
            ids = self._inv_index.get(token)
            if not ids:
                continue
            idf = self._idf.get(token, 0.0)
            for i in ids:
                tf = self._doc_tokens[i].count(token)
                denominator = tf + BM25_K1 * (1 - BM25_B + BM25_B * self._doc_len[i] / self._avg_len)
                scores[i] += idf * tf * (BM25_K1 + 1) / denominator

        # 编号直查兜底：查询里写明了编号，就该命中那一条
        for match in RULE_ID_RE.finditer(query):
            index = self._by_rule.get(match.group(0))
            if index is not None:
                scores[index] += RULE_ID_BOOST * (self._idf.get(match.group(0).lower(), 1.0) or 1.0)

        # 无编号片段整体降权，避免速查表压住正规规则条目
        for i, chunk in enumerate(self.chunks):
            if not chunk.rule_id:
                scores[i] *= NO_RULE_PENALTY

        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        results: list[PolicyChunk] = []
        for i in ranked[: max(1, int(top_k))]:
            if scores[i] <= 0:
                continue
            results.append(replace(self.chunks[i], score=round(scores[i], 4)))
        return results

    def list_rules(self, domain: str = "") -> list[dict[str, str]]:
        """列出规则清单（编号/名称/业务域），不返回正文。"""
        rows: list[dict[str, str]] = []
        for chunk in self.chunks:
            if not chunk.rule_id:
                continue
            if domain and domain not in chunk.domain and domain not in chunk.source:
                continue
            rows.append({"rule_id": chunk.rule_id, "name": chunk.name, "domain": chunk.domain})
        return rows

    def stats(self) -> dict[str, object]:
        """知识库概况，供报告与 README 引用。"""
        rules = self.list_rules()
        domains = sorted({r["domain"] for r in rules if r["domain"]})
        return {
            "规则条数": len(rules),
            "片段总数": len(self.chunks),
            "业务域": domains,
            "词项总数": len(self._inv_index),
        }
