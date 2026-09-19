"""Redis服务封装"""
import json
from datetime import timedelta
import redis as redis_module
import os

REDIS_HOST = os.getenv("REDIS_HOST") 
REDIS_PORT = int(os.getenv("REDIS_PORT"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB"))

# Refresh Token 过期时间（与JWT refresh token一致）
REFRESH_TOKEN_TTL = timedelta(days=7)

# Key 前缀
PREFIX_REFRESH = "refresh_token:"   # refresh_token:{jti} -> user_id
PREFIX_USER_TOKENS = "user_tokens:"  # user_tokens:{user_id} -> set of jti


def get_redis() -> redis_module.Redis:
    """获取Redis连接"""
    return redis_module.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=3,
    )


def store_refresh_token(user_id: int, jti: str, ttl_seconds: int = None, user_agent: str = "") -> bool:
    """
    将 Refresh Token 的 jti 存入 Redis
    - refresh_token:{jti} -> json({"user_id": ..., "user_agent": ...}) （正向查：token -> user + 设备）
    - user_tokens:{user_id} -> set of jti （反向查：user -> tokens，用于踢下线）
    """
    if ttl_seconds is None:
        ttl_seconds = int(REFRESH_TOKEN_TTL.total_seconds())

    r = get_redis()
    try:
        pipe = r.pipeline()
        data = json.dumps({"user_id": user_id, "user_agent": user_agent})
        pipe.setex(f"{PREFIX_REFRESH}{jti}", ttl_seconds, data)
        pipe.sadd(f"{PREFIX_USER_TOKENS}{user_id}", jti)
        pipe.expire(f"{PREFIX_USER_TOKENS}{user_id}", ttl_seconds)
        pipe.execute()
        return True
    finally:
        r.close()


def validate_refresh_token(jti: str) -> dict | None:
    """
    验证 Refresh Token 是否在 Redis 中有效
    返回值: {"user_id": int, "user_agent": str} 或 None
    """
    r = get_redis()
    try:
        data = r.get(f"{PREFIX_REFRESH}{jti}")
        if data is None:
            return None
        parsed = json.loads(data)
        return {
            "user_id": int(parsed["user_id"]),
            "user_agent": parsed.get("user_agent", ""),
        }
    finally:
        r.close()


def revoke_refresh_token(jti: str) -> bool:
    """吊销单个 Refresh Token"""
    r = get_redis()
    try:
        data = r.get(f"{PREFIX_REFRESH}{jti}")
        if data is None:
            return False
        parsed = json.loads(data)
        uid = int(parsed["user_id"])
        pipe = r.pipeline()
        pipe.delete(f"{PREFIX_REFRESH}{jti}")
        pipe.srem(f"{PREFIX_USER_TOKENS}{uid}", jti)
        pipe.execute()
        return True
    finally:
        r.close()


def revoke_all_user_tokens(user_id: int) -> int:
    """吊销用户的所有 Refresh Token（全部踢下线）"""
    r = get_redis()
    try:
        jtis = r.smembers(f"{PREFIX_USER_TOKENS}{user_id}")
        if not jtis:
            return 0
        pipe = r.pipeline()
        for jti in jtis:
            pipe.delete(f"{PREFIX_REFRESH}{jti}")
        pipe.delete(f"{PREFIX_USER_TOKENS}{user_id}")
        pipe.execute()
        return len(jtis)
    finally:
        r.close()
