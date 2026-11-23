"""Real model/search adapters; tests inject doubles only at these boundaries."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .config import AppError, Settings
from .prompts import INTERVIEW, RESEARCH, ASSESS, WRITER, AUDIT

PROMPTS = {"interview": ("需求澄清", INTERVIEW), "research": ("竞品研究", RESEARCH),
           "assess": ("可行性评估", ASSESS), "writer": ("PRD 编写", WRITER), "audit": ("需求一致性复核", AUDIT)}


def parse_object(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1])
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        raise AppError("模型没有返回有效的结构化结果。请重试，或换用支持 JSON 输出的模型。", 502) from None
    if not isinstance(value, dict):
        raise AppError("模型返回的结果应为 JSON 对象，请重试。", 502)
    return value


class HelloAgentsBackend:
    def __init__(self, settings: Settings):
        self.settings = settings

    def run(self, role: str, context: dict) -> dict:
        self.settings.validate()
        try:
            from hello_agents import HelloAgentsLLM, SimpleAgent
        except ImportError:
            raise AppError("缺少 HelloAgents 依赖。请使用运行本项目的 Python 执行：python -m pip install -r requirements.txt", 503) from None
        name, prompt = PROMPTS[role]
        try:
            llm = HelloAgentsLLM(model=self.settings.model, api_key=self.settings.api_key,
                                 base_url=self.settings.base_url, provider="custom", temperature=0.2, timeout=self.settings.timeout)
            # Fresh agent for each call: explicit session context prevents cross-project history leakage.
            agent = SimpleAgent(name=name, llm=llm, system_prompt=prompt)
            response = agent.run(json.dumps(context, ensure_ascii=False))
        except Exception:
            # Do not forward SDK errors: they may contain headers or provider credentials.
            raise AppError("模型请求失败。请检查连接地址、模型名称、密钥额度或网络后重试。", 502) from None
        return parse_object(str(response))


class TavilySearch:
    def __init__(self, key: str):
        self.key = key

    def search(self, query: str) -> list[dict]:
        if not self.key:
            raise AppError("尚未配置搜索密钥。请配置 Tavily，或关闭联网竞品研究后继续。", 503)
        request = Request("https://api.tavily.com/search", method="POST",
                          data=json.dumps({"query": query, "max_results": 6, "search_depth": "basic",
                                           "include_answer": False, "include_raw_content": False}).encode(),
                          headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read(2_000_000))
        except (HTTPError, URLError, TimeoutError, ValueError, OSError):
            raise AppError("竞品搜索失败，本次未获得可核验的竞品资料。", 502) from None
        results, seen = [], set()
        stamp = datetime.now(timezone.utc).isoformat()
        for item in payload.get("results", [])[:6]:
            url = str(item.get("url", ""))
            parsed = urlparse(url)
            if parsed.scheme not in ("https", "http") or not parsed.hostname or url in seen:
                continue
            seen.add(url)
            results.append({"id": f"S{len(results) + 1}", "title": str(item.get("title", ""))[:300],
                            "url": url, "content": str(item.get("content", ""))[:5000], "retrieved_at": stamp})
        return results
