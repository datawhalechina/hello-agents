# src/agent/NewsSentimentAgent/news_tools/aggregator.py
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.agent.NewsSentimentAgent.schemas import (
    RawNewsSchema,
    SingleNewsAnalysisSchema,
    NewsSentimentResultSchema
)
from src.agent.NewsSentimentAgent.news_tools.collector import fetch_stock_news
from src.agent.NewsSentimentAgent.news_tools.llm_analyzer import analyze_single_news


def analyze_news_batch(symbol: str, limit: int = 15, force_refresh: bool = False) -> NewsSentimentResultSchema:
    """
    采集新闻 -> 并发调用大模型 -> 聚合统计 -> 返回最终 Schema
    """
    # ✅ 修复：将计时起点移到函数内部，每次调用都会重新计时
    t0 = time.time()

    result = NewsSentimentResultSchema(stock_code=symbol)

    # 1. 采集新闻
    try:
        raw_news = fetch_stock_news(symbol, limit=limit, force_refresh=force_refresh)
    except Exception as e:
        result.error_msg = f"新闻采集失败: {str(e)}"
        return result

    if not raw_news:
        result.error_msg = "未获取到任何新闻数据"
        return result

    analyzed_articles: List[SingleNewsAnalysisSchema] = []
    failed_count = 0

    # 2. 并发调用大模型（线程池，最大并发设为max_workers，防止触发 API 限流）
    print(f"开始并发分析 {len(raw_news)} 条新闻 (并发度: 3)...")

    with ThreadPoolExecutor(max_workers=3) as executor:
        # 提交所有任务
        future_to_news = {executor.submit(analyze_single_news, news): news for news in raw_news}

        # 获取结果
        for future in as_completed(future_to_news):
            news = future_to_news[future]
            try:
                analysis = future.result()
                if analysis:
                    analyzed_articles.append(analysis)
                else:
                    failed_count += 1
            except Exception as e:
                print(f"[Error] 分析新闻时发生异常: {e}")
                failed_count += 1

    result.analyzed_count = len(analyzed_articles)
    result.failed_count = failed_count

    if not analyzed_articles:
        result.error_msg = "所有新闻分析均失败"
        return result

    # 3. 聚合计算
    pos_count = sum(1 for a in analyzed_articles if a.impact_judgment == "利好")
    neg_count = sum(1 for a in analyzed_articles if a.impact_judgment == "利空")
    neu_count = len(analyzed_articles) - pos_count - neg_count

    total = len(analyzed_articles)
    result.positive_ratio = round(pos_count / total, 2)
    result.negative_ratio = round(neg_count / total, 2)
    result.neutral_ratio = round(neu_count / total, 2)

    # 加权综合得分 (简单的算术平均，后续可以换成按时间衰减)
    result.weighted_sentiment_score = round(
        sum(a.sentiment_score for a in analyzed_articles) / total, 2
    )

    # 判断整体舆情
    if result.weighted_sentiment_score > 0.2:
        result.overall_sentiment = "偏多"
    elif result.weighted_sentiment_score < -0.2:
        result.overall_sentiment = "偏空"
    else:
        result.overall_sentiment = "中性"

    # 4. 提取 Top 3 利好与利空（主 Agent 写报告直接引用）
    # 利好排序：情绪得分越高越好
    positive_news = [a for a in analyzed_articles if a.impact_judgment == "利好"]
    positive_news.sort(key=lambda x: x.sentiment_score, reverse=True)
    result.top_positive_news = positive_news[:3]

    # 利空排序：情绪得分越低（越负）越好
    negative_news = [a for a in analyzed_articles if a.impact_judgment == "利空"]
    negative_news.sort(key=lambda x: x.sentiment_score)
    result.top_negative_news = negative_news[:3]

    # 完整明细
    result.articles = analyzed_articles

    print(f"分析完成！成功: {total} 条，失败: {failed_count} 条。整体舆情: {result.overall_sentiment}")

    # ✅ 修复：使用局部变量 t0 来计算准确耗时
    print(f"⏱️ 子 Agent2 内部总耗时: {time.time() - t0:.2f} 秒")

    return result