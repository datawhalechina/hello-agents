from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List, Any

class SystemLog(BaseModel):
    id: int
    forum_id: int
    level: str = "info"
    source: Optional[str] = None
    content: str
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)
