from __future__ import annotations

from dataclasses import dataclass
from urllib.request import Request, urlopen
import json
import re


@dataclass(slots=True)
class LLMClient:
    model_name: str
    api_key: str
    base_url: str
    timeout_seconds: int
    json_mode: bool = True

    def is_enabled(self) -> bool:
        return bool(self.model_name and self.api_key and self.base_url)

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_enabled():
            raise RuntimeError("LLM client is not configured. Check .env.")

        payload = {
            "model": self.model_name,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}

        body = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            choices = data.get("choices") or []
            if not choices:
                raise RuntimeError(f"Unexpected LLM response: {raw}")
            message = choices[0].get("message") or {}
            return (message.get("content") or "").strip()


SUMMARY_SYSTEM_PROMPT = """
你是一名高标准的中文技术简报编辑，面向持续跟踪 AI/LLM、工程实践、科技产业判断的读者。

你的任务不是直译文章，而是输出高质量的结构化中文阅读卡片。

规则：
1. 只输出 JSON，不要输出任何额外解释。
2. 对技术文章优先提炼：解决的问题、方法、限制、工程意义。
3. 对产业文章优先提炼：核心判断、依据、商业影响、可能偏差。
4. 如果文章信息密度不高，要明确给低分，并建议跳过。
5. 语言要自然、准确、克制，避免空话。
6. 关键词尽量保留英文术语原词。
"""


TRANSLATION_SYSTEM_PROMPT = """
你是一名专业技术翻译编辑。你的任务是把英文技术或商业文章翻译成自然、准确、适合中文读者的版本。

规则：
1. 保留关键术语英文原词，并在首次出现时给出中文说明。
2. 不要漏掉重要限定条件和结论。
3. 不要过度润色，不要改变原意。
4. 只输出 JSON。
"""


def build_summary_prompt(title: str, source_name: str, category: str, article_text: str) -> str:
    trimmed = article_text[:14000]
    return f"""
请阅读下面文章，并输出一个 JSON 对象，字段必须完整存在。

文章标题: {title}
来源: {source_name}
分类: {category}

JSON schema:
{{
  "article_type": "技术实战 | 模型/产品更新 | 行业评论 | 商业分析 | 研究长文 | 资讯公告",
  "score": 0-100 的整数,
  "worth_reading": "建议细读 | 选择性阅读 | 可先跳过",
  "one_line": "一句话结论，20-40字",
  "summary": "4-6句中文摘要，直接告诉我这篇文章讲了什么",
  "key_points": ["3条关键点"],
  "why_it_matters": "这篇文章对持续学习 AI/LLM 和科技产业的人为什么重要",
  "engineering_takeaway": "如果偏技术，就写工程启发；如果偏产业，就写实际决策启发",
  "business_signal": "如果偏产业或产品竞争，就写商业信号；否则给出与产业相关的简短判断",
  "limitations": "作者可能忽略的地方、适用边界或文章局限",
  "keywords": ["3-5个关键词"],
  "recommended_action": "我接下来最适合做什么：细读原文 / 只看摘要 / 跳过即可"
}}

打分规则:
- 85-100: 高信息密度，值得优先读
- 70-84: 有价值，可以看
- 50-69: 有一点价值，但不必优先
- 0-49: 噪音偏多，可跳过

文章正文:
{trimmed}
"""


def build_translation_prompt(title: str, article_text: str) -> str:
    trimmed = article_text[:16000]
    return f"""
请把下面这篇英文文章翻译成自然、准确、适合中文技术读者阅读的中文。

输出 JSON:
{{
  "translation": "完整中文译文"
}}

要求:
1. 保留关键观点，不要遗漏。
2. 术语首次出现时保留英文原词。
3. 段落清晰，语言自然。

标题: {title}

正文:
{trimmed}
"""


def parse_json_response(text: str) -> dict:
    text = text.strip()
    if not text:
        raise ValueError("Empty LLM response")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))
