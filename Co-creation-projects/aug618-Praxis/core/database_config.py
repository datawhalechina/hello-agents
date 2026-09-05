"""
数据库配置管理
支持Qdrant向量数据库和Neo4j图数据库的配置
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

# Load environment variables early so DB configs pick them up
load_dotenv()


class QdrantConfig(BaseModel):
    """Qdrant向量数据库配置"""
    
    # 连接配置
    url: Optional[str] = Field(
        default=None,
        description="Qdrant服务URL (云服务或自定义URL)"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Qdrant API密钥 (云服务需要)"
    )
    
    # 集合配置
    collection_name: str = Field(
        default="hello_agents_vectors",
        description="向量集合名称"
    )
    vector_size: int = Field(
        default=384,
        description="向量维度"
    )
    distance: str = Field(
        default="cosine",
        description="距离度量方式 (cosine, dot, euclidean)"
    )
    
    # 连接配置
    timeout: int = Field(
        default=30,
        description="连接超时时间(秒)"
    )
    
    @classmethod
    def from_env(cls) -> "QdrantConfig":
        """从环境变量创建配置"""
        return cls(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
            collection_name=os.getenv("QDRANT_COLLECTION", "hello_agents_vectors"),
            vector_size=int(os.getenv("QDRANT_VECTOR_SIZE", "384")),
            distance=os.getenv("QDRANT_DISTANCE", "cosine"),
            timeout=int(os.getenv("QDRANT_TIMEOUT", "30"))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump(exclude_none=True)


class Neo4jConfig(BaseModel):
    """Neo4j图数据库配置"""
    
    # 连接配置
    uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j连接URI"
    )
    username: str = Field(
        default="neo4j",
        description="用户名"
    )
    password: str = Field(
        default="hello-agents-password",
        description="密码"
    )
    database: str = Field(
        default="neo4j",
        description="数据库名称"
    )
    
    # 连接池配置
    max_connection_lifetime: int = Field(
        default=3600,
        description="最大连接生命周期(秒)"
    )
    max_connection_pool_size: int = Field(
        default=50,
        description="最大连接池大小"
    )
    connection_acquisition_timeout: int = Field(
        default=60,
        description="连接获取超时(秒)"
    )
    
    @classmethod
    def from_env(cls) -> "Neo4jConfig":
        """从环境变量创建配置"""
        return cls(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "hello-agents-password"),
            database=os.getenv("NEO4J_DATABASE", "neo4j"),
            max_connection_lifetime=int(os.getenv("NEO4J_MAX_CONNECTION_LIFETIME", "3600")),
            max_connection_pool_size=int(os.getenv("NEO4J_MAX_CONNECTION_POOL_SIZE", "50")),
            connection_acquisition_timeout=int(os.getenv("NEO4J_CONNECTION_TIMEOUT", "60"))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()


class DatabaseConfig(BaseModel):
    """数据库配置管理器"""
    
    qdrant: QdrantConfig = Field(
        default_factory=QdrantConfig,
        description="Qdrant向量数据库配置"
    )
    neo4j: Neo4jConfig = Field(
        default_factory=Neo4jConfig,
        description="Neo4j图数据库配置"
    )
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """从环境变量创建配置"""
        return cls(
            qdrant=QdrantConfig.from_env(),
            neo4j=Neo4jConfig.from_env()
        )
    
    def get_qdrant_config(self) -> Dict[str, Any]:
        """获取Qdrant配置字典"""
        return self.qdrant.to_dict()
    
    def get_neo4j_config(self) -> Dict[str, Any]:
        """获取Neo4j配置字典"""
        return self.neo4j.to_dict()
    
    def validate_connections(self) -> Dict[str, bool]:
        """验证数据库连接配置"""
        results = {}
        
        # 验证Qdrant配置
        try:
            from ..memory.storage.qdrant_store import QdrantVectorStore
            qdrant_store = QdrantVectorStore(**self.get_qdrant_config())
            results["qdrant"] = qdrant_store.health_check()
            logger.info(f"✅ Qdrant连接验证: {'成功' if results['qdrant'] else '失败'}")
        except Exception as e:
            results["qdrant"] = False
            logger.error(f"❌ Qdrant连接验证失败: {e}")
        
        # 验证Neo4j配置
        try:
            from ..memory.storage.neo4j_store import Neo4jGraphStore
            neo4j_store = Neo4jGraphStore(**self.get_neo4j_config())
            results["neo4j"] = neo4j_store.health_check()
            logger.info(f"✅ Neo4j连接验证: {'成功' if results['neo4j'] else '失败'}")
        except Exception as e:
            results["neo4j"] = False
            logger.error(f"❌ Neo4j连接验证失败: {e}")
        
        return results


# 全局配置实例
db_config = DatabaseConfig.from_env()


def get_database_config() -> DatabaseConfig:
    """获取数据库配置"""
    return db_config


def update_database_config(**kwargs) -> None:
    """更新数据库配置"""
    global db_config
    
    if "qdrant" in kwargs:
        db_config.qdrant = QdrantConfig(**kwargs["qdrant"])
    
    if "neo4j" in kwargs:
        db_config.neo4j = Neo4jConfig(**kwargs["neo4j"])
    
    logger.info("✅ 数据库配置已更新")
