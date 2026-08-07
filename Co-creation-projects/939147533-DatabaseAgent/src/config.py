"""
数据库配置管理
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class DatabaseConfig:
    """Oracle数据库配置类"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        service_name: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.host = host or os.getenv("DB_HOST", "localhost")
        self.port = port or int(os.getenv("DB_PORT", "1521"))
        self.service_name = service_name or os.getenv("DB_SERVICE_NAME", "ORCL")
        self.username = username or os.getenv("DB_USERNAME", "system")
        self.password = password or os.getenv("DB_PASSWORD", "")
        
    def get_connection_string(self) -> str:
        """获取Oracle连接字符串"""
        return f"{self.username}/{self.password}@{self.host}:{self.port}/{self.service_name}"
    
    def validate(self) -> bool:
        """验证配置是否完整"""
        return all([self.host, self.port, self.service_name, self.username, self.password])