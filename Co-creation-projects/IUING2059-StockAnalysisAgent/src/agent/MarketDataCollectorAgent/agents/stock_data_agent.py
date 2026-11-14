# agents/stock_data_agent.py
import time
import random
from ..stock_tools.quote import fetch_quote
from ..stock_tools.fundamental import fetch_fundamental
from ..stock_tools.valuation import fetch_valuation
from ..stock_tools.technical import fetch_technical
from ..stock_tools._common import trade_status, timeout


class StockDataAgent:
    """
    专职子 Agent：个股数据采集 Agent
    对标 NewsSentimentAgent 的架构，对外提供标准化 run() 接口。
    """

    def __init__(self):
        # Agent 基础属性，方便主 Agent 识别和打印
        self.name = "StockDataAgent"
        self.description = "负责获取单只 A 股的行情、估值、技术面、基本面数据。"

        # 原有配置原样保留
        self._dim_map = {
            "quote": fetch_quote,
            "valuation": fetch_valuation,
            "technical": fetch_technical,
            "fundamental": fetch_fundamental,
        }
        self._dim_timeout = {
            "quote": 15,
            "valuation": 15,
            "technical": 20,
            "fundamental": 30,
        }

    def run(self, stock_code: str, dims: list[str]) -> dict:
        """
        主 Agent 调用的唯一入口（标准化接口）。
        以下代码逻辑与你原来的 run_stock_data_agent 函数完全一致，未做任何修改。
        """
        data, errors, meta = {}, [], {}

        for dim in dims:
            fn = self._dim_map.get(dim)
            if not fn:
                errors.append(f"unknown_dim: {dim}")
                continue

            max_attempts = 2  # 方案三：每个维度最多尝试 2 次
            for attempt in range(max_attempts):
                try:
                    # 方案三：加入 0.5 到 1.5 秒的随机休眠，模拟人工操作，降低被封 IP 的概率
                    time.sleep(random.uniform(0.5, 1.5))

                    with timeout(self._dim_timeout.get(dim, 15)):
                        result = fn(stock_code).model_dump(exclude_none=True)

                    data[dim] = result
                    if dim == "quote":
                        meta["trade_status"] = trade_status()

                    # 如果成功获取，直接跳出重试循环，进入下一个维度
                    break

                except Exception as e:
                    if attempt == max_attempts - 1:
                        # 如果是最后一次尝试依然失败，记录错误
                        errors.append(f"{dim}: {type(e).__name__}: {e}")
                    else:
                        # 如果不是最后一次失败，等待 1 秒后重试
                        time.sleep(1.0)

        return {"stock_code": stock_code, "data": data, "errors": errors, "meta": meta}


# 保留原函数名作为兼容（可选，方便旧代码直接调用，实际由 Tool 层调用类）
def run_stock_data_agent(stock_code: str, dims: list[str]) -> dict:
    """兼容原函数的包装器，内部调用 StockDataAgent.run()"""
    agent = StockDataAgent()
    return agent.run(stock_code, dims)