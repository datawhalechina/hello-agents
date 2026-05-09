"""
股票数据文件缓存服务 — 每只股票的所有数据存储到本地文件

每次获取数据时优先从本地文件读取，未命中或过期才调用接口。
支持 grep 风格的文件内容搜索。
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Any

from app.config import settings

logger = logging.getLogger(__name__)

_cache_lock = threading.Lock()

# 缓存根目录
_STOCK_CACHE_ROOT = settings.DATA_DIR / "stock_cache"

# 各数据类型的文件名
_DATA_TYPE_FILES = {
    "quote": "quote.json",
    "financial": "financial.json",
    "profile": "profile.json",
    "holders": "holders.json",
    "sentiment": "sentiment.json",
    "news": "news.json",
}

# 当日缓存有效期（同一只股票同一天只调一次接口）
_TODAY = date.today().isoformat()


class StockFileCache:
    """股票数据文件缓存"""

    def __init__(self):
        _STOCK_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
        self._index_file = _STOCK_CACHE_ROOT / "_index.json"
        self._index: dict = {}
        self._load_index()

    # ---- 索引管理 ----

    def _load_index(self):
        """加载主索引"""
        try:
            if self._index_file.exists():
                self._index = json.loads(self._index_file.read_text(encoding="utf-8"))
                logger.debug("文件缓存索引已加载: %d 条", len(self._index))
        except Exception:
            self._index = {}

    def _save_index(self):
        """保存主索引"""
        try:
            self._index_file.write_text(json.dumps(self._index, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("保存缓存索引失败: %s", e)

    def _stock_dir(self, stock_code: str) -> Path:
        clean = stock_code.strip().upper()
        d = _STOCK_CACHE_ROOT / clean
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _data_file(self, stock_code: str, data_type: str) -> Path:
        filename = _DATA_TYPE_FILES.get(data_type, f"{data_type}.json")
        return self._stock_dir(stock_code) / filename

    def _update_index(self, stock_code: str, data_type: str):
        code = stock_code.strip().upper()
        if code not in self._index:
            self._index[code] = {"data_types": [], "cached_at": datetime.now().isoformat()}
        if data_type not in self._index[code]["data_types"]:
            self._index[code]["data_types"].append(data_type)
        self._index[code]["cached_at"] = datetime.now().isoformat()

    # ---- 读写操作 ----

    def get(self, stock_code: str, data_type: str, max_age_hours: int = 24) -> Optional[dict]:
        """
        从文件缓存读取数据

        Args:
            stock_code: 股票代码
            data_type: 数据类型 (quote/financial/profile/holders/sentiment/news)
            max_age_hours: 最大有效时长（小时），超过则视为过期

        Returns:
            缓存数据字典，未命中或过期返回 None
        """
        filepath = self._data_file(stock_code, data_type)
        if not filepath.exists():
            return None

        # 检查文件时效
        mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600
        file_date = mtime.strftime("%Y-%m-%d")

        # 当日数据直接返回（不限小时数）
        if file_date == _TODAY:
            pass
        elif age_hours > max_age_hours:
            logger.debug("缓存过期: %s/%s (%.1f小时前)", stock_code, data_type, age_hours)
            return None

        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            logger.debug("文件缓存命中: %s/%s", stock_code, data_type)
            return data
        except Exception as e:
            logger.warning("读取缓存文件失败 %s: %s", filepath, e)
            return None

    def set(self, stock_code: str, data_type: str, data: dict) -> bool:
        """
        将数据写入文件缓存

        Args:
            stock_code: 股票代码
            data_type: 数据类型
            data: 数据字典

        Returns:
            是否写入成功
        """
        filepath = self._data_file(stock_code, data_type)
        try:
            wrapper = {
                "stock_code": stock_code,
                "data_type": data_type,
                "cached_at": datetime.now().isoformat(),
                "cache_date": _TODAY,
                "data": data,
            }
            filepath.write_text(json.dumps(wrapper, ensure_ascii=False, indent=2), encoding="utf-8")
            self._update_index(stock_code, data_type)
            self._save_index()
            logger.debug("文件缓存写入: %s/%s", stock_code, data_type)
            return True
        except Exception as e:
            logger.warning("写入缓存文件失败 %s: %s", filepath, e)
            return False

    def has(self, stock_code: str, data_type: str) -> bool:
        """检查是否存在有效缓存"""
        filepath = self._data_file(stock_code, data_type)
        if not filepath.exists():
            return False
        mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
        return mtime.strftime("%Y-%m-%d") == _TODAY

    # ---- grep 风格搜索 ----

    def grep_search(self, keyword: str, data_type: Optional[str] = None) -> list[dict]:
        """
        在所有缓存文件中搜索关键词（类似 grep）

        Args:
            keyword: 搜索关键词
            data_type: 限定数据类型，None 为全部

        Returns:
            匹配结果列表 [{stock_code, data_type, file_path, line: str, ...}]
        """
        results = []
        keyword_lower = keyword.lower()

        # 先查索引快速定位候选股票
        candidates = []
        for code, info in self._index.items():
            if keyword_lower in code.lower():
                candidates.append(code)
                continue
            types = info.get("data_types", [])
            if data_type and data_type not in types:
                continue
            candidates.append(code)

        # 对候选股票目录做内容 grep
        for code in candidates:
            stock_dir = self._stock_dir(code)
            if not stock_dir.exists():
                continue

            for fname in stock_dir.glob("*.json"):
                dtype = fname.stem
                if data_type and dtype != data_type:
                    continue

                try:
                    content = fname.read_text(encoding="utf-8")
                    if keyword_lower in content.lower():
                        # 提取匹配行
                        lines = content.split("\n")
                        matched_lines = [l.strip() for l in lines if keyword_lower in l.lower()]
                        results.append({
                            "stock_code": code,
                            "data_type": dtype,
                            "file_path": str(fname),
                            "matched_lines": matched_lines[:10],
                            "match_count": len(matched_lines),
                            "cached_at": datetime.fromtimestamp(fname.stat().st_mtime).isoformat(),
                        })
                except Exception:
                    continue

        return results

    def get_stock_codes(self) -> list[str]:
        """获取所有已缓存的股票代码"""
        return list(self._index.keys())

    def get_stock_data_types(self, stock_code: str) -> list[str]:
        """获取某股票已缓存的数据类型"""
        info = self._index.get(stock_code.upper(), {})
        return info.get("data_types", [])

    def clear_stock_cache(self, stock_code: Optional[str] = None):
        """清除缓存"""
        if stock_code:
            stock_dir = self._stock_dir(stock_code)
            for f in stock_dir.glob("*.json"):
                try:
                    f.unlink()
                except Exception:
                    pass
            code = stock_code.upper()
            self._index.pop(code, None)
            self._save_index()
        else:
            for f in _STOCK_CACHE_ROOT.glob("**/*.json"):
                try:
                    f.unlink()
                except Exception:
                    pass
            self._index.clear()
            self._save_index()

    def get_stats(self) -> dict:
        """获取缓存统计"""
        total_files = sum(1 for _ in _STOCK_CACHE_ROOT.glob("**/*.json"))
        total_size = sum(f.stat().st_size for f in _STOCK_CACHE_ROOT.glob("**/*.json") if f.is_file())
        return {
            "stock_count": len(self._index),
            "total_files": total_files,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "cache_root": str(_STOCK_CACHE_ROOT),
        }


_stock_cache_instance: Optional[StockFileCache] = None


def get_stock_file_cache() -> StockFileCache:
    """获取 StockFileCache 全局单例"""
    global _stock_cache_instance
    if _stock_cache_instance is None:
        with _cache_lock:
            if _stock_cache_instance is None:
                _stock_cache_instance = StockFileCache()
    return _stock_cache_instance
