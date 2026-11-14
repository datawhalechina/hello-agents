# src/agent/NewsSentimentAgent/agents/news_agent.py
from src.agent.NewsSentimentAgent.news_tools import analyze_news_batch
from src.agent.NewsSentimentAgent.schemas import NewsSentimentResultSchema


class NewsSentimentAgent:
    """
    子 Agent2：新闻舆情采集与情感分析 Agent
    """

    def __init__(self, default_limit: int = 15):
        # Agent 的基础属性，方便主 Agent 打印和识别
        self.name = "NewsSentimentAgent"
        self.description = "负责采集个股新闻，调用大模型进行情感分析和利好利空判断，输出结构化舆情汇总。"
        self.default_limit = default_limit

    def run(self, symbol: str, limit: int = None, force_refresh: bool = False) -> NewsSentimentResultSchema:
        """
        主 Agent 调用的唯一入口。
        :param symbol: 股票代码，如 "000001"
        :param limit: 限制分析的新闻条数（若不传，使用默认配置）
        :param force_refresh: 是否强制刷新（忽略本地缓存重新采集和分析）
        :return: 结构化的舆情分析结果 NewsSentimentResultSchema
        """
        limit = limit if limit is not None else self.default_limit
        print(f"\n[{self.name}] 🚀 启动任务: 正在分析 {symbol} 的新闻舆情 (Limit={limit})...")

        # 调用底层工具链（采集 -> 并发LLM -> 聚合）
        result = analyze_news_batch(symbol=symbol, limit=limit, force_refresh=force_refresh)

        # 简单的状态日志（使用 getattr 兜底，防止 Schema 里没定义 error_msg 时崩溃）
        err = getattr(result, 'error_msg', None)
        if err:
            print(f"[{self.name}] ⚠️ 任务完成（有异常）: {err}")
        else:
            print(f"[{self.name}] ✅ 任务完成，整体舆情: {result.overall_sentiment}")

        return result