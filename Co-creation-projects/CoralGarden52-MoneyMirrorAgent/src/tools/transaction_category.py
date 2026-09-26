"""Rule-first transaction categorization with durable merchant corrections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from ..models import Transaction

CATEGORIES = ("餐饮", "交通", "娱乐", "购物", "住房", "学习", "健身", "订阅", "医疗", "其他")


@dataclass(slots=True)
class CategoryResult:
    category: str
    confidence: float
    source: str


class TransactionCategoryTool:
    rules: dict[str, tuple[str, ...]] = {
        "住房": ("房租", "租金", "物业", "水电", "燃气", "电费", "宽带"),
        "订阅": ("netflix", "spotify", "爱奇艺", "腾讯视频", "优酷", "b站大会员", "网易云音乐", "qq音乐", "喜马拉雅", "会员", "订阅", "icloud", "云盘"),
        "餐饮": ("外卖", "美团", "饿了么", "餐厅", "饭店", "火锅", "烧烤", "奶茶", "咖啡", "星巴克", "便利店", "早餐", "午餐", "晚餐"),
        "交通": ("地铁", "公交", "滴滴", "打车", "高铁", "火车", "加油", "停车", "共享单车", "单车"),
        "娱乐": ("电影", "影院", "演唱会", "游戏", "steam", "剧本杀", "桌游", "livehouse", "音乐节", "门票"),
        "购物": ("淘宝", "天猫", "京东", "拼多多", "商场", "优衣库", "服饰", "鞋", "数码", "商城", "超市", "礼物"),
        "学习": ("课程", "书店", "图书", "学习", "考试", "培训", "语言", "知识", "论文"),
        "健身": ("健身", "瑜伽", "游泳", "跑步", "keep", "运动", "球馆"),
        "医疗": ("医院", "药房", "药店", "体检", "医疗"),
    }

    def classify(self, transaction: Transaction, memory_lookup: Callable[[str], str | None] | None = None) -> CategoryResult:
        if transaction.kind == "income":
            return CategoryResult("收入", 1.0, "income_rule")
        if memory_lookup:
            remembered = memory_lookup(transaction.merchant)
            if remembered in CATEGORIES:
                return CategoryResult(remembered, 1.0, "memory")
        haystack = f"{transaction.merchant} {transaction.note}".lower()
        for category, keywords in self.rules.items():
            if any(keyword.lower() in haystack for keyword in keywords):
                return CategoryResult(category, 0.92, "keyword_rule")
        return CategoryResult("其他", 0.25, "fallback")

    def apply(self, transactions: Iterable[Transaction], memory_lookup: Callable[[str], str | None] | None = None) -> list[Transaction]:
        result: list[Transaction] = []
        for transaction in transactions:
            classified = self.classify(transaction, memory_lookup)
            transaction.category = classified.category
            transaction.category_confidence = classified.confidence
            result.append(transaction)
        return result
