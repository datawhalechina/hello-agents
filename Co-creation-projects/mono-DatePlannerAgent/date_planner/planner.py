# -*- coding: utf-8 -*-
"""
DatePlannerAgent 方案层：需求采集 + 高德调研编排 + 8 段式报告输出。

说明：本包不依赖任何大模型 Key，负责“数据采集 + 结构化输出”；
若接入上层 LLM Agent（如 HelloAgents 的 SimpleAgent / ReAct），
可直接复用本包的数据方法，把报告模板交给大模型填充。
"""
from .amap_client import AMapClient, pretty_poi

# 分组询问模板（适合上层 Agent 或命令行交互）
QUESTION_GROUPS = [
    {
        "group": "第一组｜基本信息",
        "questions": [
            "哪个城市/地区？",
            "大概从哪里出发？",
            "哪一天、几点见面？",
            "两人预算多少？",
            "交通方式？（步行/公交/打车/电动车）",
        ],
    },
    {
        "group": "第二组｜关系和氛围",
        "questions": [
            "第一次约会还是已经比较熟？",
            "想要：安静聊天 / 互动体验 / 浪漫氛围 / 轻松随意？",
            "室内、室外还是都可以？",
            "有没有不喜欢的活动？",
        ],
    },
    {
        "group": "第三组｜活动偏好",
        "questions": [
            "从下面选（可多选）：展览/美术馆；咖啡/甜品；手工体验；水族馆/动物园；公园/江边/夜景；餐厅；电影/演出；桌游/保龄球等互动活动。",
        ],
    },
]

REPORT_TEMPLATE = """# 约会方案调研报告

## 1. 用户需求总结
{summary}

## 2. 推荐活动方向
{direction}

## 3. 本次调研到的关键事实
{facts}

## 4. 推荐路线（候选）
{routes}

## 5. 具体时间与交通
{timeline}

## 6. 需要提前确认的事项
{todos}

## 7. 备用方案
{fallback}

## 8. 省流版（100 字内）
{short}
"""


class DatePlanner:
    """约会方案编排器：输入需求，输出结构化调研结果。"""

    def __init__(self, key=None):
        self.client = AMapClient(key)

    # ---------- 数据调研 ----------
    def search_pois(self, keywords, city="", limit=5):
        """关键词搜索候选 POI（自动过滤无坐标项）。"""
        pois = self.client.text_search(keywords, city=city, offset=limit)
        return [p for p in pois if p.get("location")]

    def pick_best(self, pois):
        """按评分降序挑候选（评分缺失排在最后）。"""
        def score(p):
            try:
                return float(p.get("rating") or 0)
            except (TypeError, ValueError):
                return 0
        return sorted(pois, key=score, reverse=True)

    def leg(self, origin_loc, dest_loc, type_="2"):
        """两地点间骑行距离，返回可读文本。"""
        r = self.client.distance(origin_loc, dest_loc, type_=type_)
        return f"{r['km']} km / 约 {r['min']} 分钟" if r else "需要确认"

    def weather_of(self, city, date_str=None):
        """查天气，返回当日可读文本。"""
        casts = self.client.weather(city)
        for c in casts:
            if date_str is None or c.get("date") == date_str:
                return (f"{c.get('date','')} {c.get('week','')} | {c.get('dayweather','需要确认')}/"
                        f"{c.get('nightweather','需要确认')} | 白天{c.get('daytemp','?')}° "
                        f"夜间{c.get('nighttemp','?')}° | {c.get('daywind','')}风"
                        f"{c.get('daypower','')}")
        return "需要确认（高德未返回该日期预报）"

    # ---------- 输出 ----------
    def build_report(self, summary, direction, facts, routes,
                     timeline, todos, fallback, short):
        """按 8 段式模板生成报告文本。"""
        return REPORT_TEMPLATE.format(
            summary=summary, direction=direction, facts=facts,
            routes=routes, timeline=timeline, todos=todos,
            fallback=fallback, short=short,
        )

    def demo(self, city="北京", keywords="西餐厅"):
        """快速演示：搜索 + 排序 + 打印候选（不发报告，仅展示数据流）。"""
        print(f"== 演示: {city} 搜索「{keywords}」 ==")
        pois = self.search_pois(keywords, city=city)
        for i, p in enumerate(self.pick_best(pois)[:5], 1):
            print(pretty_poi(p, index=f"[{i}]"))
        if pois:
            first = pois[0]
            print("\n== 详情演示（第一个候选） ==")
            detail = self.client.detail(first["id"])
            print(pretty_poi(detail, index="[D]"))
        print("\n== 天气演示 ==")
        print(self.weather_of(city))
        return pois


if __name__ == "__main__":
    import sys
    kw = sys.argv[1] if len(sys.argv) > 1 else "西餐厅"
    DatePlanner().demo(keywords=kw)
