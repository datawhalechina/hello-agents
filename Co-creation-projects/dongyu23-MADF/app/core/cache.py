import json
import logging
from typing import Any, Optional, List
from datetime import datetime
from app.core.config import redis_client

logger = logging.getLogger(__name__)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class RedisService:
    """Redis 缓存与缓冲服务类"""

    @staticmethod
    def set_cache(key: str, value: Any, expire: int = 3600):
        """通用缓存写入"""
        if not redis_client: return False
        try:
            redis_client.set(key, json.dumps(value, cls=DateTimeEncoder), ex=expire)
            return True
        except Exception as e:
            logger.error(f"Redis 缓存设置失败: {e}")
            return False

    @staticmethod
    def get_cache(key: str) -> Optional[Any]:
        """通用缓存读取"""
        if not redis_client: return None
        try:
            data = redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Redis 缓存读取失败: {e}")
            return None

    @staticmethod
    def delete_cache(key: str) -> bool:
        """删除单个缓存"""
        if not redis_client: return False
        try:
            redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis 缓存删除失败: {e}")
            return False

    @staticmethod
    def delete_keys_pattern(pattern: str) -> int:
        """按模式批量删除缓存"""
        if not redis_client: return 0
        try:
            # Use scan_iter for robust cursor handling
            keys = list(redis_client.scan_iter(match=pattern, count=100))
            
            if keys:
                logger.info(f"Deleting {len(keys)} keys matching pattern '{pattern}'")
                return redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis 模式删除失败: {e}")
            return 0

    @staticmethod
    def push_message(queue: str, message: Any):
        """消息缓冲：将数据推入队列尾部 (用于日志或消息缓冲)"""
        if not redis_client: return False
        try:
            redis_client.rpush(queue, json.dumps(message, cls=DateTimeEncoder))
            return True
        except Exception as e:
            logger.error(f"Redis 消息缓冲推送失败: {e}")
            return False

    @staticmethod
    def pop_messages(queue: str, count: int = 10) -> List[Any]:
        """批量获取并移除缓冲的消息 (用于批量写入数据库)"""
        if not redis_client: return []
        messages = []
        try:
            # 循环弹出指定数量的消息
            for _ in range(count):
                msg = redis_client.lpop(queue)
                if not msg: break
                messages.append(json.loads(msg))
            return messages
        except Exception as e:
            logger.error(f"Redis 消息弹出失败: {e}")
            return []

cache_service = RedisService()
