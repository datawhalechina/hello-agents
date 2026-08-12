"""维基百科开放 API：多语种条目检索与对照（无需密钥，需遵守使用规范）。"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests

_WIKI_UA = (
    "HelloAgentsHistoricalReview/1.0 (educational; https://github.com/datawhalechina/hello-agents)"
)
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": _WIKI_UA})


def _get(lang: str, params: dict[str, Any]) -> dict[str, Any]:
    host = f"https://{lang}.wikipedia.org/w/api.php"
    r = _SESSION.get(host, params=params, timeout=25)
    r.raise_for_status()
    return r.json()


def wiki_search(params: str) -> str:
    """
    在指定语言维基中按关键词搜索条目标题。

    参数格式：`语言代码###关键词`
    示例：`zh###安史之乱`、`en###Fall of Constantinople`
    """
    raw = (params or "").strip()
    if "###" not in raw:
        return "错误：格式应为 语言代码###关键词，例如 zh###靖康之变"
    lang, _, q = raw.partition("###")
    lang, q = lang.strip().lower(), q.strip()
    if not lang or not q:
        return "错误：语言和关键词均不能为空。"

    data = _get(
        lang,
        {
            "action": "opensearch",
            "search": q,
            "limit": 8,
            "namespace": 0,
            "format": "json",
        },
    )
    # opensearch: [term, [titles], [desc], [urls]]
    if not isinstance(data, list) or len(data) < 2:
        return f"[{lang}] 搜索无结果或接口异常。"
    titles = data[1] if len(data) > 1 else []
    descs = data[2] if len(data) > 2 else []
    if not titles:
        return f"[{lang}] 未找到与「{q}」匹配的条目，可换 en###同一主题的英文检索词再试。"

    lines = [f"[{lang}.wikipedia] 关键词「{q}」候选条目："]
    for i, t in enumerate(titles):
        d = descs[i] if i < len(descs) else ""
        lines.append(f"  {i+1}. {t} — {d[:200]}")
    lines.append("\n建议：用 wiki_article 拉取全文摘录，或 wiki_multiview 做中英日等多语种对照。")
    return "\n".join(lines)


def wiki_article(params: str) -> str:
    """
    获取维基条目纯文本摘录（非导语部分也会尽量多取字符）。

    参数格式：`语言代码###条目名`（条目名需与站内标题一致或接近）
    示例：`zh###岳飞`、`en###Qin Shi Huang`
    """
    raw = (params or "").strip()
    if "###" not in raw:
        return "错误：格式应为 语言代码###条目名，例如 zh###王安石"
    lang, _, title = raw.partition("###")
    lang, title = lang.strip().lower(), title.strip()
    if not lang or not title:
        return "错误：语言或条目名为空。"

    data = _get(
        lang,
        {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "explaintext": 1,
            "exchars": 10000,
            "format": "json",
        },
    )
    pages = data.get("query", {}).get("pages", {})
    out: list[str] = []
    for _pid, page in pages.items():
        if int(_pid) < 0 or page.get("missing"):
            out.append(f"[{lang}] 未找到条目「{title}」。请先用 wiki_search 查准确标题。")
            continue
        t = page.get("title", title)
        ex = (page.get("extract") or "").strip()
        if not ex:
            out.append(f"[{lang}]「{t}」无正文摘录（可能是消歧义页）。")
            continue
        if len(ex) > 11000:
            ex = ex[:11000] + "\n... [截断]"
        url = f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"
        out.append(f"=== {lang}.wikipedia / {t} ===\n{url}\n\n{ex}")
    return "\n\n".join(out) if out else "未获取到内容。"


def wiki_langlinks(params: str) -> str:
    """
    列出某条目在其他语言维基中的对应标题（便于横向对比域外叙述）。

    参数格式：`语言代码###条目名`
    """
    raw = (params or "").strip()
    if "###" not in raw:
        return "错误：格式应为 语言代码###条目名"
    lang, _, title = raw.partition("###")
    lang, title = lang.strip().lower(), title.strip()

    data = _get(
        lang,
        {
            "action": "query",
            "titles": title,
            "prop": "langlinks",
            "lllimit": 50,
            "format": "json",
        },
    )
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return "未查询到页面。"
    lines: list[str] = []
    for _pid, page in pages.items():
        if page.get("missing"):
            return f"未找到「{title}」。"
        resolved = page.get("title", title)
        links = page.get("langlinks") or []
        if not links:
            return f"「{resolved}」暂无其他语言链接，可换 en/zh 起搜或直接用 search 找外国史籍研究。"
        lines.append(f"条目「{resolved}」({lang}.wiki) 的部分语种对应：")
        for ll in links[:40]:
            lines.append(f"  - {ll.get('lang')}: {ll.get('*')}")
    return "\n".join(lines)


def _query_page_extract_and_links(
    lang: str, title: str
) -> tuple[str | None, str | None, dict[str, str]]:
    """返回 (resolved_title, extract_plain, langlinks map lang_code->foreign_title)。"""
    data = _get(
        lang,
        {
            "action": "query",
            "titles": title,
            "prop": "langlinks|extracts",
            "lllang": "en|ja|ko|zh|fr|de",
            "lllimit": 30,
            "explaintext": 1,
            "exchars": 5000,
            "format": "json",
        },
    )
    pages = data.get("query", {}).get("pages", {})
    for _pid, page in pages.items():
        if page.get("missing"):
            return None, None, {}
        resolved = page.get("title", title)
        ex = (page.get("extract") or "").strip()
        links = {ll["lang"]: ll["*"] for ll in (page.get("langlinks") or [])}
        return resolved, ex or None, links
    return None, None, {}


def _looks_cjk(text: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in text)


def wiki_multiview(params: str) -> str:
    """
    以关键词起搜：含汉字时优先中文维基；纯拉丁字母等则优先英文维基（避免误匹配）。
    再拉取关联语种（如英/日/中与主站交叉）条目摘录并列。
    """
    q = (params or "").strip()
    if not q:
        return "错误：请提供历史事件或人物关键词。"

    blocks: list[str] = []
    targets: list[tuple[str, str]] = []
    seen_titles: set[tuple[str, str]] = set()

    def add_block(lang: str, title: str, label: str, excerpt: str) -> None:
        key = (lang, title)
        if key in seen_titles:
            return
        seen_titles.add(key)
        if len(excerpt) > 5500:
            excerpt = excerpt[:5500] + "..."
        blocks.append(
            f"{label}{title}\n"
            f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}\n\n{excerpt}"
        )

    primary = "zh" if _looks_cjk(q) else "en"
    secondary = "en" if primary == "zh" else "zh"

    os_primary = _get(
        primary,
        {
            "action": "opensearch",
            "search": q,
            "limit": 5,
            "namespace": 0,
            "format": "json",
        },
    )
    p_title = None
    if isinstance(os_primary, list) and len(os_primary) > 1 and os_primary[1]:
        p_title = os_primary[1][0]

    if p_title:
        resolved, ex, links = _query_page_extract_and_links(primary, p_title)
        if resolved and ex and "may refer to" not in ex.lower() and "消歧义" not in ex[:80]:
            add_block(primary, resolved, "【主站维基】", ex)
            order = ["en", "ja", "ko", "zh", "fr", "de"] if primary == "zh" else ["zh", "ja", "ko", "en"]
            for code in order:
                if code == primary:
                    continue
                if code in links:
                    targets.append((code, links[code]))

    if not blocks:
        os_sec = _get(
            secondary,
            {
                "action": "opensearch",
                "search": q,
                "limit": 5,
                "namespace": 0,
                "format": "json",
            },
        )
        s_title = None
        if isinstance(os_sec, list) and len(os_sec) > 1 and os_sec[1]:
            s_title = os_sec[1][0]
        if s_title:
            resolved, ex, links = _query_page_extract_and_links(secondary, s_title)
            if resolved and ex:
                add_block(secondary, resolved, "【备用语种维基】", ex)
                order = ["zh", "en", "ja", "ko"] if secondary == "en" else ["en", "ja", "ko"]
                for code in order:
                    if code == secondary:
                        continue
                    if code in links:
                        targets.append((code, links[code]))

    for lang, tit in targets:
        key = (lang, tit)
        if key in seen_titles:
            continue
        snippet = wiki_article(f"{lang}###{tit}")
        if snippet.startswith("错误") or "未找到条目" in snippet:
            continue
        blocks.append(f"\n--- 对照语种 {lang} ---\n{snippet}")

    if not blocks:
        return (
            f"未能为「{q}」自动匹配到维基正文。请用 wiki_search 分别试 zh### 与 en###，"
            "或使用 search 检索学术/史料网页后再 fetch_url_text。"
        )

    header = (
        f"多语种维基摘录对照（关键词：{q}）。注意：维基为二手综述，非原始档案；"
        "不同语种条目由不同社群编写，立场与侧重可能不同。\n"
    )
    body = "\n\n".join(blocks)
    if len(header) + len(body) > 28000:
        body = body[: 28000 - len(header)] + "\n... [总长度已截断]"
    return header + body
