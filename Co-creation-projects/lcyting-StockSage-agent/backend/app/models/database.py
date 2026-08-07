"""
智能股票分析助手 — 数据库连接模块

使用SQLAlchemy + aiosqlite实现异步数据库访问。
数据库文件自动创建在项目data目录下。
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from pathlib import Path
import sys

# 确保能导入配置模块
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "backend"))

from app.config import settings


# 将SQLite URL转换为异步版本（aiosqlite）
def _build_async_url(url: str) -> str:
    """将 sqlite:/// 格式转为 sqlite+aiosqlite:/// 格式"""
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///")
    return url


# 确保数据目录存在
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

# 创建异步引擎
engine = create_async_engine(
    _build_async_url(settings.DATABASE_URL),
    echo=False,  # 开发时可设为True查看SQL日志
)

# 创建异步会话工厂
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# SQLAlchemy声明式基类
class Base(DeclarativeBase):
    pass


async def init_db():
    """初始化数据库，创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db_session() -> AsyncSession:
    """获取数据库会话（FastAPI依赖注入用）"""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
