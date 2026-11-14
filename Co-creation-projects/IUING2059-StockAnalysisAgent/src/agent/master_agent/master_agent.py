# src/agent/master_agent/master_agent.py
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# 引入 hello_agents 的 LLM
from hello_agents import HelloAgentsLLM

# 导入我们刚刚封装好的两个 Tool，而不是原来的原生 Agent
from src.tools import MarketDataTool, NewsSentimentTool

# 导入 Prompt 保持不变
from src.agent.master_agent.prompts import MASTER_SYSTEM_PROMPT, build_master_user_prompt

load_dotenv()


class StockAnalysisMaster:
    def __init__(self):
        self.name = "StockAnalysisMaster"

        # 实例化 Tool
        self.market_tool = MarketDataTool()
        self.news_tool = NewsSentimentTool(default_limit=2)  # 保持你的防卡死技巧

        # 使用 HelloAgentsLLM 替代 OpenAI 客户端
        self.llm = HelloAgentsLLM()

    def run(self, symbol: str) -> str:
        print(f"\n[{self.name}] 🚀 启动综合分析任务，目标股票: {symbol}")
        start_time = time.time()

        market_data = None
        news_data = None

        print(f"[{self.name}] 正在并发调度子 Agent (Tools)...")

        with ThreadPoolExecutor(max_workers=2) as executor:
            # 并发调用 Tool 的 run 方法，传入参数字典
            future_market = executor.submit(self.market_tool.run, {"stock_code": symbol})
            future_news = executor.submit(self.news_tool.run, {"stock_code": symbol})

            # 获取结果
            try:
                resp_market = future_market.result()
                # 检查 Tool 返回状态
                if str(resp_market.status) == "ToolStatus.SUCCESS" or getattr(resp_market.status, "name",
                                                                              "") == "SUCCESS":
                    market_data = resp_market.data
                else:
                    print(f"❌ 子 Tool1(行情) 调用失败: {resp_market.message}")
            except Exception as e:
                print(f"❌ 子 Tool1(行情) 调用异常: {e}")

            try:
                resp_news = future_news.result()
                if str(resp_news.status) == "ToolStatus.SUCCESS" or getattr(resp_news.status, "name", "") == "SUCCESS":
                    news_data = resp_news.data
                else:
                    print(f"❌ 子 Tool2(舆情) 调用失败: {resp_news.message}")
            except Exception as e:
                print(f"❌ 子 Tool2(舆情) 调用异常: {e}")

        print(f"[{self.name}] ✅ 子 Tool 调度完毕，耗时 {time.time() - start_time:.2f} 秒。")

        # 2. 数据格式化处理 —— 兼容 Pydantic 对象和普通 dict
        if market_data:
            if hasattr(market_data, 'model_dump_json'):
                market_json = market_data.model_dump_json(indent=2)
            else:
                market_json = json.dumps(market_data, ensure_ascii=False, indent=2, default=str)
        else:
            market_json = "无数据"

        if news_data:
            if hasattr(news_data, 'model_dump_json'):
                news_json = news_data.model_dump_json(indent=2)
            else:
                news_json = json.dumps(news_data, ensure_ascii=False, indent=2, default=str)
        else:
            news_json = "无数据"

        # 3. 组装 Prompt 并调用大模型生成报告
        print(f"[{self.name}] 🧠 正在让大模型撰写最终投资研报...")
        user_prompt = build_master_user_prompt(symbol, market_json, news_json)

        user_prompt += "\n\n【系统提示】如果数据中缺少股票名称，请根据股票代码自行推断并补全股票简称（例如 600519 对应贵州茅台）。"

        try:
            messages = [
                {"role": "system", "content": MASTER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
            # 使用 HelloAgentsLLM 的 invoke 方法
            response = self.llm.invoke(messages)

            # 兼容不同框架的返回格式
            if hasattr(response, "content"):
                report = response.content
            else:
                report = str(response)

        except Exception as e:
            return f"❌ 生成最终研报失败: {e}"

        total_time = time.time() - start_time
        print(f"[{self.name}] 🎉 研报生成完毕！总耗时: {total_time:.2f} 秒。")

        return report