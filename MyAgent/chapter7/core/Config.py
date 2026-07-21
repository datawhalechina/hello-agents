
from typing import Optional

from openai import BaseModel


class Config(BaseModel):
    default_model : str = "gpt-3.5-turbo"
    default_provider : str = "openai"
    temperature : float = 0.7
    max_token : Optional[int] = None
    
    debug : bool = False
    log_level : str = "INFO"
    
    max_history_length : int = 100
    
    
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量创建配置"""
        return cls(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS")) if os.getenv("MAX_TOKENS") else None,
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.dict()