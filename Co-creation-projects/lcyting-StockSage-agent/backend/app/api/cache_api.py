"""
股票文件缓存 API — grep搜索、缓存管理、数据统计
"""

from fastapi import APIRouter, Query
from app.services.stock_file_cache import get_stock_file_cache
from app.utils.response import success_response, error_response

router = APIRouter(prefix="/cache", tags=["文件缓存"])


@router.get("/search")
async def grep_search(
    keyword: str = Query(..., description="搜索关键词"),
    data_type: str = Query(None, description="限定数据类型: quote/financial/profile/holders/sentiment"),
):
    """grep 风格搜索缓存文件内容

    在所有已缓存的股票数据文件中搜索关键词，返回匹配结果。
    """
    fc = get_stock_file_cache()
    results = fc.grep_search(keyword, data_type)
    return success_response(data={
        "keyword": keyword,
        "total_matches": len(results),
        "results": results,
    })


@router.get("/stock/{stock_code}")
async def get_stock_cache_info(stock_code: str):
    """查询某股票的缓存状态"""
    fc = get_stock_file_cache()
    data_types = fc.get_stock_data_types(stock_code)
    return success_response(data={
        "stock_code": stock_code,
        "cached_types": data_types,
        "has_quote": "quote" in data_types,
        "has_financial": "financial" in data_types,
        "has_profile": "profile" in data_types,
        "has_holders": "holders" in data_types,
        "has_sentiment": "sentiment" in data_types,
    })


@router.get("/stats")
async def cache_stats():
    """获取缓存统计信息"""
    fc = get_stock_file_cache()
    return success_response(data=fc.get_stats())


@router.delete("/clear")
async def clear_cache(
    stock_code: str = Query(None, description="指定股票代码，不传则清空全部"),
):
    """清除文件缓存"""
    fc = get_stock_file_cache()
    fc.clear_stock_cache(stock_code)
    return success_response(message=f"缓存已清除{'(' + stock_code + ')' if stock_code else ''}")


@router.get("/list")
async def list_cached_stocks():
    """列出所有已缓存的股票代码"""
    fc = get_stock_file_cache()
    codes = fc.get_stock_codes()
    result = []
    for code in codes:
        types = fc.get_stock_data_types(code)
        result.append({"code": code, "data_types": types})
    return success_response(data={"stocks": result, "total": len(result)})
