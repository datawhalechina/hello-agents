# src/agent/NewsSentimentAgent/news_tools/llm_analyzer.py
import os
import json
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from pydantic import ValidationError

# 显式定位 .env，避免从别的目录启动时找不到
load_dotenv(dotenv_path=Path(__file__).resolve().parents[3] / ".env")

# 强行清空系统代理，防止请求被劫持挂起（必须在创建 client 前）
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["ALL_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""
os.environ["all_proxy"] = ""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from openai import RateLimitError, APITimeoutError, APIConnectionError

from src.agent.NewsSentimentAgent.schemas import RawNewsSchema, SingleNewsAnalysisSchema

# 忽略系统代理的 httpx client，并设置连接/读取超时
http_client = httpx.Client(
    trust_env=False,
    timeout=httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0),
)

llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL_ID"),
    temperature=0.0,
    api_key=os.getenv("LLM_API_KEY"),        # 新参数名
    base_url=os.getenv("LLM_BASE_URL"),      # 新参数名
    timeout=15.0,                        # 整体请求超时
    max_retries=0,                       # 底层不重试，由外层统一控制
    max_tokens=300,                      # 限制输出，防 thinking 模型跑飞
    http_client=http_client,
)

SYSTEM_PROMPT = """你是一个资深的股票市场金融分析师，擅长解读新闻舆情对个股股价的潜在影响。

你的任务是分析用户提供的新闻标题和摘要，并严格输出纯 JSON 格式的数据（不要包含任何 Markdown 的 ```json 标记，也不要有任何解释性文字）。

必须遵循以下 JSON 结构：
{
  "title": "新闻标题",
  "sentiment_label": "positive | negative | neutral (三选一)",
  "sentiment_score": 浮点数 (-1.0 到 1.0 之间，-1.0极度利空，1.0极度利好，0.0中性),
  "impact_judgment": "利好 | 利空 | 中性 (三选一)",
  "impact_reason": "一句话说明判断依据 (不超过20字)",
  "one_line_summary": "新闻的一句话中文摘要 (不超过30字)",
  "confidence": 浮点数 (0.0 到 1.0 之间)
}

【注意】
1. sentiment_label 代表文本本身的情绪。
2. impact_judgment 代表对股价的实际传导预期（两者可以不同，例如"公司被罚款"情绪负面，但如果罚款金额极小，对股价可能判定为中性甚至利空出尽）。
3. 如果新闻内容与目标个股不直接相关（例如大盘指数新闻），请判定为 neutral 和 中性，并在 reason 中说明。
4. 只输出 JSON，不要输出任何思考过程、解释或 Markdown 标记。
"""


def _clean_json_response(text: str) -> str:
    """清洗大模型返回的文本，提取纯净的 JSON 字符串"""
    text = text.strip()
    # 兼容 ```json / ``` 代码块
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    # 兜底：截取第一个 { 到最后一个 } 之间的内容
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return text


def _extract_text(content) -> str:
    """兼容 LangChain 返回 str 或 list[dict] 两种 content 形态"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


def analyze_single_news(
    news_item: RawNewsSchema, max_retries: int = 3
) -> SingleNewsAnalysisSchema | None:
    user_content = f"标题: {news_item.title}\n"
    if news_item.content:
        user_content += f"摘要: {news_item.content}\n"

    for attempt in range(max_retries):
        try:
            start_t = time.time()

            response = llm.invoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=user_content),
                ]
            )

            end_t = time.time()
            print(f"  [LLM耗时] {end_t - start_t:.2f}s -> {news_item.title[:15]}")

            raw_text = _extract_text(response.content)
            clean_text = _clean_json_response(raw_text)
            data = json.loads(clean_text)
            return SingleNewsAnalysisSchema(**data)

        except RateLimitError:
            wait = 5 * (attempt + 1)   # 5s, 10s, 15s 递增
            print(f"  ⚠️ 触发限流，{wait}s 后重试 ({news_item.title[:10]})")
            time.sleep(wait)
        except (APITimeoutError, APIConnectionError) as e:
            wait = 2 * (attempt + 1)
            print(f"  ⏱️ 超时/连接异常，{wait}s 后重试: {e}")
            time.sleep(wait)
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"  ❌ 解析失败 ({news_item.title[:10]}): {e}")
            # 解析失败通常重试也没用，但 thinking 模型偶发，可保留一次
            time.sleep(1)
        except Exception as e:
            print(f"  ❌ 异常 ({news_item.title[:10]}): {e}")
            time.sleep(1)

    return None