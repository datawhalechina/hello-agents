"""
智能股票分析助手 — 资讯搜索API路由

提供金融资讯搜索、个股舆情分析、热门资讯查询接口。
"""

from fastapi import APIRouter, Query
from app.services import news_service
from app.utils.mx_http import mx_result_to_http
from app.utils.response import error_response

router = APIRouter(prefix="/news", tags=["资讯搜索"])


@router.get("/search")
async def search_news(
    query: str = Query(..., description="自然语言搜索问句"),
):
    """搜索金融资讯

    - **query**: 自然语言搜索问句，如 "人工智能板块近期新闻"、"贵州茅台最新研报"
    """
    if not query or not query.strip():
        return error_response(code=400, message="请输入搜索内容")

    result = news_service.search_news(query.strip())
    return mx_result_to_http(result)


@router.get("/sentiment/{code}")
async def get_stock_sentiment(code: str):
    """获取个股舆情分析

    根据股票代码搜索该股票相关的新闻、研报、公告，并进行分类整理。

    - **code**: 6位股票代码，如 600519（贵州茅台）、000001（平安银行）
    """
    if not code or len(code) < 4:
        return error_response(code=400, message="请输入有效的股票代码")

    result = news_service.analyze_sentiment(code)
    return mx_result_to_http(result)


@router.get("/hot")
async def get_hot_news():
    """获取当前市场热门资讯

    返回今日A股市场热点动态、北向资金流向等资讯摘要。
    """
    result = news_service.search_market_news()
    return mx_result_to_http(result)
