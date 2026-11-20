"""Local source ingestion and explicit evidence identifiers."""

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TOPIC = "多源观测缺失或延迟时，如何可靠识别人工增雨作业条件，并在证据不足时拒判？"
DEFAULT_RESOURCES = "研究原型；地区与云型待导师确认；尚无经专家独立标注的数据；先做数据盘点和小样本验证。"


def load_sources(path=None):
    payload = json.loads(Path(path or ROOT / "data/sources.json").read_text(encoding="utf-8-sig"))
    return validate_sources(payload.get("sources") if isinstance(payload, dict) else payload)


def validate_sources(sources):
    if not isinstance(sources, list) or not 2 <= len(sources) <= 10:
        raise ValueError("请提供2—10份有文本的资料；可使用内置示例。")
    ids = set()
    total = 0
    normalized = []
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("每份资料必须是JSON对象。")
        s = dict(source)
        sid = s.get("id", "")
        if not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,24}", sid) or sid in ids:
            raise ValueError("资料id须为唯一的字母数字标识，如P1。")
        ids.add(sid)
        if not isinstance(s.get("title"), str) or not s["title"].strip():
            raise ValueError(f"{sid}缺少标题。")
        url = s.get("url", "")
        if url and (not isinstance(url, str) or urlsplit(url).scheme not in ("http", "https")):
            raise ValueError(f"{sid}的来源链接必须是http/https网址。")
        if not isinstance(s.get("authors", []), list) or any(not isinstance(a, str) for a in s.get("authors", [])):
            raise ValueError(f"{sid}的authors应为字符串列表。")
        pages = s.get("pages")
        if not isinstance(pages, list) or not pages:
            raise ValueError(f"{sid}只有元数据，没有可分析的正文或摘要，请补充文本。")
        for i, page in enumerate(pages):
            if not isinstance(page, dict) or not isinstance(page.get("text"), str) or not page["text"].strip():
                raise ValueError(f"{sid}第{i + 1}段缺少文本。")
            if len(page["text"]) > 18000:
                raise ValueError("单段文本过长，请按页或小段拆分（每段不超过18000字符）。")
            total += len(page["text"])
        if total > 100000:
            raise ValueError("本版单次资料文本最多100000字符，请先选取与研究问题相关的段落。")
        s.setdefault("authors", [])
        s.setdefault("year", "未核实")
        s.setdefault("venue", "未核实")
        s.setdefault("doi", "")
        s.setdefault("url", "")
        s.setdefault("kind", "paper")
        s.setdefault("reading_scope", "用户提供文本；元数据待核实")
        normalized.append(s)
    return normalized


def fingerprint(sources):
    return hashlib.sha256(json.dumps(sources, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def evidence_for(sources):
    """Every included text span has an ID, a location, and a provenance label."""
    evidence = []
    for s in sources:
        for i, page in enumerate(s["pages"], 1):
            evidence.append({"id": f"{s['id']}-E{i}", "source_id": s["id"],
                             "location": str(page.get("page", f"段落{i}")),
                             "provenance": page.get("provenance", "用户提供文本，待核实"),
                             "text": page["text"], "url": s["url"]})
    return evidence


def pdf_source(path, source_id="P1", title=None, url=""):
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        raise ValueError("暂不支持加密PDF，请先解密或粘贴可读取的文本。")
    pages = []
    for i, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        if text:
            # Preserve page location when splitting long pages.
            for start in range(0, len(text), 12000):
                pages.append({"page": f"PDF第{i}页", "text": text[start:start + 12000],
                              "provenance": "PDF文本自动提取，图表图像未解析，需核对"})
    if sum(len(p["text"]) for p in pages) < 100:
        raise ValueError("PDF未提取到足够文本，可能是扫描件。请OCR后导入或粘贴摘要。")
    if sum(len(p["text"]) for p in pages) > 100000:
        raise ValueError("PDF文本超过本版100000字符上限，请选取相关章节后导入。")
    metadata = reader.metadata or {}
    return {"id": source_id, "title": title or metadata.get("/Title") or Path(path).stem,
            "authors": [], "year": "未核实", "venue": "未核实", "doi": "", "url": url,
            "kind": "paper", "reading_scope": "PDF文本；不含OCR、图表视觉理解；作者年份待核实", "pages": pages}


def search_crossref(query, limit=5):
    """Retrieve metadata and available abstracts, never fabricate missing abstracts."""
    import requests
    if not query.strip() or len(query) > 300:
        raise ValueError("请输入1—300字符的检索词。")
    response = requests.get("https://api.crossref.org/works", params={"query.bibliographic": query, "rows": min(max(limit, 1), 8)},
                            headers={"User-Agent": "CloudSeedResearchAgent/0.1 (educational literature assistant)"}, timeout=20)
    response.raise_for_status()
    results = []
    for i, item in enumerate(response.json()["message"]["items"], 1):
        abstract = re.sub(r"<[^>]*>", " ", item.get("abstract", "")).strip()
        authors = [" ".join(filter(None, [a.get("given"), a.get("family")])) for a in item.get("author", [])]
        dates = item.get("published", {}).get("date-parts", [["未核实"]])
        results.append({"id": f"R{i}", "title": item.get("title", ["未报告标题"])[0], "authors": authors,
                        "year": dates[0][0], "venue": "; ".join(item.get("container-title", [])),
                        "doi": item.get("DOI", ""), "url": item.get("URL", ""), "kind": "paper",
                        "reading_scope": "Crossref元数据与摘要；未读取全文",
                        "pages": [{"page": "Crossref摘要", "text": abstract, "provenance": "Crossref提供的摘要文本"}] if abstract else [],
                        "needs_text": not bool(abstract)})
    return results
