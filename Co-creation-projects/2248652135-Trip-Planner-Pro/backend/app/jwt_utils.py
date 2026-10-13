"""JWT工具 - 标准RFC7519格式 + Redis持久化Refresh Token"""
import os
import secrets
import jwt
from datetime import datetime, timedelta, timezone

_ISSUER = "trip-planner-pro"

# 密钥（首次运行自动生成）
_SECRET_KEY = None


def _get_secret() -> str:
    global _SECRET_KEY
    if _SECRET_KEY is None:
        key = os.getenv("JWT_SECRET")
        if not key:
            key = os.urandom(32).hex()
            os.environ["JWT_SECRET"] = key
        _SECRET_KEY = key
    return _SECRET_KEY


ALGORITHM = "HS256"

# 过期时间
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: int) -> str:
    """生成标准 Access Token（30分钟有效，HttpOnly Cookie传递）"""
    now = _now()
    payload = {
        "iss": _ISSUER,
        "sub": str(user_id),
        "aud": f"{_ISSUER}/api",
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
        "jti": secrets.token_hex(16),
        "type": "access",
    }
    return jwt.encode(payload, _get_secret(), algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> tuple:
    """
    生成标准 Refresh Token（7天有效，jti存入Redis）
    返回: (token_str, jti)
    """
    now = _now()
    jti = secrets.token_hex(16)
    payload = {
        "iss": _ISSUER,
        "sub": str(user_id),
        "aud": f"{_ISSUER}/auth/refresh",
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": now,
        "jti": jti,
        "type": "refresh",
    }
    token = jwt.encode(payload, _get_secret(), algorithm=ALGORITHM)
    return token, jti


def verify_access_token(token: str) -> dict:
    """验证 Access Token，返回 {"id": user_id}"""
    payload = jwt.decode(
        token,
        _get_secret(),
        algorithms=[ALGORITHM],
        audience=f"{_ISSUER}/api",
        issuer=_ISSUER,
        options={"require": ["exp", "iat", "sub", "jti", "type"]},
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Token类型错误")
    return {"id": int(payload["sub"])}


def verify_refresh_token(token: str) -> dict:
    """验证 Refresh Token（仅JWT签名验证），返回 {"id": user_id, "jti": jti}"""
    payload = jwt.decode(
        token,
        _get_secret(),
        algorithms=[ALGORITHM],
        audience=f"{_ISSUER}/auth/refresh",
        issuer=_ISSUER,
        options={"require": ["exp", "iat", "sub", "jti", "type"]},
    )
    if payload.get("type") != "refresh":
        raise jwt.InvalidTokenError("Token类型错误")
    return {"id": int(payload["sub"]), "jti": payload["jti"]}


def get_token_jti(token: str) -> str:
    """解码token获取jti（不验证签名，仅用于找回jti）"""
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload.get("jti", "")
    except Exception:
        return ""
