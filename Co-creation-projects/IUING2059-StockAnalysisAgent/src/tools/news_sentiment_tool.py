# 路径: src/tools/news_sentiment_tool.py
import json
from hello_agents.tools import Tool, ToolParameter, ToolResponse
from hello_agents.tools.errors import ToolErrorCode
from src.agent.NewsSentimentAgent.agents import NewsSentimentAgent

def _to_plain(obj):
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj

class NewsSentimentTool(Tool):
    def __init__(self, default_limit: int = 2):
        super().__init__(
            name="news_sentiment_analyzer",
            description="抓取指定 A 股股票的最新新闻，并调用大模型进行情感极性分析。输入为股票代码，如 600519。",
        )
        # 注意：这里不再传 llm，也不创建 HelloAgentsLLM
        self._agent = NewsSentimentAgent(default_limit=default_limit)

    def get_parameters(self):
        return [
            ToolParameter(
                name="stock_code",
                type="string",
                description="A 股股票代码，例如 600519",
                required=True,
            )
        ]

    def run(self, parameters):
        stock_code = (parameters or {}).get("stock_code", "").strip()
        if not stock_code:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="参数 'stock_code' 不能为空",
            )
        try:
            if hasattr(self._agent, "run"):
                result = self._agent.run(stock_code)
            elif hasattr(self._agent, "analyze"):
                result = self._agent.analyze(stock_code)
            else:
                raise AttributeError("NewsSentimentAgent 既没有 run 也没有 analyze 方法，请检查源码")

            result = _to_plain(result)
            return ToolResponse.success(
                text=json.dumps(result, ensure_ascii=False, indent=2, default=str),
                data=result,
            )
        except Exception as exc:
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=f"新闻情感分析失败: {exc}",
            )