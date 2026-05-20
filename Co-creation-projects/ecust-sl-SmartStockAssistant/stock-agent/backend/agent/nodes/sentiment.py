# backend/agent/nodes/sentiment.py
import json
from openai import AsyncOpenAI

from agent.state import StockAnalysisState
from app.config import settings


def _build_sentiment_prompt(news_data: list, symbol: str) -> str:
    """构建情感分析 prompt"""
    news_text = json.dumps(news_data[:10], ensure_ascii=False, indent=2)
    return f"""
请对以下关于股票 {symbol} 的新闻数据进行情感分析。

## 新闻数据
{news_text}

请严格按照以下 JSON 格式返回，不要输出任何其他内容：
{{
  "score": 0.65,
  "label": "positive",
  "reason": "主要利好因素说明",
  "key_factors": ["因素1", "因素2"]
}}

评分规则：
- score 范围 -1.0（极度悲观）到 1.0（极度乐观）
- label: "positive"(>0.2) | "neutral"(-0.2~0.2) | "negative"(<-0.2)
- reason: 一句话总结主要情感驱动因素
- key_factors: 最多3个关键因素
""".strip()


def _parse_sentiment_response(content: str) -> dict:
    """解析 Qwen 返回的 JSON，容错处理"""
    try:
        # 清理可能的 markdown 代码块
        clean = content.strip()
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except Exception:
        # 解析失败时返回中性默认值
        return {
            "score": 0.0,
            "label": "neutral",
            "reason": "情感分析解析失败，默认中性",
            "key_factors": [],
        }


async def sentiment_node(state: StockAnalysisState) -> StockAnalysisState:
    """
    情感分析节点：调用 Qwen 对新闻数据打分。
    无新闻数据时返回中性得分，不阻断流程。
    返回 delta（仅 sentiment_* 字段），避免并行写冲突。
    """
    # mock 模式
    if settings.use_mock_data:
        return {
            "sentiment_score": 0.65,
            "sentiment_label": "positive",
            "sentiment_reason": "公司业绩超预期，市场情绪偏乐观",
            "sentiment_factors": ["季报超预期", "机构增持", "行业政策利好"],
        }

    # 无新闻数据时跳过
    news_data = state.get("news_data") or []
    if not news_data:
        return {
            "sentiment_score": 0.0,
            "sentiment_label": "neutral",
            "sentiment_reason": "暂无新闻数据，情感得分默认中性",
            "sentiment_factors": [],
        }

    client = AsyncOpenAI(
        api_key=settings.modelscope_api_key,
        base_url=settings.modelscope_base_url,
    )

    try:
        response = await client.chat.completions.create(
            model=settings.qwen_sentiment_model,
            messages=[
                {
                    "role": "system",
                    "content": "你是专业的金融情感分析师，只返回 JSON 格式数据，不输出任何其他内容。",
                },
                {
                    "role": "user",
                    "content": _build_sentiment_prompt(news_data, state["symbol"]),
                },
            ],
            temperature=0.1,   # 情感分析要求稳定输出
            max_tokens=300,
        )
        if not response.choices:
            # modelscope 偶尔会返回空 choices（限流/排队），降级为中性
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "sentiment_reason": "情感模型暂时不可用，默认中性",
                "sentiment_factors": [],
            }
        result = _parse_sentiment_response(
            response.choices[0].message.content
        )
        return {
            "sentiment_score": float(result.get("score", 0.0)),
            "sentiment_label": result.get("label", "neutral"),
            "sentiment_reason": result.get("reason", ""),
            "sentiment_factors": result.get("key_factors", []),
        }

    except Exception as e:
        return {
            "sentiment_score": 0.0,
            "sentiment_label": "neutral",
            "sentiment_reason": f"情感分析失败：{e}",
            "sentiment_factors": [],
        }