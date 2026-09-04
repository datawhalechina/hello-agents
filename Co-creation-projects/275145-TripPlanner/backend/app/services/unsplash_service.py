# backend/app/services/unsplash_service.py
import requests
from typing import Optional, List, Dict
from functools import lru_cache
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# 占位图片URL（当无法获取图片时使用）
DEFAULT_PLACEHOLDER_IMAGES = [
    "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1523906834658-6e24ef2386f9?w=800&h=600&fit=crop"
]


class UnsplashService:
    """
    Unsplash图片服务（优化版）
    - 添加缓存机制提高性能
    - 支持异步批量搜索
    - 提供降级策略（占位图）
    """

    def __init__(self, access_key: str, cache_size: int = 1000):
        """
        初始化Unsplash服务
        
        Args:
            access_key: Unsplash访问密钥
            cache_size: LRU缓存大小
        """
        self.access_key = access_key
        self.base_url = "https://api.unsplash.com"
        self.cache_size = cache_size
        self.executor = ThreadPoolExecutor(max_workers=5)  # 线程池用于异步请求
        logger.info(f"✅ Unsplash服务初始化完成，缓存大小: {cache_size}")

    def search_photos(self, query: str, per_page: int = 10, use_cache: bool = True) -> List[Dict]:
        """
        搜索图片
        
        Args:
            query: 搜索关键词
            per_page: 每页数量
            use_cache: 是否使用缓存
        
        Returns:
            图片列表
        """
        # 如果启用缓存，先尝试使用缓存方法
        if use_cache:
            return self._search_photos_cached(query, per_page)
        
        return self._search_photos_internal(query, per_page)

    @lru_cache(maxsize=1000)
    def _search_photos_cached(self, query: str, per_page: int = 10) -> List[Dict]:
        """
        带缓存的图片搜索方法
        
        Args:
            query: 搜索关键词
            per_page: 每页数量
        
        Returns:
            图片列表
        """
        logger.debug(f"💾 缓存搜索图片: '{query}'")
        return self._search_photos_internal(query, per_page)

    def _search_photos_internal(self, query: str, per_page: int = 10) -> List[Dict]:
        """
        内部图片搜索方法（不使用缓存）
        
        Args:
            query: 搜索关键词
            per_page: 每页数量
        
        Returns:
            图片列表
        """
        try:
            url = f"{self.base_url}/search/photos"
            params = {
                "query": query,
                "per_page": per_page,
                "client_id": self.access_key
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            logger.info(f"🔍 搜索图片: '{query}'")
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            photos = []
            for result in results:
                photos.append({
                    "url": result["urls"]["regular"],
                    "description": result.get("description", ""),
                    "photographer": result["user"]["name"]
                })

            logger.info(f"✅ 找到 {len(photos)} 张图片")
            return photos

        except Exception as e:
            logger.error(f"❌ 搜索图片失败: '{query}', 错误: {e}")
            return []

    @lru_cache(maxsize=2000)
    def get_photo_url(self, query: str, use_fallback: bool = True) -> Optional[str]:
        """
        获取单张图片URL（带缓存，支持两级降级策略）
        
        降级策略：
        1. 第一级：搜索完整查询（景点名+城市）
        2. 第二级：如果第一级失败，提取城市名单独搜索
        3. 第三级：如果第二级失败，使用占位图
        
        Args:
            query: 搜索关键词（格式：景点名 城市）
            use_fallback: 是否在失败时使用占位图
        
        Returns:
            图片URL或占位图URL
        """
        logger.debug(f"🔍 获取图片URL（缓存）: '{query}'")
        
        # 第一级：搜索完整查询（景点名+城市）
        photos = self._search_photos_internal(query, per_page=1)
        
        if photos:
            url = photos[0].get("url")
            logger.info(f"✅ 第一级搜索成功: {url}")
            return url
        
        # 第二级：如果完整查询失败，尝试只搜索城市名
        # 从查询中提取可能的 cityName（通常是最后一个词）
        query_parts = query.split()
        if len(query_parts) > 1:
            city_query = query_parts[-1]  # 假设最后一个词是城市名
            logger.warning(f"⚠️ 第一级搜索失败，尝试城市搜索: '{city_query}'")
            city_photos = self._search_photos_internal(city_query, per_page=1)
            
            if city_photos:
                url = city_photos[0].get("url")
                logger.info(f"✅ 第二级搜索成功（城市图片）: {url}")
                return url
        
        # 第三级：使用占位图
        if use_fallback:
            logger.warning(f"⚠️ 城市搜索也失败，使用占位图: '{query}'")
            return self._get_placeholder_image(query)
        else:
            logger.warning(f"⚠️ 所有搜索失败: '{query}'")
            return None

    def get_photo_url_async(self, query: str, use_fallback: bool = True) -> str:
        """
        异步获取单张图片URL
        
        Args:
            query: 搜索关键词
            use_fallback: 是否在失败时使用占位图
        
        Returns:
            图片URL
        """
        return self.get_photo_url(query, use_fallback)

    async def fetch_images_batch(
        self,
        queries: List[str],
        use_fallback: bool = True,
        use_cache: bool = True
    ) -> List[Optional[str]]:
        """
        批量异步获取图片URL
        
        Args:
            queries: 查询关键词列表
            use_fallback: 是否使用占位图
            use_cache: 是否使用缓存
        
        Returns:
            图片URL列表
        """
        # 获取事件循环
        loop = asyncio.get_event_loop()
        
        # 创建异步任务
        tasks = [
            loop.run_in_executor(
                self.executor,
                self.get_photo_url_async,
                query,
                use_fallback
            )
            for query in queries
        ]
        
        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ 获取图片失败: '{queries[i]}', 错误: {result}")
                if use_fallback:
                    final_results.append(self._get_placeholder_image(queries[i]))
                else:
                    final_results.append(None)
            else:
                final_results.append(result)
        
        logger.info(f"✅ 批量获取图片完成: {len([r for r in final_results if r])}/{len(queries)}")
        return final_results

    def _get_placeholder_image(self, seed: str) -> str:
        """
        根据种子获取占位图URL
        
        Args:
            seed: 用于选择占位图的种子（如景点名称）
        
        Returns:
            占位图URL
        """
        # 使用字符串哈希来选择占位图
        hash_val = hash(seed)
        index = abs(hash_val) % len(DEFAULT_PLACEHOLDER_IMAGES)
        placeholder_url = DEFAULT_PLACEHOLDER_IMAGES[index]
        logger.debug(f"💾 使用占位图[{index}]: {placeholder_url}")
        return placeholder_url

    def clear_cache(self):
        """清空缓存"""
        self._search_photos_cached.cache_clear()
        self.get_photo_url.cache_clear()
        logger.info("🗑️ Unsplash缓存已清空")

    def get_cache_stats(self) -> Dict[str, int]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计字典
        """
        return {
            "search_photos_cache_info": self._search_photos_cached.cache_info()._asdict(),
            "get_photo_url_cache_info": self.get_photo_url.cache_info()._asdict()
        }
