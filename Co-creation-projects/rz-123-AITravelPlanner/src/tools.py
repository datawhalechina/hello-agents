"""
三个本地工具：景点检索、天气查询、预算测算。

为什么不用模型直接「记住」票价和天气：
  大模型的记忆会过期，也可能编造。把可验证的数据放进工具，
  模型只负责「选」和「排」，结果才可复现、可核对。

所有工具都继承 HelloAgents 的 Tool 基类：
  - name / description：模型靠这两个字段决定「什么时候调用我」
  - run(parameters)：真正干活的逻辑，输入字典、输出字符串
  - get_parameters()：声明参数，框架据此生成 function calling schema
"""

from __future__ import annotations

import hashlib                          # 生成稳定的伪随机天气（同一城市+日期结果不变）
import json                            # 工具之间用 JSON 字符串传递结构化数据
from datetime import date, timedelta   # 计算未来几天的日期
from pathlib import Path               # 定位知识库文件
from typing import Any, Dict, List

from hello_agents.tools import Tool, ToolParameter, ToolResponse

# 景点知识库固定在项目 data/ 目录下（不硬编码绝对路径，换机器也能跑）
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_attractions() -> Dict[str, List[dict]]:
    """读取景点知识库；文件缺失时返回空字典，让上层的兜底逻辑接管"""
    path = DATA_DIR / "attractions.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


class AttractionSearchTool(Tool):
    """按城市 + 关键词检索候选景点"""

    def __init__(self) -> None:
        # description 写得越具体，模型越不容易在错误的时机调用
        super().__init__(
            name="search_attractions",
            description=(
                "查询指定城市的候选景点，返回名称、类型、建议游玩时长(小时)、"
                "门票价格(元)、所在区域和一句话简介。用于规划行程前收集素材。"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="city", type="string", description="城市名，例如 杭州"),
            ToolParameter(
                name="keyword",
                type="string",
                description="可选关键词，例如 博物馆 / 美食；为空则返回全部",
                required=False,
                default="",
            ),
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        city = str(parameters.get("city") or "").strip()
        keyword = str(parameters.get("keyword") or "").strip()
        spots = _load_attractions().get(city, [])

        # 关键词同时匹配名称、类型和简介，尽量不漏掉「美食」这类描述
        if keyword:
            spots = [
                s for s in spots
                if keyword in s.get("name", "")
                or keyword in s.get("type", "")
                or keyword in s.get("desc", "")
            ]

        if not spots:
            # 返回明确空结果而不是报错，让模型可以改用其他城市或放宽条件
            empty = {"city": city, "keyword": keyword, "count": 0, "attractions": []}
            return ToolResponse.success(text=json.dumps(empty, ensure_ascii=False), data=empty)
        payload = {"city": city, "keyword": keyword, "count": len(spots), "attractions": spots}
        # 新版框架要求返回 ToolResponse：text 给模型读，data 给程序用
        return ToolResponse.success(text=json.dumps(payload, ensure_ascii=False), data=payload)


class WeatherTool(Tool):
    """查询某城市某天的天气（演示用确定性数据，不依赖外部 Key）"""

    # 天气状况候选集，按哈希取模选择
    _CONDITIONS = ["晴", "多云", "阴", "小雨"]

    def __init__(self) -> None:
        super().__init__(
            name="get_weather",
            description=(
                "查询指定城市指定日期的天气，返回天气状况、最低温、最高温与出行提示。"
                "日期格式 YYYY-MM-DD；不传日期时默认从明天开始。"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="city", type="string", description="城市名，例如 杭州"),
            ToolParameter(
                name="date",
                type="string",
                description="日期 YYYY-MM-DD，可留空",
                required=False,
                default="",
            ),
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        city = str(parameters.get("city") or "").strip()
        day = str(parameters.get("date") or "").strip() or str(date.today() + timedelta(days=1))

        # 用 md5 前 8 位做种子：同一城市同一天永远得到同样的天气，便于复现和测试
        seed = int(hashlib.md5(f"{city}{day}".encode("utf-8")).hexdigest()[:8], 16)
        condition = self._CONDITIONS[seed % len(self._CONDITIONS)]
        low = 10 + seed % 12               # 最低温 10~21℃
        high = low + 6 + seed % 5          # 最高温比最低温高 6~10℃

        payload = {
            "city": city,
            "date": day,
            "condition": condition,
            "temp_low": low,
            "temp_high": high,
            "tip": "有雨请带伞" if condition == "小雨" else "适合户外活动",
            "data_source": "demo",     # 明确标注：这不是实时天气
        }
        return ToolResponse.success(text=json.dumps(payload, ensure_ascii=False), data=payload)


class BudgetCalculatorTool(Tool):
    """把行程开销拆成交通/住宿/餐饮/门票四项并汇总"""

    def __init__(self) -> None:
        super().__init__(
            name="calc_budget",
            description=(
                "按人数与天数计算旅行预算明细：往返交通、住宿、餐饮、门票，"
                "并返回总价与人均。所有金额单位为元。"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="days", type="integer", description="行程天数"),
            ToolParameter(name="people", type="integer", description="出行人数"),
            ToolParameter(name="transport", type="number", description="每人往返交通费"),
            ToolParameter(name="hotel_per_night", type="number", description="每晚住宿费（按一间房计）"),
            ToolParameter(name="food_per_day", type="number", description="每人每天餐饮费"),
            ToolParameter(name="tickets", type="number", description="门票合计（全体人员）"),
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        # 统一转数字并兜底为 0，避免模型传空字符串导致计算崩溃
        days = int(parameters.get("days") or 0)
        people = max(int(parameters.get("people") or 1), 1)
        transport = float(parameters.get("transport") or 0)
        hotel = float(parameters.get("hotel_per_night") or 0)
        food = float(parameters.get("food_per_day") or 0)
        tickets = float(parameters.get("tickets") or 0)

        # 住宿按「晚数 = 天数 - 1」估算，房间数按两人一间向上取整
        nights = max(days - 1, 0)
        rooms = (people + 1) // 2

        transport_total = transport * people
        hotel_total = hotel * nights * rooms
        food_total = food * days * people
        total = transport_total + hotel_total + food_total + tickets

        payload = {
            "transport": round(transport_total, 2),
            "hotel": round(hotel_total, 2),
            "food": round(food_total, 2),
            "tickets": round(tickets, 2),
            "total": round(total, 2),
            "per_person": round(total / people, 2),
        }
        return ToolResponse.success(text=json.dumps(payload, ensure_ascii=False), data=payload)


def build_tools() -> List[Tool]:
    """一次性创建全部工具，供调研/预算 Agent 使用"""
    return [AttractionSearchTool(), WeatherTool(), BudgetCalculatorTool()]
